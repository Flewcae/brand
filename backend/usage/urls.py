from django.urls import path

from . import views

urlpatterns = [
    path("brands/<uuid:brand_id>/usage/", views.UsageLogListView.as_view(), name="usage-list"),
    path(
        "brands/<uuid:brand_id>/usage/summary/",
        views.UsageSummaryView.as_view(),
        name="usage-summary",
    ),
]
