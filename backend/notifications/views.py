from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushSubscription
from .serializers import NotificationSerializer, PushSubscriptionSerializer


class PushSubscriptionCreateView(generics.CreateAPIView):
    serializer_class = PushSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Re-subscribing with the same endpoint (e.g. browser storage cleared)
        # reactivates the existing row instead of violating the unique
        # constraint on endpoint.
        endpoint = serializer.validated_data["endpoint"]
        existing = PushSubscription.objects.filter(endpoint=endpoint).first()
        if existing:
            existing.p256dh_key = serializer.validated_data["p256dh_key"]
            existing.auth_key = serializer.validated_data["auth_key"]
            existing.user_agent = serializer.validated_data.get("user_agent", existing.user_agent)
            existing.user = self.request.user
            existing.is_active = True
            existing.save()
            serializer.instance = existing
        else:
            serializer.save(user=self.request.user)


class PushSubscriptionDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PushSubscription.objects.filter(user=self.request.user)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user).order_by("-created_at")
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == "true")
        return qs


class NotificationUpdateView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VapidPublicKeyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"vapid_public_key": settings.VAPID_PUBLIC_KEY})
