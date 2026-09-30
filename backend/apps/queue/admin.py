from django.contrib import admin

from apps.common.admin import NoDeleteAdminMixin
from apps.queue.models import AuditEvent, Note, SessionRecord, Student, TokenSequence


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0
    can_delete = False


class SessionRecordInline(admin.TabularInline):
    model = SessionRecord
    extra = 0
    can_delete = False
    readonly_fields = ["counsellor", "centre", "queue_at", "called_at", "started_at", "ended_at", "outcome"]


@admin.register(Student)
class StudentAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    """Read-mostly: queue state belongs to apps.queue.services."""

    list_display = ["token", "name", "centre", "counsellor", "status", "consent", "checkin_at"]
    list_filter = ["status", "centre", "stream", "source"]
    search_fields = ["token", "name", "mobile"]
    readonly_fields = [
        "token",
        "centre",
        "counsellor",
        "source",
        "status",
        "checkin_at",
        "queue_at",
        "priority",
        "called_at",
        "started_at",
        "ended_at",
        "recalls",
        "consent",
        "consent_at",
        "consent_by",
        "rating",
        "access_key",
    ]
    inlines = [SessionRecordInline, NoteInline]


@admin.register(TokenSequence)
class TokenSequenceAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["centre", "last_number"]
    readonly_fields = ["centre", "last_number"]


@admin.register(AuditEvent)
class AuditEventAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["at", "verb", "centre", "student", "actor", "on_behalf_of"]
    list_filter = ["verb", "centre"]


@admin.register(SessionRecord)
class SessionRecordAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["student", "counsellor", "centre", "started_at", "ended_at", "outcome"]


@admin.register(Note)
class NoteAdmin(NoDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["created_at", "student", "author_name"]
