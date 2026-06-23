from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BrandAIContext, BrandAsset, BrandColor, BrandProfile
from .serializers import (
    ApplyAIContextSerializer,
    BrandAIContextSerializer,
    BrandAssetSerializer,
    BrandColorSerializer,
    BrandProfileSerializer,
)
from .tasks import analyze_brand_asset


def _brands_for_user(user):
    return BrandProfile.objects.filter(
        agency__memberships__user=user, agency__memberships__is_active=True
    ).distinct()


class BrandScopedMixin:
    def get_brand(self):
        return get_object_or_404(_brands_for_user(self.request.user), pk=self.kwargs["brand_id"])


class BrandListCreateView(generics.ListCreateAPIView):
    serializer_class = BrandProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _brands_for_user(self.request.user)

    def perform_create(self, serializer):
        membership = self.request.user.agency_memberships.filter(is_active=True).first()
        serializer.save(agency=membership.agency)


class BrandDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BrandProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _brands_for_user(self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class BrandColorListCreateView(BrandScopedMixin, generics.ListCreateAPIView):
    serializer_class = BrandColorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BrandColor.objects.filter(brand=self.get_brand())

    def perform_create(self, serializer):
        serializer.save(brand=self.get_brand())


class BrandColorDetailView(BrandScopedMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BrandColorSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "color_id"

    def get_queryset(self):
        return BrandColor.objects.filter(brand=self.get_brand())


class BrandAssetListCreateView(BrandScopedMixin, generics.ListCreateAPIView):
    serializer_class = BrandAssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = BrandAsset.objects.filter(brand=self.get_brand())
        asset_type = self.request.query_params.get("asset_type")
        if asset_type:
            qs = qs.filter(asset_type=asset_type)
        return qs

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES["file"]
        asset = serializer.save(
            brand=self.get_brand(),
            original_filename=uploaded_file.name,
            content_type=uploaded_file.content_type or "",
        )
        analyze_brand_asset.delay(str(asset.id))


class BrandAssetDetailView(BrandScopedMixin, generics.DestroyAPIView):
    serializer_class = BrandAssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "asset_id"

    def get_queryset(self):
        return BrandAsset.objects.filter(brand=self.get_brand())


class BrandAssetAnalysisView(BrandScopedMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, brand_id, asset_id):
        asset = get_object_or_404(BrandAsset.objects.filter(brand=self.get_brand()), pk=asset_id)
        return Response(BrandAssetSerializer(asset).data)


class BrandAIContextView(BrandScopedMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, brand_id):
        ai_context, _ = BrandAIContext.objects.get_or_create(brand=self.get_brand())
        return Response(BrandAIContextSerializer(ai_context).data)


class ApplyBrandAIContextView(BrandScopedMixin, generics.GenericAPIView):
    serializer_class = ApplyAIContextSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, brand_id):
        brand = self.get_brand()
        ai_context = get_object_or_404(BrandAIContext, brand=brand)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field = serializer.validated_data["target_field"]
        mode = serializer.validated_data["mode"]

        current = getattr(brand, field)
        if mode == "replace" or not current:
            setattr(brand, field, ai_context.enrichment_summary)
        else:
            setattr(brand, field, f"{current}\n\n{ai_context.enrichment_summary}")
        brand.save(update_fields=[field, "updated_at"])
        return Response(BrandProfileSerializer(brand).data)
