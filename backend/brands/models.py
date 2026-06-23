import uuid

from django.db import models

from agencies.models import Agency


def brand_asset_upload_path(instance, filename):
    return f"brands/{instance.brand_id}/assets/{instance.asset_type}/{filename}"


class BrandProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="brands")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    is_active = models.BooleanField(default=True)

    # Onboarding / ground-truth fields (user-authored, never auto-overwritten by AI)
    style_description = models.TextField(blank=True)
    voice_tone_description = models.TextField(blank=True)
    voice_traits = models.JSONField(default=list, blank=True)
    target_audience = models.TextField(blank=True)
    font_primary = models.CharField(max_length=255, blank=True)
    font_secondary = models.CharField(max_length=255, blank=True)

    country_code = models.CharField(max_length=2, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    default_publish_time = models.TimeField(default="09:00")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agency", "slug"], name="unique_brand_slug_per_agency"),
        ]
        indexes = [
            models.Index(fields=["agency", "is_active"]),
        ]

    def __str__(self):
        return self.name


class BrandColor(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXTRACTED_FROM_LOGO = "extracted_from_logo", "Extracted from logo"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="colors")
    name = models.CharField(max_length=100, blank=True)
    hex_value = models.CharField(max_length=7)
    role = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.MANUAL)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.brand} - {self.hex_value}"


class BrandAsset(models.Model):
    class AssetType(models.TextChoices):
        LOGO = "logo", "Logo"
        IDENTITY_DOCUMENT = "identity_document", "Identity document"

    class AnalysisStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(max_length=30, choices=AssetType.choices)
    file = models.FileField(upload_to=brand_asset_upload_path)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)

    # Populated by the analyze_brand_asset task when the upload is a PDF:
    # list of storage keys/URLs for each page rendered as an image.
    page_images = models.JSONField(default=list, blank=True)

    claude_vision_analysis = models.JSONField(null=True, blank=True)
    analysis_status = models.CharField(
        max_length=20, choices=AnalysisStatus.choices, default=AnalysisStatus.PENDING
    )
    is_primary = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["brand", "asset_type"]),
        ]

    def __str__(self):
        return f"{self.brand} - {self.asset_type} ({self.original_filename})"


class BrandAIContext(models.Model):
    """Claude's vision-derived enrichment, kept separate from BrandProfile's
    user-authored fields. The user must explicitly pull this into their own
    fields via the ai-context/apply/ endpoint -- it is never auto-merged."""

    brand = models.OneToOneField(BrandProfile, on_delete=models.CASCADE, related_name="ai_context")
    style_keywords = models.JSONField(default=list, blank=True)
    mood_descriptors = models.JSONField(default=list, blank=True)
    visual_donts = models.JSONField(default=list, blank=True)
    enrichment_summary = models.TextField(blank=True)
    source_assets = models.ManyToManyField(BrandAsset, related_name="ai_context_runs", blank=True)
    last_enriched_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"AI context for {self.brand}"
