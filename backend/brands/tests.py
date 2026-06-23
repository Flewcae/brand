import tempfile
from unittest.mock import patch

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from testing import create_agency_with_user, create_brand, make_claude_response

from .models import BrandAIContext, BrandAsset
from .tasks import analyze_brand_asset

TEMP_MEDIA_ROOT = tempfile.mkdtemp()
_LOCAL_STORAGE = override_settings(
    STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}},
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
)


class BrandProfileConstraintTests(TestCase):
    def test_unique_slug_per_agency(self):
        _, agency = create_agency_with_user()
        create_brand(agency, slug="acme")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                create_brand(agency, name="Acme 2", slug="acme")

    def test_same_slug_allowed_across_different_agencies(self):
        _, agency1 = create_agency_with_user(email="a@example.com")
        _, agency2 = create_agency_with_user(email="b@example.com", agency_name="Other Agency")
        create_brand(agency1, slug="acme")
        create_brand(agency2, slug="acme")  # should not raise


class BrandApiScopingTests(APITestCase):
    def test_brand_list_scoped_to_own_agency(self):
        user1, agency1 = create_agency_with_user(email="u1@example.com")
        _, agency2 = create_agency_with_user(email="u2@example.com", agency_name="Other")
        create_brand(agency1, slug="brand1")
        create_brand(agency2, slug="brand2")

        self.client.force_authenticate(user=user1)
        response = self.client.get("/api/brands/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [b["slug"] for b in response.data["results"]]
        self.assertEqual(slugs, ["brand1"])

    def test_other_agencys_brand_detail_returns_404(self):
        user1, agency1 = create_agency_with_user(email="u1@example.com")
        _, agency2 = create_agency_with_user(email="u2@example.com", agency_name="Other")
        other_brand = create_brand(agency2, slug="not-mine")

        self.client.force_authenticate(user=user1)
        response = self.client.get(f"/api/brands/{other_brand.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@_LOCAL_STORAGE
class AnalyzeBrandAssetTaskTests(TestCase):
    def test_analyze_image_asset_updates_ai_context_not_brand_fields(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, style_description="Orijinal stil")
        asset = BrandAsset.objects.create(
            brand=brand,
            asset_type=BrandAsset.AssetType.LOGO,
            file=SimpleUploadedFile("logo.png", b"fake-png-bytes", content_type="image/png"),
            original_filename="logo.png",
            content_type="image/png",
        )

        fake_response = make_claude_response(
            '{"style_keywords": ["minimal"], "mood_descriptors": ["warm"], '
            '"visual_donts": ["clutter"], "summary": "Sicak ve minimalist bir marka."}'
        )

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            analyze_brand_asset(str(asset.id))

        asset.refresh_from_db()
        self.assertEqual(asset.analysis_status, BrandAsset.AnalysisStatus.DONE)
        self.assertEqual(asset.claude_vision_analysis["style_keywords"], ["minimal"])

        brand.refresh_from_db()
        self.assertEqual(brand.style_description, "Orijinal stil")  # never auto-overwritten

        ai_context = BrandAIContext.objects.get(brand=brand)
        self.assertEqual(ai_context.style_keywords, ["minimal"])
        self.assertIn(asset, ai_context.source_assets.all())

    def test_analyze_pdf_asset_converts_pages_to_images(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        doc = fitz.open()
        doc.new_page()
        pdf_bytes = doc.tobytes()

        asset = BrandAsset.objects.create(
            brand=brand,
            asset_type=BrandAsset.AssetType.IDENTITY_DOCUMENT,
            file=SimpleUploadedFile("guide.pdf", pdf_bytes, content_type="application/pdf"),
            content_type="application/pdf",
        )
        fake_response = make_claude_response(
            '{"summary": "ok", "style_keywords": [], "mood_descriptors": [], "visual_donts": []}'
        )
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            analyze_brand_asset(str(asset.id))

        asset.refresh_from_db()
        self.assertEqual(asset.analysis_status, BrandAsset.AnalysisStatus.DONE)
        self.assertEqual(len(asset.page_images), 1)

    def test_analyze_asset_marks_failed_on_error(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        asset = BrandAsset.objects.create(
            brand=brand,
            asset_type=BrandAsset.AssetType.LOGO,
            file=SimpleUploadedFile("logo.png", b"fake-png-bytes", content_type="image/png"),
            content_type="image/png",
        )
        with patch("anthropic.Anthropic", side_effect=RuntimeError("boom")):
            analyze_brand_asset(str(asset.id))
        asset.refresh_from_db()
        self.assertEqual(asset.analysis_status, BrandAsset.AnalysisStatus.FAILED)


@_LOCAL_STORAGE
class BrandAssetUploadApiTests(APITestCase):
    def test_upload_dispatches_analysis_task(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        self.client.force_authenticate(user=user)

        with patch("brands.tasks.analyze_brand_asset.delay") as mock_delay:
            response = self.client.post(
                f"/api/brands/{brand.id}/assets/",
                {
                    "asset_type": "logo",
                    "file": SimpleUploadedFile("logo.png", b"bytes", content_type="image/png"),
                },
                format="multipart",
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_delay.assert_called_once()


class ApplyAIContextApiTests(APITestCase):
    def test_apply_appends_summary_to_chosen_field(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency, style_description="Mevcut metin")
        BrandAIContext.objects.create(brand=brand, enrichment_summary="AI onerisi.")

        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/api/brands/{brand.id}/ai-context/apply/",
            {"target_field": "style_description", "mode": "append"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        brand.refresh_from_db()
        self.assertIn("Mevcut metin", brand.style_description)
        self.assertIn("AI onerisi.", brand.style_description)

    def test_apply_replace_mode_overwrites_field(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency, style_description="Eski metin")
        BrandAIContext.objects.create(brand=brand, enrichment_summary="Yeni AI metni.")

        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/api/brands/{brand.id}/ai-context/apply/",
            {"target_field": "style_description", "mode": "replace"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        brand.refresh_from_db()
        self.assertEqual(brand.style_description, "Yeni AI metni.")
