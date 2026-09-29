from __future__ import annotations

from django.db.models import Prefetch

from apps.counsellors.models import Counsellor, Posting


def counsellors_qs():
    return Counsellor.objects.prefetch_related(
        Prefetch("postings", queryset=Posting.objects.select_related("centre").order_by("centre__date", "id"))
    )


def posting_payload(p: Posting) -> dict:
    return {
        "id": p.id,
        "counsellor_id": p.counsellor_id,
        "centre_id": p.centre_id,
        "city": p.centre.city,
        "venue": p.centre.venue,
        "date": p.centre.date.isoformat(),
        "centre_status": p.centre.status,
        "desk_label": p.desk_label,
        "duty": p.duty,
    }


def counsellor_payload(c: Counsellor) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "mobile": c.mobile,
        "streams": c.streams,
        "expected_session_min": c.expected_session_min,
        "postings": [posting_payload(p) for p in c.postings.all()],  # prefetched
    }


def counsellor_list() -> list:
    return [counsellor_payload(c) for c in counsellors_qs()]


def counsellor_by_id(pk: int):
    return counsellors_qs().filter(pk=pk).first()


def posting_by_id(pk: int):
    return Posting.objects.select_related("centre", "counsellor").filter(pk=pk).first()
