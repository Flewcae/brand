from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from brands.models import BrandProfile

from .models import BrandHoliday, CountryHolidayTemplate
from .serializers import (
    BrandHolidaySerializer,
    CountryHolidayTemplateSerializer,
    ImportHolidaysSerializer,
)
from .tasks import import_brand_holidays


def _get_brand(user, brand_id):
    qs = BrandProfile.objects.filter(
        agency__memberships__user=user, agency__memberships__is_active=True
    ).distinct()
    return get_object_or_404(qs, pk=brand_id)


class CountryTemplateListView(generics.ListAPIView):
    serializer_class = CountryHolidayTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CountryHolidayTemplate.objects.all().order_by("country_code")


class BrandHolidayImportView(generics.GenericAPIView):
    serializer_class = ImportHolidaysSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id):
        brand = _get_brand(request.user, brand_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        import_brand_holidays.delay(
            str(brand.id),
            serializer.validated_data["country_code"].upper(),
            serializer.validated_data["years"],
        )
        return Response({"detail": "İçe aktarma işlemi başlatıldı."}, status=status.HTTP_202_ACCEPTED)


class BrandHolidayListView(generics.ListAPIView):
    serializer_class = BrandHolidaySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        qs = BrandHoliday.objects.filter(brand=brand).order_by("date")

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs


class BrandHolidayDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BrandHolidaySerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "holiday_id"

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        return BrandHoliday.objects.filter(brand=brand)
