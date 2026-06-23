import json
import logging
import re
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

CLAUDE_TEXT_MODEL = "claude-sonnet-4-6"
YEARS_AHEAD = 3
STALE_AFTER_DAYS = 90

POPULAR_DAYS_PROMPT = (
    "'{country_code}' ülke koduna sahip ülkede sosyal medya pazarlaması için "
    "önemli olan popüler/ticari günleri listele (resmi tatil OLMAYAN, örn. "
    "Sevgililer Günü, Black Friday, Anneler Günü, Kadınlar Günü gibi günler). "
    "Sadece şu şemaya uyan bir JSON listesi döndür, başka hiçbir metin ekleme: "
    '[{{"name": "...", "month": 1-12, "day": 1-31, "description": "kısa açıklama"}}]'
)


@shared_task
def refresh_country_holiday_template(country_code, requesting_brand_id=None):
    from .models import CountryHolidayTemplate, CountryHolidayTemplateEntry

    template, _ = CountryHolidayTemplate.objects.get_or_create(country_code=country_code)
    current_year = timezone.now().year
    years = list(range(current_year, current_year + YEARS_AHEAD + 1))

    official_entries = _official_entries(country_code, years)
    popular_entries = _popular_entries(country_code, years, requesting_brand_id)

    with transaction.atomic():
        # Full replace rather than upsert -- simpler, and this is a cheap,
        # infrequent maintenance operation (refreshed at most every ~90 days).
        CountryHolidayTemplateEntry.objects.filter(template=template).delete()
        CountryHolidayTemplateEntry.objects.bulk_create(
            CountryHolidayTemplateEntry(template=template, **entry)
            for entry in official_entries + popular_entries
        )

    template.popular_days_last_refreshed_at = timezone.now()
    template.popular_days_source_meta = {"model": CLAUDE_TEXT_MODEL, "years": years}
    template.save(update_fields=["popular_days_last_refreshed_at", "popular_days_source_meta"])
    return str(template.id)


def _official_entries(country_code, years):
    from .models import CountryHolidayTemplateEntry

    import holidays as holidays_lib

    try:
        country_holidays = holidays_lib.country_holidays(country_code, years=years)
    except NotImplementedError:
        logger.warning("holidays library has no data for country_code=%s", country_code)
        return []

    # NOTE: the `holidays` library doesn't reliably tag entries as
    # official vs. religious across all supported countries, so everything
    # it returns is classified OFFICIAL here. Refine per-country later if needed.
    return [
        {
            "name": name,
            "date": entry_date,
            "category": CountryHolidayTemplateEntry.Category.OFFICIAL,
            "source": CountryHolidayTemplateEntry.Source.HOLIDAYS_LIB,
            "description": "",
        }
        for entry_date, name in sorted(country_holidays.items())
    ]


def _popular_entries(country_code, years, requesting_brand_id):
    from .models import CountryHolidayTemplateEntry

    raw_days = _fetch_popular_days_from_claude(country_code, requesting_brand_id)

    entries = []
    for year in years:
        for day in raw_days:
            try:
                resolved_date = date(year, int(day["month"]), int(day["day"]))
            except (KeyError, ValueError, TypeError):
                continue
            entries.append(
                {
                    "name": str(day.get("name", ""))[:255],
                    "date": resolved_date,
                    "category": CountryHolidayTemplateEntry.Category.POPULAR,
                    "source": CountryHolidayTemplateEntry.Source.CLAUDE_CURATED,
                    "description": day.get("description", ""),
                }
            )
    return entries


def _fetch_popular_days_from_claude(country_code, requesting_brand_id):
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_TEXT_MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": POPULAR_DAYS_PROMPT.format(country_code=country_code),
            }
        ],
    )

    if requesting_brand_id:
        _log_usage(requesting_brand_id, response)

    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json_list(text)


def _log_usage(brand_id, response):
    # Country-template refreshes are shared across brands of the same
    # country; we only attribute Claude cost to a brand when the refresh
    # was triggered synchronously by that brand's import request. Beat-
    # triggered refreshes (no specific brand) are not billed to anyone.
    from usage.models import UsageLog

    UsageLog.objects.create(
        brand_id=brand_id,
        provider=UsageLog.Provider.CLAUDE,
        model=CLAUDE_TEXT_MODEL,
        operation=UsageLog.Operation.SUGGESTION_GENERATION,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


def _parse_json_list(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return []


@shared_task
def import_brand_holidays(brand_id, country_code, years):
    from .models import BrandHoliday, CountryHolidayTemplate, CountryHolidayTemplateEntry

    template = CountryHolidayTemplate.objects.filter(country_code=country_code).first()
    is_stale = (
        template is None
        or template.popular_days_last_refreshed_at is None
        or template.popular_days_last_refreshed_at < timezone.now() - timedelta(days=STALE_AFTER_DAYS)
    )
    if is_stale:
        refresh_country_holiday_template(country_code, requesting_brand_id=brand_id)
        template = CountryHolidayTemplate.objects.get(country_code=country_code)

    entries = CountryHolidayTemplateEntry.objects.filter(template=template, date__year__in=years)

    created_ids = []
    for entry in entries:
        brand_holiday, _ = BrandHoliday.objects.get_or_create(
            brand_id=brand_id,
            source_template_entry=entry,
            date=entry.date,
            defaults={
                "name": entry.name,
                "category": entry.category,
                "is_active": True,
            },
        )
        created_ids.append(str(brand_holiday.id))
    return created_ids


@shared_task
def refresh_stale_country_templates():
    from .models import CountryHolidayTemplate

    threshold = timezone.now() - timedelta(days=STALE_AFTER_DAYS)
    stale_templates = CountryHolidayTemplate.objects.filter(
        Q(popular_days_last_refreshed_at__isnull=True) | Q(popular_days_last_refreshed_at__lt=threshold)
    )
    for template in stale_templates:
        refresh_country_holiday_template.delay(template.country_code)
