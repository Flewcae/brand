import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import firebase_admin
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
        else:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app

ESCALATION_STEPS = [
    ("sent_24h", timedelta(hours=24), "reminder_24h", "Yarın paylaşım var"),
    ("sent_12h", timedelta(hours=12), "reminder_12h", "12 saat sonra paylaşım var"),
    ("sent_3h", timedelta(hours=3), "reminder_3h", "3 saat sonra paylaşım var"),
    ("sent_due", timedelta(hours=0), "reminder_due", "Paylaşım zamanı geldi"),
]


@shared_task
def scan_reminder_escalations():
    from content_calendar.models import ContentCalendarEntry

    from .models import ReminderEscalationState

    now = timezone.now()
    candidates = ContentCalendarEntry.objects.filter(
        status__in=[ContentCalendarEntry.Status.APPROVED, ContentCalendarEntry.Status.GENERATED],
        scheduled_date__gte=now.date() - timedelta(days=1),
    ).select_related("brand")

    for entry in candidates:
        publish_at_utc = _resolve_publish_datetime_utc(entry)
        if publish_at_utc is None:
            continue

        state, _ = ReminderEscalationState.objects.get_or_create(calendar_entry=entry)

        for field_name, lead_time, notification_type, title in ESCALATION_STEPS:
            if getattr(state, field_name):
                continue
            # Window check (<=) rather than equality: the scanner runs every
            # 15 min, so an exact-instant match would miss most thresholds.
            if now >= publish_at_utc - lead_time:
                notify_brand_agency.delay(
                    brand_id=str(entry.brand_id),
                    notification_type=notification_type,
                    title=title,
                    body=entry.brief[:120] or str(entry.scheduled_date),
                    related_calendar_entry_id=str(entry.id),
                )
                setattr(state, field_name, True)
                state.save(update_fields=[field_name, "updated_at"])


def _resolve_publish_datetime_utc(entry):
    brand = entry.brand
    publish_time = entry.scheduled_time or brand.default_publish_time
    try:
        tz = ZoneInfo(brand.timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    local_dt = datetime.combine(entry.scheduled_date, publish_time, tzinfo=tz)
    return local_dt.astimezone(ZoneInfo("UTC"))


@shared_task
def send_notification(
    user_id,
    brand_id=None,
    notification_type="generation_done",
    title="",
    body="",
    related_calendar_entry_id=None,
    related_generation_version_id=None,
):
    from .models import Notification

    notification = Notification.objects.create(
        user_id=user_id,
        brand_id=brand_id,
        notification_type=notification_type,
        title=title,
        body=body,
        related_calendar_entry_id=related_calendar_entry_id,
        related_generation_version_id=related_generation_version_id,
    )
    send_fcm_push.delay(str(notification.id))
    return str(notification.id)


@shared_task
def notify_brand_agency(
    brand_id,
    notification_type,
    title,
    body,
    related_calendar_entry_id=None,
    related_generation_version_id=None,
):
    """Fan-out for notifications with no single owning user (weekly
    suggestion batches, reminder escalations): every active member of the
    brand's agency gets their own Notification row."""
    from agencies.models import AgencyMembership
    from brands.models import BrandProfile

    brand = BrandProfile.objects.select_related("agency").get(id=brand_id)
    user_ids = AgencyMembership.objects.filter(agency=brand.agency, is_active=True).values_list(
        "user_id", flat=True
    )

    for user_id in user_ids:
        send_notification.delay(
            user_id=str(user_id),
            brand_id=str(brand_id),
            notification_type=notification_type,
            title=title,
            body=body,
            related_calendar_entry_id=related_calendar_entry_id,
            related_generation_version_id=related_generation_version_id,
        )


@shared_task
def send_fcm_push(notification_id):
    from .models import Notification, PushSubscription

    notification = Notification.objects.select_related("user").get(id=notification_id)
    subscriptions = list(PushSubscription.objects.filter(user=notification.user, is_active=True))

    if not subscriptions:
        notification.delivery_status = Notification.DeliveryStatus.SKIPPED_NO_SUBSCRIPTION
        notification.save(update_fields=["delivery_status"])
        return

    _get_firebase_app()
    any_sent = False

    for subscription in subscriptions:
        message = messaging.Message(
            notification=messaging.Notification(title=notification.title, body=notification.body),
            token=subscription.registration_token,
        )
        try:
            messaging.send(message)
            any_sent = True
        except FirebaseError as exc:
            # Token no longer valid (app uninstalled, permission revoked, etc.)
            if getattr(exc, "code", None) in ("NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"):
                subscription.is_active = False
                subscription.save(update_fields=["is_active"])
            logger.warning("FCM push failed for subscription_id=%s: %s", subscription.id, exc)

    notification.delivery_status = (
        Notification.DeliveryStatus.SENT if any_sent else Notification.DeliveryStatus.FAILED
    )
    notification.sent_at = timezone.now()
    notification.save(update_fields=["delivery_status", "sent_at"])
