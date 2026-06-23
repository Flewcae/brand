from django.contrib import admin

from .models import CalendarSuggestionBatch, ContentCalendarEntry


@admin.register(ContentCalendarEntry)
class ContentCalendarEntryAdmin(admin.ModelAdmin):
    list_display = ("brand", "scheduled_date", "content_format", "status", "source")
    list_filter = ("status", "source", "content_format")


@admin.register(CalendarSuggestionBatch)
class CalendarSuggestionBatchAdmin(admin.ModelAdmin):
    list_display = ("brand", "trigger", "status", "entry_count", "created_at")
    list_filter = ("trigger", "status")
