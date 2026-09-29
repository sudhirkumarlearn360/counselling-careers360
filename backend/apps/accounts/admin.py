from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import LoginAttempt, StaffUser


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "name", "role", "centre", "counsellor", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["email", "name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "title", "role", "centre", "counsellor")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "centre", "counsellor", "password1", "password2"),
            },
        ),
    )


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ["email", "failed_count", "last_failed_at"]
