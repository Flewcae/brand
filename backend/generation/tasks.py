import json
import logging
import re

import httpx
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

CLAUDE_TEXT_MODEL = "claude-sonnet-4-6"
XAI_API_BASE = "https://api.x.ai/v1"
GROK_IMAGE_MODEL = "grok-imagine-image-quality"
GROK_VIDEO_MODEL = "grok-imagine-video"

ASPECT_RATIO_MAP = {
    "landscape": "16:9",
    "portrait": "9:16",
    "square": "1:1",
}

# Appended in code, never left to the LLM to remember -- image/video models
# routinely garble on-image text, so the render-exactly-as-written clause
# must always be present (or the explicit no-text clause) regardless of
# whether Claude's own prose happens to restate it.
TEXT_RENDER_CLAUSE = (
    'Render the text "{text}" exactly as written, correctly spelled, fully '
    "legible, with clean accurate typography -- do not distort, garble, "
    "duplicate, or misspell any character."
)
NO_TEXT_CLAUSE = (
    "Do not include any text, typography, captions, signage, or watermarks "
    "anywhere in the image/video."
)

PROMPT_WRITING_INSTRUCTIONS = (
    "Aşağıdaki marka bağlamını ve içerik brief'ini kullanarak, bir görsel/"
    "video üretim modeli için optimize edilmiş, İngilizce bir üretim "
    "prompt'u yaz.\n\n"
    "Brief'te görselde/videoda GÖRÜNMESİ istenen bir slogan, fiyat, tarih, "
    "isim veya başka bir yazı/ifade varsa, bu metni `on_image_text` alanına "
    "harf harf BİREBİR aynı şekilde yaz (Türkçe karakterler dahil: ı, İ, ş, "
    "ğ, ü, ö, ç -- değiştirme, sadeleştirme veya İngilizceye çevirme). "
    "Brief'te görselde gözükmesi gereken bir metin YOKSA `on_image_text`'i "
    "null yap -- kendiliğinden slogan/yazı icat ETME. Metnin render "
    "doğruluğu kod tarafında ayrıca garanti edilecek, bunun için prompt "
    "icine ekstra bir seyler eklemene gerek yok; sadece sahneyi tasvir et.\n\n"
    "Sadece şu şemaya uyan tek bir JSON nesnesi döndür, başka hiçbir metin "
    'ekleme: {{"prompt": "...", "on_image_text": "..." veya null}}\n\n'
    "{brand_context}\n{holiday_line}\nİçerik brief'i: {brief}\n"
    "Format: {aspect_ratio}"
)


def _xai_headers():
    return {
        "Authorization": f"Bearer {settings.XAI_API_KEY}",
        "Content-Type": "application/json",
    }


def _parse_prompt_response(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return text.strip(), None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return text.strip(), None
    return data.get("prompt", text).strip(), data.get("on_image_text") or None


def _build_grok_prompt(version):
    import anthropic

    from brands.services import build_brand_context_text

    entry = version.calendar_entry
    brand = entry.brand

    holiday_line = f"Özel gün bağlamı: {entry.brand_holiday.name}" if entry.brand_holiday_id else ""
    prompt_request = PROMPT_WRITING_INSTRUCTIONS.format(
        brand_context=build_brand_context_text(brand),
        holiday_line=holiday_line,
        brief=entry.brief,
        aspect_ratio=entry.aspect_ratio,
    )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLAUDE_TEXT_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt_request}],
    )
    _log_claude_usage(brand, version, response)
    raw_text = "".join(block.text for block in response.content if block.type == "text")
    base_prompt, on_image_text = _parse_prompt_response(raw_text)

    text_clause = TEXT_RENDER_CLAUSE.format(text=on_image_text) if on_image_text else NO_TEXT_CLAUSE
    return f"{base_prompt} {text_clause}"


def _log_claude_usage(brand, version, response):
    from usage.models import UsageLog

    UsageLog.objects.create(
        brand=brand,
        provider=UsageLog.Provider.CLAUDE,
        model=CLAUDE_TEXT_MODEL,
        operation=UsageLog.Operation.PROMPT_GENERATION,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        generation_version=version,
    )


def _log_grok_usage(brand, version, model, operation, cost_in_usd_ticks):
    from usage.models import UsageLog

    UsageLog.objects.create(
        brand=brand,
        provider=UsageLog.Provider.GROK,
        model=model,
        operation=operation,
        cost_in_usd_ticks=cost_in_usd_ticks,
        generation_version=version,
    )


def _notify_generation_result(version, success):
    from notifications.tasks import send_notification

    if not version.requested_by_id:
        return
    entry = version.calendar_entry
    if success:
        title = "İçerik üretimi tamamlandı"
        body = f"{entry.brief[:80]} için üretim hazır."
        notification_type = "generation_done"
    else:
        title = "İçerik üretimi başarısız oldu"
        body = version.error_message[:200] or "Üretim sırasında bir hata oluştu."
        notification_type = "generation_failed"

    send_notification.delay(
        user_id=str(version.requested_by_id),
        brand_id=str(entry.brand_id),
        notification_type=notification_type,
        title=title,
        body=body,
        related_calendar_entry_id=str(entry.id),
        related_generation_version_id=str(version.id),
    )


@shared_task
def run_image_generation(version_id):
    from .models import GenerationVersion

    version = GenerationVersion.objects.select_related("calendar_entry__brand").get(id=version_id)
    entry = version.calendar_entry
    brand = entry.brand

    try:
        prompt_text = _build_grok_prompt(version)
        version.claude_prompt_text = prompt_text
        version.status = GenerationVersion.Status.PROMPT_READY
        version.save(update_fields=["claude_prompt_text", "status"])

        payload = {
            "model": GROK_IMAGE_MODEL,
            "prompt": prompt_text,
            "aspect_ratio": ASPECT_RATIO_MAP.get(entry.aspect_ratio, "1:1"),
            "n": 1,
            "resolution": "2k",
            "response_format": "url",
        }
        version.grok_request_payload = payload
        version.status = GenerationVersion.Status.SUBMITTED
        version.save(update_fields=["grok_request_payload", "status"])

        response = httpx.post(
            f"{XAI_API_BASE}/images/generations",
            headers=_xai_headers(),
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        image_url = data["data"][0]["url"]
        cost_ticks = (data.get("usage") or {}).get("cost_in_usd_ticks")

        # Always re-host Grok's media in our own storage: image URLs from
        # xAI's own storage_options are only guaranteed for 30 days, and
        # video URL longevity isn't documented at all -- never rely on it.
        media_bytes = httpx.get(image_url, timeout=60).content
        version.media_file.save(f"{version.id}.png", ContentFile(media_bytes), save=False)
        version.grok_response_meta = {"cost_in_usd_ticks": cost_ticks}
        version.status = GenerationVersion.Status.DONE
        version.save(update_fields=["media_file", "grok_response_meta", "status", "updated_at"])

        _log_grok_usage(brand, version, GROK_IMAGE_MODEL, "image_generation", cost_ticks)
        _notify_generation_result(version, success=True)
    except Exception as exc:
        logger.exception("Image generation failed for version_id=%s", version_id)
        version.status = GenerationVersion.Status.FAILED
        version.error_message = str(exc)
        version.save(update_fields=["status", "error_message", "updated_at"])
        _notify_generation_result(version, success=False)


@shared_task
def submit_video_generation(version_id):
    from .models import GenerationVersion

    version = GenerationVersion.objects.select_related("calendar_entry__brand").get(id=version_id)

    try:
        prompt_text = _build_grok_prompt(version)
        version.claude_prompt_text = prompt_text
        version.status = GenerationVersion.Status.PROMPT_READY
        version.save(update_fields=["claude_prompt_text", "status"])

        # Deliberately minimal -- confirmed empirically against the live API:
        # "grok-imagine-video" is the text-to-video model ("grok-imagine-
        # video-1.5" rejects text-only prompts with "Text-to-video is not
        # supported for this model" -- it's image-to-video only). The old
        # hardcoded "resolution": "1080p" was also rejected ("1080p video
        # resolution is not available for this model"). Rather than guess
        # another enum value with unconfirmed support, omit both resolution
        # and aspect_ratio and let xAI apply its own defaults.
        payload = {
            "model": GROK_VIDEO_MODEL,
            "prompt": prompt_text,
            "duration": 8,
        }
        version.grok_request_payload = payload
        version.status = GenerationVersion.Status.SUBMITTED
        version.save(update_fields=["grok_request_payload", "status"])

        response = httpx.post(
            f"{XAI_API_BASE}/videos/generations",
            headers=_xai_headers(),
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        version.grok_request_id = data["request_id"]
        version.status = GenerationVersion.Status.PROCESSING
        version.save(update_fields=["grok_request_id", "status", "updated_at"])
    except Exception as exc:
        logger.exception("Video submission failed for version_id=%s", version_id)
        version.status = GenerationVersion.Status.FAILED
        version.error_message = str(exc)
        version.save(update_fields=["status", "error_message", "updated_at"])
        _notify_generation_result(version, success=False)


@shared_task
def poll_pending_video_generations():
    from .models import GenerationVersion

    pending_ids = GenerationVersion.objects.filter(
        media_type=GenerationVersion.MediaType.VIDEO,
        status=GenerationVersion.Status.PROCESSING,
    ).values_list("id", flat=True)
    for version_id in pending_ids:
        poll_video_generation.delay(str(version_id))


@shared_task
def poll_video_generation(version_id):
    from .models import GenerationVersion

    version = GenerationVersion.objects.select_related("calendar_entry__brand").get(id=version_id)
    if version.status != GenerationVersion.Status.PROCESSING:
        return

    brand = version.calendar_entry.brand

    try:
        response = httpx.get(
            f"{XAI_API_BASE}/videos/{version.grok_request_id}",
            headers=_xai_headers(),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        remote_status = data.get("status")

        if remote_status == "pending":
            return  # leave as processing, scanner will retry next cycle

        if remote_status == "done":
            # Documented response shape nests the result under "video": {"url": ...}
            # rather than a top-level "url" -- accept either defensively.
            video_url = (data.get("video") or {}).get("url") or data.get("url")
            cost_ticks = (data.get("usage") or {}).get("cost_in_usd_ticks")
            media_bytes = httpx.get(video_url, timeout=120).content
            version.media_file.save(f"{version.id}.mp4", ContentFile(media_bytes), save=False)
            version.grok_response_meta = {"cost_in_usd_ticks": cost_ticks}
            version.status = GenerationVersion.Status.DONE
            version.save(update_fields=["media_file", "grok_response_meta", "status", "updated_at"])
            _log_grok_usage(brand, version, GROK_VIDEO_MODEL, "video_generation", cost_ticks)
            _notify_generation_result(version, success=True)
        elif remote_status in ("failed", "expired"):
            version.status = GenerationVersion.Status.FAILED
            version.error_message = data.get("error") or f"Grok video generation {remote_status}."
            version.save(update_fields=["status", "error_message", "updated_at"])
            _notify_generation_result(version, success=False)
    except Exception:
        # Transient poll error: leave status as processing so the next
        # scanner cycle retries -- do not mark failed on our own request error.
        logger.exception("Video poll request failed for version_id=%s", version_id)
