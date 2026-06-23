from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from brands.models import BrandProfile
from content_calendar.models import ContentCalendarEntry

from .models import GenerationVersion
from .serializers import GenerationVersionSerializer
from .tasks import run_image_generation, submit_video_generation


def _get_calendar_entry(user, brand_id, entry_id):
    brand = get_object_or_404(
        BrandProfile.objects.filter(
            agency__memberships__user=user, agency__memberships__is_active=True
        ).distinct(),
        pk=brand_id,
    )
    return get_object_or_404(ContentCalendarEntry, pk=entry_id, brand=brand)


class GenerationListCreateView(generics.ListCreateAPIView):
    serializer_class = GenerationVersionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        entry = _get_calendar_entry(self.request.user, self.kwargs["brand_id"], self.kwargs["entry_id"])
        return GenerationVersion.objects.filter(calendar_entry=entry).order_by("-version_number")

    def create(self, request, *args, **kwargs):
        entry = _get_calendar_entry(request.user, self.kwargs["brand_id"], self.kwargs["entry_id"])
        next_version = GenerationVersion.objects.filter(calendar_entry=entry).count() + 1
        version = GenerationVersion.objects.create(
            calendar_entry=entry,
            version_number=next_version,
            media_type=entry.content_format,
            requested_by=request.user,
        )
        if entry.content_format == ContentCalendarEntry.ContentFormat.IMAGE:
            run_image_generation.delay(str(version.id))
        else:
            submit_video_generation.delay(str(version.id))
        return Response(GenerationVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class GenerationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = GenerationVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "version_id"

    def get_queryset(self):
        entry = _get_calendar_entry(self.request.user, self.kwargs["brand_id"], self.kwargs["entry_id"])
        return GenerationVersion.objects.filter(calendar_entry=entry)


class SelectGenerationVersionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id, entry_id, version_id):
        entry = _get_calendar_entry(request.user, brand_id, entry_id)
        version = get_object_or_404(GenerationVersion, pk=version_id, calendar_entry=entry)
        entry.active_generation_version = version
        entry.save(update_fields=["active_generation_version", "updated_at"])
        return Response(GenerationVersionSerializer(version).data)
