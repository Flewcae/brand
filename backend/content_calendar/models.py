import uuid

from django.db import models

from brands.models import BrandProfile


class ContentCalendarEntry(models.Model):
    class ContentFormat(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    class AspectRatio(models.TextChoices):
        LANDSCAPE = "landscape", "Landscape"
        PORTRAIT = "portrait", "Portrait"
        SQUARE = "square", "Square"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUGGESTED = "suggested", "Suggested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        GENERATED = "generated", "Generated"
        PUBLISHED = "published", "Published"

    class Source(models.TextChoices):
        USER_INPUT = "user_input", "User input"
        CLAUDE_SUGGESTION = "claude_suggestion", "Claude suggestion"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="calendar_entries")
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    content_format = models.CharField(max_length=10, choices=ContentFormat.choices)
    aspect_ratio = models.CharField(max_length=10, choices=AspectRatio.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField(max_length=20, choices=Source.choices)
    brief = models.TextField(blank=True)

    brand_holiday = models.ForeignKey(
        "special_days.BrandHoliday",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_entries",
    )
    suggestion_batch = models.ForeignKey(
        "CalendarSuggestionBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )
    parent_entry = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="variations"
    )
    active_generation_version = models.ForeignKey(
        "generation.GenerationVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["brand", "scheduled_date"]),
            models.Index(fields=["brand", "status"]),
        ]

    def __str__(self):
        return f"{self.brand} - {self.scheduled_date} ({self.status})"


class CalendarSuggestionBatch(models.Model):
    class Trigger(models.TextChoices):
        WEEKLY_BEAT = "weekly_beat", "Weekly beat"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="suggestion_batches")
    trigger = models.CharField(max_length=20, choices=Trigger.choices)
    requested_by = models.ForeignKey(
        "agencies.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggestion_batches",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    entry_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.brand} - {self.trigger} ({self.status})"
