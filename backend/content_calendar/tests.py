from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from special_days.models import BrandHoliday
from testing import create_agency_with_user, create_brand, make_claude_response

from .models import CalendarSuggestionBatch, ContentCalendarEntry
from .tasks import evaluate_calendar_entry, generate_suggestion_batch


def _create_entry(brand, **kwargs):
    defaults = dict(
        scheduled_date=date.today(),
        content_format=ContentCalendarEntry.ContentFormat.IMAGE,
        aspect_ratio=ContentCalendarEntry.AspectRatio.SQUARE,
        source=ContentCalendarEntry.Source.USER_INPUT,
    )
    defaults.update(kwargs)
    return ContentCalendarEntry.objects.create(brand=brand, **defaults)


class CalendarEntryApiTests(APITestCase):
    def test_create_entry_sets_user_input_source(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        self.client.force_authenticate(user=user)
        response = self.client.post(
            f"/api/brands/{brand.id}/calendar/",
            {
                "scheduled_date": "2026-08-01",
                "content_format": "image",
                "aspect_ratio": "square",
                "brief": "Test brief",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["source"], "user_input")
        self.assertEqual(response.data["status"], "draft")

    def test_approve_and_reject_endpoints(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand)
        self.client.force_authenticate(user=user)

        response = self.client.post(f"/api/brands/{brand.id}/calendar/{entry.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertEqual(entry.status, ContentCalendarEntry.Status.APPROVED)

        response = self.client.post(f"/api/brands/{brand.id}/calendar/{entry.id}/reject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertEqual(entry.status, ContentCalendarEntry.Status.REJECTED)

    def test_generate_now_creates_manual_batch_and_dispatches_task(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        self.client.force_authenticate(user=user)
        with patch("content_calendar.tasks.generate_suggestion_batch.delay") as mock_delay:
            response = self.client.post(f"/api/brands/{brand.id}/calendar/suggestions/generate-now/")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["trigger"], "manual")
        mock_delay.assert_called_once()


class EvaluateCalendarEntryTaskTests(TestCase):
    def test_creates_variation_children_linked_to_parent(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        entry = _create_entry(brand, brief="Orijinal fikir")

        fake_response = make_claude_response('[{"brief": "Varyasyon 1"}, {"brief": "Varyasyon 2"}]')
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            evaluate_calendar_entry(str(entry.id), variation_count=2)

        children = ContentCalendarEntry.objects.filter(parent_entry=entry)
        self.assertEqual(children.count(), 2)
        self.assertTrue(all(c.status == ContentCalendarEntry.Status.SUGGESTED for c in children))
        self.assertTrue(all(c.source == ContentCalendarEntry.Source.CLAUDE_SUGGESTION for c in children))


class GenerateSuggestionBatchTaskTests(TestCase):
    def test_creates_entries_and_links_valid_holiday(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        holiday = BrandHoliday.objects.create(
            brand=brand,
            name="Sevgililer Gunu",
            date=date.today() + timedelta(days=5),
            category="popular",
        )
        batch = CalendarSuggestionBatch.objects.create(
            brand=brand, trigger=CalendarSuggestionBatch.Trigger.MANUAL
        )

        fake_json = (
            '[{"brief": "Kahve indirimi", "content_format": "image", '
            '"aspect_ratio": "square", "scheduled_date": "%s", '
            '"brand_holiday_id": "%s"}]' % (holiday.date.isoformat(), holiday.id)
        )
        fake_response = make_claude_response(fake_json)

        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "notifications.tasks.notify_brand_agency.delay"
        ) as mock_notify:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            generate_suggestion_batch(str(batch.id))

        batch.refresh_from_db()
        self.assertEqual(batch.status, CalendarSuggestionBatch.Status.DONE)
        self.assertEqual(batch.entry_count, 1)
        entry = ContentCalendarEntry.objects.get(suggestion_batch=batch)
        self.assertEqual(entry.brand_holiday_id, holiday.id)
        mock_notify.assert_called_once()

    def test_invalid_holiday_id_is_ignored(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        batch = CalendarSuggestionBatch.objects.create(
            brand=brand, trigger=CalendarSuggestionBatch.Trigger.MANUAL
        )
        fake_json = (
            '[{"brief": "Genel oneri", "content_format": "image", '
            '"aspect_ratio": "square", "scheduled_date": "2026-08-10", '
            '"brand_holiday_id": "not-a-real-id"}]'
        )
        fake_response = make_claude_response(fake_json)
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "notifications.tasks.notify_brand_agency.delay"
        ):
            mock_anthropic.return_value.messages.create.return_value = fake_response
            generate_suggestion_batch(str(batch.id))

        entry = ContentCalendarEntry.objects.get(suggestion_batch=batch)
        self.assertIsNone(entry.brand_holiday_id)

    def test_malformed_suggestion_is_skipped_not_fatal(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        batch = CalendarSuggestionBatch.objects.create(
            brand=brand, trigger=CalendarSuggestionBatch.Trigger.MANUAL
        )
        # missing required scheduled_date -> KeyError caught per-suggestion
        fake_response = make_claude_response('[{"brief": "Eksik veri"}]')
        with patch("anthropic.Anthropic") as mock_anthropic, patch(
            "notifications.tasks.notify_brand_agency.delay"
        ):
            mock_anthropic.return_value.messages.create.return_value = fake_response
            generate_suggestion_batch(str(batch.id))

        batch.refresh_from_db()
        self.assertEqual(batch.status, CalendarSuggestionBatch.Status.DONE)
        self.assertEqual(batch.entry_count, 0)
