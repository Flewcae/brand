from django.contrib import admin

from .models import BrandAIContext, BrandAsset, BrandColor, BrandProfile


class BrandColorInline(admin.TabularInline):
    model = BrandColor
    extra = 0


@admin.register(BrandProfile)
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "agency", "country_code", "is_active", "created_at")
    list_filter = ("is_active", "country_code")
    search_fields = ("name", "agency__name")
    inlines = [BrandColorInline]


@admin.register(BrandAsset)
class BrandAssetAdmin(admin.ModelAdmin):
    list_display = ("brand", "asset_type", "analysis_status", "is_primary", "uploaded_at")
    list_filter = ("asset_type", "analysis_status")


@admin.register(BrandAIContext)
class BrandAIContextAdmin(admin.ModelAdmin):
    list_display = ("brand", "last_enriched_at")
