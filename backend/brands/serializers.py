from rest_framework import serializers

from .models import BrandAIContext, BrandAsset, BrandColor, BrandProfile


class BrandColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandColor
        fields = ["id", "name", "hex_value", "role", "source", "order"]
        read_only_fields = ["id"]


class BrandProfileSerializer(serializers.ModelSerializer):
    colors = BrandColorSerializer(many=True, read_only=True)

    class Meta:
        model = BrandProfile
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "style_description",
            "voice_tone_description",
            "voice_traits",
            "target_audience",
            "font_primary",
            "font_secondary",
            "country_code",
            "timezone",
            "default_publish_time",
            "colors",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BrandAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAsset
        fields = [
            "id",
            "asset_type",
            "file",
            "original_filename",
            "content_type",
            "page_images",
            "claude_vision_analysis",
            "analysis_status",
            "is_primary",
            "uploaded_at",
        ]
        read_only_fields = [
            "id",
            "original_filename",
            "content_type",
            "page_images",
            "claude_vision_analysis",
            "analysis_status",
            "uploaded_at",
        ]


class BrandAIContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAIContext
        fields = [
            "style_keywords",
            "mood_descriptors",
            "visual_donts",
            "enrichment_summary",
            "last_enriched_at",
        ]


class ApplyAIContextSerializer(serializers.Serializer):
    target_field = serializers.ChoiceField(choices=["style_description", "voice_tone_description"])
    mode = serializers.ChoiceField(choices=["append", "replace"], default="append")
