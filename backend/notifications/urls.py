from django.urls import path

from . import views

urlpatterns = [
    path(
        "push-subscriptions/",
        views.PushSubscriptionCreateView.as_view(),
        name="push-subscription-create",
    ),
    path(
        "push-subscriptions/<uuid:pk>/",
        views.PushSubscriptionDeleteView.as_view(),
        name="push-subscription-delete",
    ),
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:pk>/", views.NotificationUpdateView.as_view(), name="notification-update"),
    path(
        "notifications/mark-all-read/",
        views.MarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
]
