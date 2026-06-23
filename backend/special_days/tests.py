from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from testing import create_agency_with_user, create_brand, make_claude_response

from .models import BrandHoliday, CountryHolidayTemplate, CountryHolidayTemplateEntry
from .tasks import import_brand_holidays, refresh_country_holiday_template


class RefreshCountryHolidayTemplateTests(TestCase):
    def test_creates_official_and_popular_entries(self):
        fake_response = make_claude_response(
            '[{"name": "Sevgililer Gunu", "month": 2, "day": 14, "description": "..."}]'
        )
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            refresh_country_holiday_template("TR")

        template = CountryHolidayTemplate.objects.get(country_code="TR")
        self.assertIsNotNone(template.popular_days_last_refreshed_at)

        official = CountryHolidayTemplateEntry.objects.filter(
            template=template, category=CountryHolidayTemplateEntry.Category.OFFICIAL
        )
        popular = CountryHolidayTemplateEntry.objects.filter(
            template=template, category=CountryHolidayTemplateEntry.Category.POPULAR
        )
        self.assertGreater(official.count(), 0)
        self.assertGreater(popular.count(), 0)
        self.assertTrue(popular.filter(name="Sevgililer Gunu").exists())

    def test_refresh_replaces_rather_than_duplicates(self):
        fake_response = make_claude_response("[]")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            refresh_country_holiday_template("TR")
            first_count = CountryHolidayTemplateEntry.objects.count()
            refresh_country_holiday_template("TR")
            second_count = CountryHolidayTemplateEntry.objects.count()
        self.assertEqual(first_count, second_count)

    def test_unsupported_country_yields_no_official_entries_but_does_not_raise(self):
        fake_response = make_claude_response("[]")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            refresh_country_holiday_template("ZZ")
        template = CountryHolidayTemplate.objects.get(country_code="ZZ")
        self.assertEqual(CountryHolidayTemplateEntry.objects.filter(template=template).count(), 0)


class ImportBrandHolidaysTaskTests(TestCase):
    def test_import_creates_brand_holidays_idempotently(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, country_code="TR")

        fake_response = make_claude_response("[]")
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.messages.create.return_value = fake_response
            current_year = timezone.now().year
            import_brand_holidays(str(brand.id), "TR", [current_year])
            first_count = BrandHoliday.objects.filter(brand=brand).count()
            import_brand_holidays(str(brand.id), "TR", [current_year])
            second_count = BrandHoliday.objects.filter(brand=brand).count()

        self.assertGreater(first_count, 0)
        self.assertEqual(first_count, second_count)

    def test_fresh_template_is_not_refreshed_again(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency, country_code="TR")
        CountryHolidayTemplate.objects.create(
            country_code="TR", popular_days_last_refreshed_at=timezone.now()
        )

        with patch("special_days.tasks.refresh_country_holiday_template") as mock_refresh:
            import_brand_holidays(str(brand.id), "TR", [timezone.now().year])
        mock_refresh.assert_not_called()


class HolidayImportApiTests(APITestCase):
    def test_import_endpoint_dispatches_task(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        self.client.force_authenticate(user=user)
        with patch("special_days.tasks.import_brand_holidays.delay") as mock_delay:
            response = self.client.post(
                f"/api/brands/{brand.id}/holidays/import/",
                {"country_code": "TR", "years": [2026]},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_delay.assert_called_once_with(str(brand.id), "TR", [2026])

    def test_holiday_list_filters_by_category(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        BrandHoliday.objects.create(brand=brand, name="Resmi", date=date.today(), category="official")
        BrandHoliday.objects.create(brand=brand, name="Pop", date=date.today(), category="popular")
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/brands/{brand.id}/holidays/?category=popular")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Pop")
