from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from testing import create_agency_with_user, create_brand

from .models import UsageLog


class UsageLogCostComputationTests(TestCase):
    def test_estimated_cost_computed_from_ticks(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        log = UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.GROK,
            model="grok-imagine-image-quality",
            operation=UsageLog.Operation.IMAGE_GENERATION,
            cost_in_usd_ticks=700_000_000,
        )
        self.assertEqual(log.estimated_cost_usd, Decimal("0.0700"))

    def test_no_ticks_leaves_estimated_cost_null(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        log = UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.CLAUDE,
            model="claude-sonnet-4-6",
            operation=UsageLog.Operation.PROMPT_GENERATION,
            input_tokens=100,
            output_tokens=50,
        )
        self.assertIsNone(log.estimated_cost_usd)

    def test_explicit_estimated_cost_is_not_overwritten(self):
        _, agency = create_agency_with_user()
        brand = create_brand(agency)
        log = UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.GROK,
            model="m",
            operation=UsageLog.Operation.IMAGE_GENERATION,
            cost_in_usd_ticks=700_000_000,
            estimated_cost_usd=Decimal("1.2345"),
        )
        self.assertEqual(log.estimated_cost_usd, Decimal("1.2345"))


class UsageSummaryApiTests(APITestCase):
    def test_summary_aggregates_by_provider(self):
        user, agency = create_agency_with_user()
        brand = create_brand(agency)
        UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.GROK,
            model="m",
            operation=UsageLog.Operation.IMAGE_GENERATION,
            cost_in_usd_ticks=700_000_000,
        )
        UsageLog.objects.create(
            brand=brand,
            provider=UsageLog.Provider.GROK,
            model="m",
            operation=UsageLog.Operation.IMAGE_GENERATION,
            cost_in_usd_ticks=300_000_000,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/brands/{brand.id}/usage/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grok_row = next(r for r in response.data["by_provider"] if r["provider"] == "grok")
        self.assertEqual(grok_row["call_count"], 2)
        self.assertEqual(grok_row["total_cost_usd"], Decimal("0.1000"))

    def test_usage_list_scoped_to_brand(self):
        user, agency = create_agency_with_user()
        brand1 = create_brand(agency, slug="brand1")
        brand2 = create_brand(agency, slug="brand2")
        UsageLog.objects.create(
            brand=brand1, provider=UsageLog.Provider.CLAUDE, model="m",
            operation=UsageLog.Operation.PROMPT_GENERATION,
        )
        UsageLog.objects.create(
            brand=brand2, provider=UsageLog.Provider.CLAUDE, model="m",
            operation=UsageLog.Operation.PROMPT_GENERATION,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/brands/{brand1.id}/usage/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
