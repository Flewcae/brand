from django.urls import path

from . import views

urlpatterns = [
    path("holidays/countries/", views.CountryTemplateListView.as_view(), name="holiday-countries"),
    path(
        "brands/<uuid:brand_id>/holidays/import/",
        views.BrandHolidayImportView.as_view(),
        name="brand-holidays-import",
    ),
    path("brands/<uuid:brand_id>/holidays/", views.BrandHolidayListView.as_view(), name="brand-holidays"),
    path(
        "brands/<uuid:brand_id>/holidays/<uuid:holiday_id>/",
        views.BrandHolidayDetailView.as_view(),
        name="brand-holiday-detail",
    ),
]
