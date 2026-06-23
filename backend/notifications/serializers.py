from rest_framework import serializers

from .models import Notification, PushSubscription


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["id", "registration_token", "user_agent", "is_active", "created_at"]
        read_only_fields = ["id", "is_active", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "brand",
            "notification_type",
            "title",
            "body",
            "related_calendar_entry",
            "related_generation_version",
            "is_read",
            "channel",
            "delivery_status",
            "created_at",
            "sent_at",
        ]
        read_only_fields = [
            "id",
            "brand",
            "notification_type",
            "title",
            "body",
            "related_calendar_entry",
            "related_generation_version",
            "channel",
            "delivery_status",
            "created_at",
            "sent_at",
        ]
