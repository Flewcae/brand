from django.urls import path

from . import views

urlpatterns = [
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/generations/",
        views.GenerationListCreateView.as_view(),
        name="generation-list",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/generations/<uuid:version_id>/",
        views.GenerationDetailView.as_view(),
        name="generation-detail",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/generations/<uuid:version_id>/select/",
        views.SelectGenerationVersionView.as_view(),
        name="generation-select",
    ),
]
