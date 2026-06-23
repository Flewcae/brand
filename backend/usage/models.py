import uuid

from django.db import models

from brands.models import BrandAsset, BrandProfile


class UsageLog(models.Model):
    """Per-brand cost/usage ledger for every Claude and Grok call -- the
    foundation for future client billing. Exactly one of
    generation_version/suggestion_batch/brand_asset should be set per row
    (soft invariant, enforced at the call site, not via DB constraint)."""

    TICKS_PER_USD = 10_000_000_000  # xAI: 100,000,000 ticks = 1 cent

    class Provider(models.TextChoices):
        CLAUDE = "claude", "Claude"
        GROK = "grok", "Grok"

    class Operation(models.TextChoices):
        VISION_ANALYSIS = "vision_analysis", "Vision analysis"
        PROMPT_GENERATION = "prompt_generation", "Prompt generation"
        SUGGESTION_GENERATION = "suggestion_generation", "Suggestion generation"
        IMAGE_GENERATION = "image_generation", "Image generation"
        VIDEO_GENERATION = "video_generation", "Video generation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="usage_logs")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    model = models.CharField(max_length=100)
    operation = models.CharField(max_length=30, choices=Operation.choices)

    cost_in_usd_ticks = models.BigIntegerField(null=True, blank=True)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    generation_version = models.ForeignKey(
        "generation.GenerationVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_logs",
    )
    suggestion_batch = models.ForeignKey(
        "content_calendar.CalendarSuggestionBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_logs",
    )
    brand_asset = models.ForeignKey(
        BrandAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_logs"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["brand", "created_at"]),
            models.Index(fields=["brand", "provider"]),
        ]

    def save(self, *args, **kwargs):
        if self.estimated_cost_usd is None and self.cost_in_usd_ticks is not None:
            self.estimated_cost_usd = self.cost_in_usd_ticks / self.TICKS_PER_USD
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand} - {self.provider}/{self.operation}"
