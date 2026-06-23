import json
import logging
import re
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

CLAUDE_TEXT_MODEL = "claude-sonnet-4-6"
SUGGESTIONS_PER_BATCH = 3
UPCOMING_HOLIDAY_WINDOW_DAYS = 21

SUGGESTION_PROMPT = (
    "Sen bir sosyal medya içerik stratejistisin. Aşağıdaki marka bağlamını, "
    "yaklaşan özel günleri ve geçmiş paylaşımları kullanarak bu marka için "
    "{count} adet yeni içerik fikri öner. Her öneri özgün ve markaya uygun "
    "olmalı. Sadece şu şemaya uyan bir JSON listesi döndür, başka metin "
    'ekleme: [{{"brief": "...", "content_format": "image|video", '
    '"aspect_ratio": "landscape|portrait|square", "scheduled_date": '
    '"YYYY-MM-DD", "brand_holiday_id": "uuid veya null"}}]\n\n'
    "Marka bağlamı:\n{brand_context}\n\nYaklaşan özel günler:\n{holiday_lines}\n\n"
    "Son paylaşılan/üretilen içerikler:\n{recent_entries}"
)

VARIATION_PROMPT = (
    "Sen bir sosyal medya içerik stratejistisin. Kullanıcının verdiği fikri "
    "aşağıdaki marka bağlamına göre değerlendir ve {count} adet iyileştirilmiş "
    "varyasyon öner. Sadece şu şemaya uyan bir JSON listesi döndür, başka "
    'metin ekleme: [{{"brief": "..."}}]\n\nMarka bağlamı:\n{brand_context}\n\n'
    "Orijinal fikir: {original_brief}"
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
def dispatch_weekly_suggestions():
    from brands.models import BrandProfile

    from .models import CalendarSuggestionBatch

    for brand_id in BrandProfile.objects.filter(is_active=True).values_list("id", flat=True):
        batch = CalendarSuggestionBatch.objects.create(
            brand_id=brand_id, trigger=CalendarSuggestionBatch.Trigger.WEEKLY_BEAT
        )
        generate_suggestion_batch.delay(str(batch.id))


@shared_task
def generate_suggestion_batch(batch_id):
    import anthropic

    from brands.services import build_brand_context_text
    from special_days.models import BrandHoliday

    from .models import CalendarSuggestionBatch, ContentCalendarEntry

    batch = CalendarSuggestionBatch.objects.select_related("brand").get(id=batch_id)
    batch.status = CalendarSuggestionBatch.Status.RUNNING
    batch.save(update_fields=["status"])
    brand = batch.brand

    try:
        today = timezone.now().date()
        upcoming_holidays = list(
            BrandHoliday.objects.filter(
                brand=brand,
                is_active=True,
                date__gte=today,
                date__lte=today + timedelta(days=UPCOMING_HOLIDAY_WINDOW_DAYS),
            ).order_by("date")
        )
        holiday_lines = "\n".join(f"- {h.name} ({h.date}) [id={h.id}]" for h in upcoming_holidays) or "Yok"

        recent_entries = ContentCalendarEntry.objects.filter(brand=brand).order_by("-scheduled_date")[:10]
        recent_lines = "\n".join(f"- {e.brief[:120]}" for e in recent_entries if e.brief) or "Yok"

        prompt = SUGGESTION_PROMPT.format(
            count=SUGGESTIONS_PER_BATCH,
            brand_context=build_brand_context_text(brand),
            holiday_lines=holiday_lines,
            recent_entries=recent_lines,
        )

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_TEXT_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        _log_usage(brand, batch, response)

        text = "".join(block.text for block in response.content if block.type == "text")
        suggestions = _parse_json_list(text)
        valid_holiday_ids = {str(h.id) for h in upcoming_holidays}

        created = 0
        for suggestion in suggestions:
            holiday_id = suggestion.get("brand_holiday_id")
            if holiday_id not in valid_holiday_ids:
                holiday_id = None
            try:
                ContentCalendarEntry.objects.create(
                    brand=brand,
                    scheduled_date=suggestion["scheduled_date"],
                    content_format=suggestion.get("content_format", "image"),
                    aspect_ratio=suggestion.get("aspect_ratio", "square"),
                    status=ContentCalendarEntry.Status.SUGGESTED,
                    source=ContentCalendarEntry.Source.CLAUDE_SUGGESTION,
                    brief=suggestion.get("brief", ""),
                    brand_holiday_id=holiday_id,
                    suggestion_batch=batch,
                )
                created += 1
            except (KeyError, ValueError):
                logger.warning("Skipping malformed suggestion for batch_id=%s: %s", batch_id, suggestion)

        batch.entry_count = created
        batch.status = CalendarSuggestionBatch.Status.DONE
        batch.completed_at = timezone.now()
        batch.save(update_fields=["entry_count", "status", "completed_at"])

        _notify_batch_ready(batch)
    except Exception:
        logger.exception("Suggestion batch generation failed for batch_id=%s", batch_id)
        batch.status = CalendarSuggestionBatch.Status.FAILED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at"])


def _log_usage(brand, batch, response):
    from usage.models import UsageLog

    UsageLog.objects.create(
        brand=brand,
        provider=UsageLog.Provider.CLAUDE,
        model=CLAUDE_TEXT_MODEL,
        operation=UsageLog.Operation.SUGGESTION_GENERATION,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        suggestion_batch=batch,
    )


def _notify_batch_ready(batch):
    from notifications.tasks import notify_brand_agency

    notify_brand_agency.delay(
        brand_id=str(batch.brand_id),
        notification_type="suggestion_batch_ready",
        title="Yeni içerik önerileri hazır",
        body=f"{batch.entry_count} yeni içerik önerisi takvime eklendi.",
    )


@shared_task
def evaluate_calendar_entry(entry_id, variation_count=3):
    import anthropic

    from brands.services import build_brand_context_text

    from .models import ContentCalendarEntry

    entry = ContentCalendarEntry.objects.select_related("brand").get(id=entry_id)
    brand = entry.brand

    try:
        prompt = VARIATION_PROMPT.format(
            count=variation_count,
            brand_context=build_brand_context_text(brand),
            original_brief=entry.brief,
        )
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=CLAUDE_TEXT_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        from usage.models import UsageLog

        UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.CLAUDE,
            model=CLAUDE_TEXT_MODEL,
            operation=UsageLog.Operation.SUGGESTION_GENERATION,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        text = "".join(block.text for block in response.content if block.type == "text")
        variations = _parse_json_list(text)

        for variation in variations:
            ContentCalendarEntry.objects.create(
                brand=brand,
                scheduled_date=entry.scheduled_date,
                scheduled_time=entry.scheduled_time,
                content_format=entry.content_format,
                aspect_ratio=entry.aspect_ratio,
                status=ContentCalendarEntry.Status.SUGGESTED,
                source=ContentCalendarEntry.Source.CLAUDE_SUGGESTION,
                brief=variation.get("brief", ""),
                brand_holiday=entry.brand_holiday,
                parent_entry=entry,
            )
    except Exception:
        logger.exception("Calendar entry evaluation failed for entry_id=%s", entry_id)
