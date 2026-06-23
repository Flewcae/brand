import base64
import json
import logging
import re

import fitz  # PyMuPDF
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)

CLAUDE_VISION_MODEL = "claude-sonnet-4-6"

VISION_PROMPT = (
    "Bu görsel(ler), bir markanın logosu veya kurumsal kimlik dökümanıdır. "
    "Markanın görsel stilini (minimalist/maksimalist, renk eğilimi, "
    "tipografi izlenimi, genel ruh hali) analiz et. Sadece şu şemaya uyan "
    "tek bir JSON nesnesi döndür, başka hiçbir metin ekleme: "
    '{"style_keywords": [...], "mood_descriptors": [...], '
    '"visual_donts": [...], "summary": "kısa paragraf, Türkçe"}'
)


@shared_task
def analyze_brand_asset(asset_id):
    from .models import BrandAsset

    asset = BrandAsset.objects.select_related("brand").get(id=asset_id)
    asset.analysis_status = BrandAsset.AnalysisStatus.PROCESSING
    asset.save(update_fields=["analysis_status"])

    try:
        image_sources = _prepare_image_sources(asset)
        analysis = _run_claude_vision_analysis(asset, image_sources)
        asset.claude_vision_analysis = analysis
        asset.analysis_status = BrandAsset.AnalysisStatus.DONE
        asset.save(update_fields=["claude_vision_analysis", "analysis_status", "page_images"])
        _update_brand_ai_context(asset, analysis)
    except Exception:
        logger.exception("Brand asset analysis failed for asset_id=%s", asset_id)
        asset.analysis_status = BrandAsset.AnalysisStatus.FAILED
        asset.save(update_fields=["analysis_status"])


def _prepare_image_sources(asset):
    """Returns [(bytes, mime_type), ...] Claude vision can consume directly.
    PDFs are rendered page-by-page to PNG via PyMuPDF (no system dependency,
    unlike pdf2image/poppler); plain images pass through unchanged."""
    if asset.content_type == "application/pdf":
        with asset.file.open("rb") as fh:
            pdf_bytes = fh.read()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_image_urls = []
        sources = []
        for page_index in range(len(doc)):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")
            storage_path = (
                f"brands/{asset.brand_id}/assets/identity_document/"
                f"pages/{asset.id}/page-{page_index + 1}.png"
            )
            saved_path = asset.file.storage.save(storage_path, ContentFile(png_bytes))
            page_image_urls.append(asset.file.storage.url(saved_path))
            sources.append((png_bytes, "image/png"))
        asset.page_images = page_image_urls
        return sources

    with asset.file.open("rb") as fh:
        raw_bytes = fh.read()
    return [(raw_bytes, asset.content_type or "image/png")]


def _run_claude_vision_analysis(asset, image_sources):
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    content = [{"type": "text", "text": VISION_PROMPT}]
    for raw_bytes, mime_type in image_sources:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": base64.standard_b64encode(raw_bytes).decode("utf-8"),
                },
            }
        )

    response = client.messages.create(
        model=CLAUDE_VISION_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    _log_usage(asset, response)

    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json_response(text)


def _log_usage(asset, response):
    from usage.models import UsageLog

    UsageLog.objects.create(
        brand=asset.brand,
        provider=UsageLog.Provider.CLAUDE,
        model=CLAUDE_VISION_MODEL,
        operation=UsageLog.Operation.VISION_ANALYSIS,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        brand_asset=asset,
    )


def _parse_json_response(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    fallback = {"summary": text.strip(), "style_keywords": [], "mood_descriptors": [], "visual_donts": []}
    if not match:
        return fallback
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return fallback


def _update_brand_ai_context(asset, analysis):
    from .models import BrandAIContext

    ai_context, _ = BrandAIContext.objects.get_or_create(brand=asset.brand)
    ai_context.style_keywords = analysis.get("style_keywords", [])
    ai_context.mood_descriptors = analysis.get("mood_descriptors", [])
    ai_context.visual_donts = analysis.get("visual_donts", [])
    ai_context.enrichment_summary = analysis.get("summary", "")
    ai_context.last_enriched_at = timezone.now()
    ai_context.save()
    ai_context.source_assets.add(asset)
