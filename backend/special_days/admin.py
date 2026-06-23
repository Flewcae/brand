from django.contrib import admin

from .models import BrandHoliday, CountryHolidayTemplate, CountryHolidayTemplateEntry


@admin.register(CountryHolidayTemplate)
class CountryHolidayTemplateAdmin(admin.ModelAdmin):
    list_display = ("country_code", "popular_days_last_refreshed_at")


@admin.register(CountryHolidayTemplateEntry)
class CountryHolidayTemplateEntryAdmin(admin.ModelAdmin):
    list_display = ("template", "name", "date", "category", "source")
    list_filter = ("category", "source")


@admin.register(BrandHoliday)
class BrandHolidayAdmin(admin.ModelAdmin):
    list_display = ("brand", "name", "date", "category", "is_active")
    list_filter = ("category", "is_active")
