from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from brands.models import BrandProfile

from .models import CalendarSuggestionBatch, ContentCalendarEntry
from .serializers import (
    CalendarSuggestionBatchSerializer,
    ContentCalendarEntrySerializer,
    MoreLikeThisSerializer,
)
from .tasks import evaluate_calendar_entry, generate_suggestion_batch


def _get_brand(user, brand_id):
    qs = BrandProfile.objects.filter(
        agency__memberships__user=user, agency__memberships__is_active=True
    ).distinct()
    return get_object_or_404(qs, pk=brand_id)


def _get_entry(user, brand_id, entry_id):
    brand = _get_brand(user, brand_id)
    return get_object_or_404(ContentCalendarEntry, pk=entry_id, brand=brand)


class CalendarEntryListCreateView(generics.ListCreateAPIView):
    serializer_class = ContentCalendarEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        qs = ContentCalendarEntry.objects.filter(brand=brand).order_by("scheduled_date")

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        content_format = self.request.query_params.get("content_format")
        if content_format:
            qs = qs.filter(content_format=content_format)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(scheduled_date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(scheduled_date__lte=date_to)

        return qs

    def perform_create(self, serializer):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        serializer.save(brand=brand, source=ContentCalendarEntry.Source.USER_INPUT)


class CalendarEntryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContentCalendarEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        return ContentCalendarEntry.objects.filter(brand=brand)


class EvaluateEntryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id, entry_id):
        entry = _get_entry(request.user, brand_id, entry_id)
        evaluate_calendar_entry.delay(str(entry.id), variation_count=3)
        return Response({"detail": "Değerlendirme başlatıldı."}, status=status.HTTP_202_ACCEPTED)


class ApproveEntryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id, entry_id):
        entry = _get_entry(request.user, brand_id, entry_id)
        entry.status = ContentCalendarEntry.Status.APPROVED
        entry.save(update_fields=["status", "updated_at"])
        return Response(ContentCalendarEntrySerializer(entry).data)


class RejectEntryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id, entry_id):
        entry = _get_entry(request.user, brand_id, entry_id)
        entry.status = ContentCalendarEntry.Status.REJECTED
        entry.save(update_fields=["status", "updated_at"])
        return Response(ContentCalendarEntrySerializer(entry).data)


class MoreLikeThisView(generics.GenericAPIView):
    serializer_class = MoreLikeThisSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id, entry_id):
        entry = _get_entry(request.user, brand_id, entry_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluate_calendar_entry.delay(str(entry.id), variation_count=serializer.validated_data["count"])
        return Response({"detail": "Yeni varyasyonlar isteniyor."}, status=status.HTTP_202_ACCEPTED)


class GenerateSuggestionsNowView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id):
        brand = _get_brand(request.user, brand_id)
        batch = CalendarSuggestionBatch.objects.create(
            brand=brand,
            trigger=CalendarSuggestionBatch.Trigger.MANUAL,
            requested_by=request.user,
        )
        generate_suggestion_batch.delay(str(batch.id))
        return Response(CalendarSuggestionBatchSerializer(batch).data, status=status.HTTP_202_ACCEPTED)


class SuggestionBatchDetailView(generics.RetrieveAPIView):
    serializer_class = CalendarSuggestionBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "batch_id"

    def get_queryset(self):
        brand = _get_brand(self.request.user, self.kwargs["brand_id"])
        return CalendarSuggestionBatch.objects.filter(brand=brand)
