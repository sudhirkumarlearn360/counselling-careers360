from django.contrib import admin

from apps.common.admin import NoDeleteAdminMixin
from apps.messaging.models import Message, OtpCode


@admin.register(Message)
class MessageAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["created_at", "template", "to", "status", "student"]
    list_filter = ["template", "status"]


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ["created_at", "mobile", "centre", "attempts", "expires_at", "verified_at"]
    exclude = ["code_hash"]
