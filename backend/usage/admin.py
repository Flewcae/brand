from django.contrib import admin

from .models import UsageLog


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ("brand", "provider", "operation", "model", "estimated_cost_usd", "created_at")
    list_filter = ("provider", "operation")
