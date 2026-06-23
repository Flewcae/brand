import uuid

from django.db import models

from agencies.models import User
from brands.models import BrandProfile


class PushSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.endpoint[:40]}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        GENERATION_DONE = "generation_done", "Generation done"
        GENERATION_FAILED = "generation_failed", "Generation failed"
        REMINDER_24H = "reminder_24h", "Reminder 24h"
        REMINDER_12H = "reminder_12h", "Reminder 12h"
        REMINDER_3H = "reminder_3h", "Reminder 3h"
        REMINDER_DUE = "reminder_due", "Reminder due"
        SUGGESTION_BATCH_READY = "suggestion_batch_ready", "Suggestion batch ready"

    class Channel(models.TextChoices):
        WEB_PUSH = "web_push", "Web push"
        IN_APP_ONLY = "in_app_only", "In-app only"

    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED_NO_SUBSCRIPTION = "skipped_no_subscription", "Skipped (no subscription)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    brand = models.ForeignKey(
        BrandProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    related_calendar_entry = models.ForeignKey(
        "content_calendar.ContentCalendarEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    related_generation_version = models.ForeignKey(
        "generation.GenerationVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WEB_PUSH)
    delivery_status = models.CharField(
        max_length=30, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["related_calendar_entry"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.notification_type}"


class ReminderEscalationState(models.Model):
    """One row per calendar entry with 4 fixed booleans rather than a generic
    per-step log table -- simpler/cheaper for a fixed 4-step ladder. Revisit
    if the escalation steps ever become configurable/dynamic."""

    calendar_entry = models.OneToOneField(
        "content_calendar.ContentCalendarEntry",
        on_delete=models.CASCADE,
        related_name="escalation_state",
    )
    sent_24h = models.BooleanField(default=False)
    sent_12h = models.BooleanField(default=False)
    sent_3h = models.BooleanField(default=False)
    sent_due = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Escalation state for {self.calendar_entry_id}"
