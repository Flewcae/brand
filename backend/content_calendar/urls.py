from django.urls import path

from . import views

urlpatterns = [
    path(
        "brands/<uuid:brand_id>/calendar/suggestions/generate-now/",
        views.GenerateSuggestionsNowView.as_view(),
        name="calendar-generate-now",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/suggestion-batches/<uuid:batch_id>/",
        views.SuggestionBatchDetailView.as_view(),
        name="calendar-suggestion-batch-detail",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/evaluate/",
        views.EvaluateEntryView.as_view(),
        name="calendar-evaluate",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/approve/",
        views.ApproveEntryView.as_view(),
        name="calendar-approve",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/reject/",
        views.RejectEntryView.as_view(),
        name="calendar-reject",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:entry_id>/more-like-this/",
        views.MoreLikeThisView.as_view(),
        name="calendar-more-like-this",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/",
        views.CalendarEntryListCreateView.as_view(),
        name="calendar-list",
    ),
    path(
        "brands/<uuid:brand_id>/calendar/<uuid:pk>/",
        views.CalendarEntryDetailView.as_view(),
        name="calendar-detail",
    ),
]
