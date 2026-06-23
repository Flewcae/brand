from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("agencies.urls")),
    path("api/", include("brands.urls")),
    path("api/", include("content_calendar.urls")),
    path("api/", include("special_days.urls")),
    path("api/", include("generation.urls")),
    path("api/", include("usage.urls")),
    path("api/", include("notifications.urls")),
]
