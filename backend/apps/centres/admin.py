from django.contrib import admin

from apps.centres.models import Centre, CentreSettings


class CentreSettingsInline(admin.StackedInline):
    model = CentreSettings
    can_delete = False


@admin.register(Centre)
class CentreAdmin(admin.ModelAdmin):
    list_display = ["city", "venue", "date", "opens_at", "closes_at", "status", "slug"]
    list_filter = ["status", "city"]
    search_fields = ["city", "venue", "slug"]
    inlines = [CentreSettingsInline]
