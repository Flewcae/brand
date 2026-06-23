from rest_framework import serializers

from .models import GenerationVersion


class GenerationVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenerationVersion
        fields = [
            "id",
            "version_number",
            "media_type",
            "status",
            "claude_prompt_text",
            "grok_request_payload",
            "grok_response_meta",
            "media_file",
            "thumbnail_file",
            "error_message",
            "requested_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
