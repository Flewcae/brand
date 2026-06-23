from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Agency, AgencyMembership, User


class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"fields": ("email", "password1", "password2")}),)
    search_fields = ("email",)


admin.site.register(User, UserAdmin)


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(AgencyMembership)
class AgencyMembershipAdmin(admin.ModelAdmin):
    list_display = ("agency", "user", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active")
