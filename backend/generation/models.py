import uuid

from django.db import models


def generation_media_upload_path(instance, filename):
    return f"generations/{instance.calendar_entry_id}/{instance.id}/{filename}"


class GenerationVersion(models.Model):
    """No separate video-job table: video-specific async fields live here too,
    since a version is 1:1 with a single Grok call attempt. `status` alone
    drives both the 'leave and get notified' and 'stay and watch' UX (the
    frontend just polls this field either way)."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        PENDING_PROMPT = "pending_prompt", "Pending prompt"
        PROMPT_READY = "prompt_ready", "Prompt ready"
        SUBMITTED = "submitted", "Submitted"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    calendar_entry = models.ForeignKey(
        "content_calendar.ContentCalendarEntry",
        on_delete=models.CASCADE,
        related_name="generation_versions",
    )
    version_number = models.PositiveSmallIntegerField()
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PROMPT)

    claude_prompt_text = models.TextField(blank=True)
    grok_request_payload = models.JSONField(default=dict, blank=True)
    grok_request_id = models.CharField(max_length=255, blank=True)
    grok_response_meta = models.JSONField(null=True, blank=True)

    media_file = models.FileField(upload_to=generation_media_upload_path, null=True, blank=True)
    thumbnail_file = models.FileField(upload_to=generation_media_upload_path, null=True, blank=True)
    error_message = models.TextField(blank=True)

    requested_by = models.ForeignKey(
        "agencies.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["calendar_entry", "version_number"], name="unique_version_per_entry"
            ),
        ]
        indexes = [
            models.Index(fields=["calendar_entry", "version_number"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.calendar_entry_id} v{self.version_number}"
