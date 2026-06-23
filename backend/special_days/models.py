import uuid

from django.db import models

from brands.models import BrandProfile


class CountryHolidayTemplate(models.Model):
    """Shared, reusable per-country cache. Never written per-brand."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country_code = models.CharField(max_length=2, unique=True)
    popular_days_last_refreshed_at = models.DateTimeField(null=True, blank=True)
    popular_days_source_meta = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.country_code


class CountryHolidayTemplateEntry(models.Model):
    """Resolved (year-included) dates, not abstract date rules -- official/
    religious days already come year-resolved from the `holidays` library
    (e.g. lunar dates), so re-deriving a rule engine for them would be
    pointless complexity; popular/marketing days are resolved to concrete
    dates at refresh time for the same reason, kept simple on purpose."""

    class Category(models.TextChoices):
        OFFICIAL = "official", "Official"
        RELIGIOUS = "religious", "Religious"
        POPULAR = "popular", "Popular"

    class Source(models.TextChoices):
        HOLIDAYS_LIB = "holidays_lib", "holidays library"
        CLAUDE_CURATED = "claude_curated", "Claude curated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(CountryHolidayTemplate, on_delete=models.CASCADE, related_name="entries")
    name = models.CharField(max_length=255)
    date = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices)
    source = models.CharField(max_length=20, choices=Source.choices)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["template", "name", "date"], name="unique_template_entry"),
        ]
        indexes = [
            models.Index(fields=["template", "date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


class BrandHoliday(models.Model):
    """Per-brand editable copy, independent of the shared template after import."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="holidays")
    source_template_entry = models.ForeignKey(
        CountryHolidayTemplateEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="brand_holidays",
    )
    name = models.CharField(max_length=255)
    date = models.DateField()
    category = models.CharField(max_length=20, choices=CountryHolidayTemplateEntry.Category.choices)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["brand", "date"]),
            models.Index(fields=["brand", "is_active"]),
        ]

    def __str__(self):
        return f"{self.brand} - {self.name} ({self.date})"
