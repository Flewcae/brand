import tempfile
from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from content_calendar.models import ContentCalendarEntry
from testing import create_agency_with_user, create_brand, make_claude_response, make_httpx_response
from usage.models import UsageLog

from .models import GenerationVersion
from .tasks import poll_video_generation, run_image_generation, submit_video_generation

TEMP_MEDIA_ROOT = tempfile.mkdtemp()
_LOCAL_STORAGE = override_settings(
    STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}},
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
)


def _create_entry(brand, content_format="image", aspect_ratio="square", brief="Test brief"):
    return ContentCalendarEntry.objects.create(
        brand=brand,
        scheduled_date=date.today(),
        content_format=content_format,
        aspect_ratio=aspect_ratio,
        source=ContentCalendarEntry.Source.USER_INPUT,
        brief=brief,
    )


@_LOCAL_STORAGE
class RunImageGenerationTaskTests(TestCase):
    def test_successful_generation_marks_done_and_stores_media(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        version = GenerationVersion.objects.create(
            calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.IMAGE
        )

        claude_response = make_claude_response("A warm minimalist coffee shot.")
        grok_response = make_httpx_response(
            json_data={
                "data": [{"url": "https://imgen.x.ai/fake.png"}],
                "usage": {"cost_in_usd_ticks": 700000000},
            }
        )
        download_response = make_httpx_response(content=b"fake-image-bytes")

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", return_value=grok_response
        ), patch("generation.tasks.httpx.get", return_value=download_response), patch(
            "notifications.tasks.send_notification.delay"
        ) as mock_notify:
            mock_anthropic.return_value.messages.create.return_value = claude_response
            run_image_generation(str(version.id))

        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.DONE)
        self.assertTrue(version.media_file.name.endswith(".png"))
        self.assertEqual(version.grok_response_meta["cost_in_usd_ticks"], 700000000)
        mock_notify.assert_not_called()  # no requested_by on this version -> no notification

        usage_log = UsageLog.objects.get(generation_version=version, provider=UsageLog.Provider.GROK)
        self.assertEqual(usage_log.cost_in_usd_ticks, 700000000)
        self.assertEqual(float(usage_log.estimated_cost_usd), 0.07)

    def test_final_prompt_demands_exact_text_rendering_when_text_specified(self):
        """Regression guard: when the brief asks for on-image text, the
        final prompt actually sent to Grok must always carry a deterministic,
        code-enforced 'render exactly as written' clause -- never left to
        the LLM's discretion, since image models routinely garble text and
        Claude won't reliably restate this instruction on its own."""
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand, brief='Kahve fiyatı: "20 TL" yazsın')
        version = GenerationVersion.objects.create(
            calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.IMAGE
        )

        claude_response = make_claude_response(
            '{"prompt": "A coffee cup with a price tag.", "on_image_text": "20 TL"}'
        )
        grok_response = make_httpx_response(
            json_data={"data": [{"url": "https://imgen.x.ai/fake.png"}], "usage": {}}
        )
        download_response = make_httpx_response(content=b"fake-image-bytes")

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", return_value=grok_response
        ), patch("generation.tasks.httpx.get", return_value=download_response), patch(
            "notifications.tasks.send_notification.delay"
        ):
            mock_anthropic.return_value.messages.create.return_value = claude_response
            run_image_generation(str(version.id))

        version.refresh_from_db()
        self.assertIn(
            'Render the text "20 TL" exactly as written, correctly spelled',
            version.claude_prompt_text,
        )

    def test_final_prompt_forbids_text_when_none_specified(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand, brief="Sicak bir kahve fotosu")
        version = GenerationVersion.objects.create(
            calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.IMAGE
        )

        claude_response = make_claude_response(
            '{"prompt": "A warm coffee photo.", "on_image_text": null}'
        )
        grok_response = make_httpx_response(
            json_data={"data": [{"url": "https://imgen.x.ai/fake.png"}], "usage": {}}
        )
        download_response = make_httpx_response(content=b"fake-image-bytes")

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", return_value=grok_response
        ), patch("generation.tasks.httpx.get", return_value=download_response), patch(
            "notifications.tasks.send_notification.delay"
        ):
            mock_anthropic.return_value.messages.create.return_value = claude_response
            run_image_generation(str(version.id))

        version.refresh_from_db()
        self.assertIn("Do not include any text", version.claude_prompt_text)

    def test_failed_grok_call_marks_failed_and_notifies_requester(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        version = GenerationVersion.objects.create(
            calendar_entry=entry,
            version_number=1,
            media_type=GenerationVersion.MediaType.IMAGE,
            requested_by=user,
        )

        claude_response = make_claude_response("A prompt.")

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", side_effect=RuntimeError("network down")
        ), patch("notifications.tasks.send_notification.delay") as mock_notify:
            mock_anthropic.return_value.messages.create.return_value = claude_response
            run_image_generation(str(version.id))

        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.FAILED)
        self.assertIn("network down", version.error_message)
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.kwargs["notification_type"], "generation_failed")


@_LOCAL_STORAGE
class SubmitVideoGenerationTaskTests(TestCase):
    def test_successful_submit_sets_processing_status(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand, content_format="video", aspect_ratio="landscape")
        version = GenerationVersion.objects.create(
            calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.VIDEO
        )

        claude_response = make_claude_response("A video prompt.")
        grok_response = make_httpx_response(json_data={"request_id": "req-123"})

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", return_value=grok_response
        ):
            mock_anthropic.return_value.messages.create.return_value = claude_response
            submit_video_generation(str(version.id))

        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.PROCESSING)
        self.assertEqual(version.grok_request_id, "req-123")

    def test_submit_failure_marks_failed(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand, content_format="video", aspect_ratio="landscape")
        version = GenerationVersion.objects.create(
            calendar_entry=entry,
            version_number=1,
            media_type=GenerationVersion.MediaType.VIDEO,
            requested_by=user,
        )
        claude_response = make_claude_response("A video prompt.")
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "generation.tasks.httpx.post", side_effect=RuntimeError("xai down")
        ), patch("notifications.tasks.send_notification.delay") as mock_notify:
            mock_anthropic.return_value.messages.create.return_value = claude_response
            submit_video_generation(str(version.id))

        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.FAILED)
        mock_notify.assert_called_once()


@_LOCAL_STORAGE
class PollVideoGenerationTaskTests(TestCase):
    def _processing_version(self, brand):
        entry = _create_entry(brand, content_format="video", aspect_ratio="landscape")
        return GenerationVersion.objects.create(
            calendar_entry=entry,
            version_number=1,
            media_type=GenerationVersion.MediaType.VIDEO,
            status=GenerationVersion.Status.PROCESSING,
            grok_request_id="req-123",
        )

    def test_pending_status_leaves_version_unchanged(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        version = self._processing_version(brand)
        response = make_httpx_response(json_data={"status": "pending"})
        with patch("generation.tasks.httpx.get", return_value=response):
            poll_video_generation(str(version.id))
        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.PROCESSING)

    def test_done_status_downloads_and_marks_done(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        version = self._processing_version(brand)

        status_response = make_httpx_response(
            json_data={
                "status": "done",
                "url": "https://imgen.x.ai/fake.mp4",
                "usage": {"cost_in_usd_ticks": 5000000000},
            }
        )
        download_response = make_httpx_response(content=b"fake-video-bytes")

        with patch(
            "generation.tasks.httpx.get", side_effect=[status_response, download_response]
        ), patch("notifications.tasks.send_notification.delay"):
            poll_video_generation(str(version.id))

        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.DONE)
        self.assertTrue(version.media_file.name.endswith(".mp4"))

        usage_log = UsageLog.objects.get(generation_version=version, provider=UsageLog.Provider.GROK)
        self.assertEqual(usage_log.cost_in_usd_ticks, 5000000000)

    def test_failed_status_marks_failed_with_error_message(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        version = self._processing_version(brand)
        response = make_httpx_response(json_data={"status": "failed", "error": "Moderation rejected"})
        with patch("generation.tasks.httpx.get", return_value=response), patch(
            "notifications.tasks.send_notification.delay"
        ):
            poll_video_generation(str(version.id))
        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.FAILED)
        self.assertEqual(version.error_message, "Moderation rejected")

    def test_transient_request_error_leaves_status_processing_for_retry(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        version = self._processing_version(brand)
        with patch("generation.tasks.httpx.get", side_effect=RuntimeError("timeout")):
            poll_video_generation(str(version.id))
        version.refresh_from_db()
        self.assertEqual(version.status, GenerationVersion.Status.PROCESSING)


@_LOCAL_STORAGE
class GenerationVersionApiTests(APITestCase):
    def test_unique_version_number_per_entry_constraint(self):
        from django.db import IntegrityError, transaction

        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        GenerationVersion.objects.create(
            calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.IMAGE
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GenerationVersion.objects.create(
                    calendar_entry=entry, version_number=1, media_type=GenerationVersion.MediaType.IMAGE
                )

    def test_trigger_endpoint_dispatches_image_task(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        self.client.force_authenticate(user=user)

        with patch("generation.tasks.run_image_generation.delay") as mock_delay:
            response = self.client.post(f"/api/brands/{brand.id}/calendar/{entry.id}/generations/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_delay.assert_called_once()
