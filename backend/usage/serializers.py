from rest_framework import serializers

from .models import UsageLog


class UsageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageLog
        fields = [
            "id",
            "provider",
            "model",
            "operation",
            "cost_in_usd_ticks",
            "input_tokens",
            "output_tokens",
            "estimated_cost_usd",
            "generation_version",
            "suggestion_batch",
            "brand_asset",
            "created_at",
        ]
        read_only_fields = fields
