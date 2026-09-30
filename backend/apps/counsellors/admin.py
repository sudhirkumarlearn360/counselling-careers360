from django.contrib import admin

from apps.counsellors.models import Counsellor, Posting


class PostingInline(admin.TabularInline):
    model = Posting
    extra = 0


@admin.register(Counsellor)
class CounsellorAdmin(admin.ModelAdmin):
    list_display = ["name", "mobile", "streams", "expected_session_min"]
    search_fields = ["name", "mobile"]
    inlines = [PostingInline]


@admin.register(Posting)
class PostingAdmin(admin.ModelAdmin):
    list_display = ["counsellor", "centre", "desk_label", "duty"]
    list_filter = ["duty", "centre"]
