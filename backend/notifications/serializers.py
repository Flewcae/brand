from rest_framework import serializers

from .models import Notification, PushSubscription


class PushSubscriptionSerializer(serializers.ModelSerializer):
    # Declared explicitly (not left to ModelSerializer's auto-generated
    # UniqueValidator) -- re-registering an existing token must reach
    # perform_create's reactivation logic instead of failing validation.
    registration_token = serializers.CharField(max_length=255)

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
