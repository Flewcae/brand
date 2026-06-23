from django.urls import path

from . import views

urlpatterns = [
    path("brands/", views.BrandListCreateView.as_view(), name="brand-list"),
    path("brands/<uuid:pk>/", views.BrandDetailView.as_view(), name="brand-detail"),
    path(
        "brands/<uuid:brand_id>/colors/",
        views.BrandColorListCreateView.as_view(),
        name="brand-colors",
    ),
    path(
        "brands/<uuid:brand_id>/colors/<uuid:color_id>/",
        views.BrandColorDetailView.as_view(),
        name="brand-color-detail",
    ),
    path(
        "brands/<uuid:brand_id>/assets/",
        views.BrandAssetListCreateView.as_view(),
        name="brand-assets",
    ),
    path(
        "brands/<uuid:brand_id>/assets/<uuid:asset_id>/",
        views.BrandAssetDetailView.as_view(),
        name="brand-asset-detail",
    ),
    path(
        "brands/<uuid:brand_id>/assets/<uuid:asset_id>/analysis/",
        views.BrandAssetAnalysisView.as_view(),
        name="brand-asset-analysis",
    ),
    path(
        "brands/<uuid:brand_id>/ai-context/",
        views.BrandAIContextView.as_view(),
        name="brand-ai-context",
    ),
    path(
        "brands/<uuid:brand_id>/ai-context/apply/",
        views.ApplyBrandAIContextView.as_view(),
        name="brand-ai-context-apply",
    ),
]
