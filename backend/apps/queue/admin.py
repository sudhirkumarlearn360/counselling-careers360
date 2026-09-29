from django.contrib import admin

from apps.queue.models import AuditEvent, Note, SessionRecord, Student, TokenSequence


class NoteInline(admin.TabularInline):
    model = Note
    extra = 0


class SessionRecordInline(admin.TabularInline):
    model = SessionRecord
    extra = 0


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Read-mostly: status changes belong to apps.queue.services."""

    list_display = ["token", "name", "centre", "counsellor", "status", "consent", "checkin_at"]
    list_filter = ["status", "centre", "stream", "source"]
    search_fields = ["token", "name", "mobile"]
    readonly_fields = ["status", "counsellor", "queue_at", "priority", "access_key"]
    inlines = [SessionRecordInline, NoteInline]


@admin.register(TokenSequence)
class TokenSequenceAdmin(admin.ModelAdmin):
    list_display = ["centre", "last_number"]
    readonly_fields = ["last_number"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["at", "verb", "centre", "student", "actor", "on_behalf_of"]
    list_filter = ["verb", "centre"]


@admin.register(SessionRecord)
class SessionRecordAdmin(admin.ModelAdmin):
    list_display = ["student", "counsellor", "centre", "started_at", "ended_at", "outcome"]
