from datetime import date, time, timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from firebase_admin.exceptions import FirebaseError
from rest_framework import status
from rest_framework.test import APITestCase

from agencies.models import AgencyMembership, User
from content_calendar.models import ContentCalendarEntry
from testing import create_agency_with_user, create_brand

from .models import Notification, PushSubscription, ReminderEscalationState
from .tasks import notify_brand_agency, scan_reminder_escalations, send_fcm_push


def _create_entry(brand, **kwargs):
    defaults = dict(
        scheduled_date=date.today(),
        content_format="image",
        aspect_ratio="square",
        source="user_input",
    )
    defaults.update(kwargs)
    return ContentCalendarEntry.objects.create(brand=brand, **defaults)


class ReminderEscalationStateConstraintTests(TestCase):
    def test_one_to_one_constraint(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        ReminderEscalationState.objects.create(calendar_entry=entry)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReminderEscalationState.objects.create(calendar_entry=entry)


class ScanReminderEscalationsTests(TestCase):
    def _entry_due_in(self, brand, hours_from_now):
        target_dt = timezone.now() + timedelta(hours=hours_from_now)
        return _create_entry(
            brand,
            scheduled_date=target_dt.date(),
            scheduled_time=target_dt.time(),
            status=ContentCalendarEntry.Status.APPROVED,
        )

    def test_fires_only_the_due_step_and_marks_it_sent(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, timezone="UTC", default_publish_time=time(12, 0))
        entry = self._entry_due_in(brand, 13)  # within the 24h window, not within 12h/3h/0h

        with patch("notifications.tasks.notify_brand_agency.delay") as mock_notify:
            scan_reminder_escalations()

        state = ReminderEscalationState.objects.get(calendar_entry=entry)
        self.assertTrue(state.sent_24h)
        self.assertFalse(state.sent_12h)
        self.assertFalse(state.sent_3h)
        self.assertFalse(state.sent_due)
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.kwargs["notification_type"], "reminder_24h")

    def test_does_not_refire_already_sent_step(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, timezone="UTC", default_publish_time=time(12, 0))
        entry = self._entry_due_in(brand, 13)
        ReminderEscalationState.objects.create(calendar_entry=entry, sent_24h=True)

        with patch("notifications.tasks.notify_brand_agency.delay") as mock_notify:
            scan_reminder_escalations()
        mock_notify.assert_not_called()

    def test_due_now_entry_fires_all_unset_steps(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, timezone="UTC", default_publish_time=time(12, 0))
        entry = self._entry_due_in(brand, -1)  # already past publish time

        with patch("notifications.tasks.notify_brand_agency.delay") as mock_notify:
            scan_reminder_escalations()

        state = ReminderEscalationState.objects.get(calendar_entry=entry)
        self.assertTrue(state.sent_24h)
        self.assertTrue(state.sent_12h)
        self.assertTrue(state.sent_3h)
        self.assertTrue(state.sent_due)
        self.assertEqual(mock_notify.call_count, 4)


class NotifyBrandAgencyTests(TestCase):
    def test_fans_out_to_all_active_members(self):
        _, agency = create_agency_with_user(email="m1@example.com")
        user2 = User.objects.create_user(email="m2@example.com", password="x")
        AgencyMembership.objects.create(agency=agency, user=user2)
        brand = create_brand(agency)

        with patch("notifications.tasks.send_notification.delay") as mock_send:
            notify_brand_agency(
                brand_id=str(brand.id), notification_type="suggestion_batch_ready", title="T", body="B"
            )
        self.assertEqual(mock_send.call_count, 2)

    def test_inactive_members_excluded(self):
        _, agency = create_agency_with_user(email="m1@example.com")
        user2 = User.objects.create_user(email="m2@example.com", password="x")
        AgencyMembership.objects.create(agency=agency, user=user2, is_active=False)
        brand = create_brand(agency)

        with patch("notifications.tasks.send_notification.delay") as mock_send:
            notify_brand_agency(brand_id=str(brand.id), notification_type="x", title="T", body="B")
        self.assertEqual(mock_send.call_count, 1)


class SendFcmPushTaskTests(TestCase):
    def test_skipped_when_no_active_subscription(self):
        user, agency = create_agency_with_user()
        notification = Notification.objects.create(
            user=user, notification_type="generation_done", title="T", body="B"
        )
        send_fcm_push(str(notification.id))
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, Notification.DeliveryStatus.SKIPPED_NO_SUBSCRIPTION)

    def test_successful_send_marks_sent(self):
        user, agency = create_agency_with_user()
        PushSubscription.objects.create(user=user, registration_token="tok-1")
        notification = Notification.objects.create(
            user=user, notification_type="generation_done", title="T", body="B"
        )
        with patch("notifications.tasks._get_firebase_app"), patch(
            "notifications.tasks.messaging.send", return_value="message-id"
        ):
            send_fcm_push(str(notification.id))
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, Notification.DeliveryStatus.SENT)

    def test_invalid_token_deactivates_subscription_and_marks_failed(self):
        user, agency = create_agency_with_user()
        subscription = PushSubscription.objects.create(user=user, registration_token="bad-tok")
        notification = Notification.objects.create(
            user=user, notification_type="generation_done", title="T", body="B"
        )
        error = FirebaseError(code="INVALID_ARGUMENT", message="bad token")
        with patch("notifications.tasks._get_firebase_app"), patch(
            "notifications.tasks.messaging.send", side_effect=error
        ):
            send_fcm_push(str(notification.id))

        subscription.refresh_from_db()
        notification.refresh_from_db()
        self.assertFalse(subscription.is_active)
        self.assertEqual(notification.delivery_status, Notification.DeliveryStatus.FAILED)

    def test_one_failed_token_does_not_block_others(self):
        user, agency = create_agency_with_user()
        PushSubscription.objects.create(user=user, registration_token="bad-tok")
        PushSubscription.objects.create(user=user, registration_token="good-tok")
        notification = Notification.objects.create(
            user=user, notification_type="generation_done", title="T", body="B"
        )
        error = FirebaseError(code="NOT_FOUND", message="gone")
        with patch("notifications.tasks._get_firebase_app"), patch(
            "notifications.tasks.messaging.send", side_effect=[error, "message-id"]
        ):
            send_fcm_push(str(notification.id))

        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, Notification.DeliveryStatus.SENT)


class PushSubscriptionApiTests(APITestCase):
    def test_register_reactivates_existing_token(self):
        user, agency = create_agency_with_user()
        existing = PushSubscription.objects.create(user=user, registration_token="tok-1", is_active=False)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/api/push-subscriptions/", {"registration_token": "tok-1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)
        self.assertEqual(PushSubscription.objects.count(), 1)

    def test_unique_registration_token_constraint(self):
        user, agency = create_agency_with_user()
        PushSubscription.objects.create(user=user, registration_token="dup-tok")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PushSubscription.objects.create(user=user, registration_token="dup-tok")
