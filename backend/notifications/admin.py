from django.contrib import admin

from .models import Notification, PushSubscription, ReminderEscalationState


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "is_read", "delivery_status", "created_at")
    list_filter = ("notification_type", "delivery_status", "is_read")


@admin.register(ReminderEscalationState)
class ReminderEscalationStateAdmin(admin.ModelAdmin):
    list_display = ("calendar_entry", "sent_24h", "sent_12h", "sent_3h", "sent_due")
