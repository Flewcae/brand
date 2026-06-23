from django.contrib import admin

from .models import GenerationVersion


@admin.register(GenerationVersion)
class GenerationVersionAdmin(admin.ModelAdmin):
    list_display = ("calendar_entry", "version_number", "media_type", "status", "created_at")
    list_filter = ("media_type", "status")
