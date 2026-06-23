from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from brands.models import BrandProfile

from .models import UsageLog
from .serializers import UsageLogSerializer


def _get_brand(user, brand_id):
    qs = BrandProfile.objects.filter(
        agency__memberships__user=user, agency__memberships__is_active=True
    ).distinct()
    return get_object_or_404(qs, pk=brand_id)


class UsageLogListView(generics.ListAPIView):
    serializer_class = UsageLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        qs = UsageLog.objects.filter(brand=brand).order_by("-created_at")

        provider = self.request.query_params.get("provider")
        if provider:
            qs = qs.filter(provider=provider)

        operation = self.request.query_params.get("operation")
        if operation:
            qs = qs.filter(operation=operation)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs


class UsageSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, brand_id):
        brand = _get_brand(request.user, brand_id)
        qs = UsageLog.objects.filter(brand=brand)

        by_provider = list(
            qs.values("provider")
            .annotate(total_cost_usd=Sum("estimated_cost_usd"), call_count=Count("id"))
            .order_by("provider")
        )
        by_operation = list(
            qs.values("operation")
            .annotate(total_cost_usd=Sum("estimated_cost_usd"), call_count=Count("id"))
            .order_by("operation")
        )
        totals = qs.aggregate(total_cost_usd=Sum("estimated_cost_usd"), call_count=Count("id"))

        return Response(
            {
                "totals": totals,
                "by_provider": by_provider,
                "by_operation": by_operation,
            }
        )
