from rest_framework import serializers

from .models import BrandHoliday, CountryHolidayTemplate


class CountryHolidayTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryHolidayTemplate
        fields = ["country_code", "popular_days_last_refreshed_at"]


class BrandHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandHoliday
        fields = ["id", "name", "date", "category", "is_active", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ImportHolidaysSerializer(serializers.Serializer):
    country_code = serializers.CharField(max_length=2)
    years = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
