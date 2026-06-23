from rest_framework import serializers

from .models import CalendarSuggestionBatch, ContentCalendarEntry


class ContentCalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentCalendarEntry
        fields = [
            "id",
            "scheduled_date",
            "scheduled_time",
            "content_format",
            "aspect_ratio",
            "status",
            "source",
            "brief",
            "brand_holiday",
            "suggestion_batch",
            "parent_entry",
            "active_generation_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "source",
            "suggestion_batch",
            "parent_entry",
            "active_generation_version",
            "created_at",
            "updated_at",
        ]


class CalendarSuggestionBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarSuggestionBatch
        fields = ["id", "trigger", "status", "entry_count", "created_at", "completed_at"]
        read_only_fields = fields


class MoreLikeThisSerializer(serializers.Serializer):
    count = serializers.IntegerField(default=3, min_value=1, max_value=10)
