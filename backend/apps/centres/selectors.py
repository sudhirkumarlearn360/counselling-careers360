"""Centre reads. One query for the centres and one for their postings, however many there are."""

from __future__ import annotations

from django.db.models import Count, Prefetch

from apps.accounts.selectors import centre_payload
from apps.centres.models import Centre
from apps.common.choices import Stream
from apps.counsellors.models import Posting


def centres_qs():
    return Centre.objects.annotate(student_total=Count("students")).prefetch_related(
        Prefetch("postings", queryset=Posting.objects.select_related("counsellor")), "staff"
    )


def coverage(centre: Centre) -> tuple:
    covered = set()
    for p in centre.postings.all():  # prefetched
        covered.update(p.counsellor.streams or [])
    return (
        [s for s in Stream.values if s in covered],
        [s for s in Stream.values if s not in covered],
    )


def centre_full_payload(centre: Centre) -> dict:
    covered, uncovered = coverage(centre)
    return {
        **centre_payload(centre),
        "expected_students": centre.expected_students,
        "front_desk_phone": centre.front_desk_phone,
        "covered_streams": covered,
        "uncovered_streams": uncovered,
        "counsellor_count": len(centre.postings.all()),
        "counsellor_names": [p.counsellor.name for p in centre.postings.all()],
        "student_count": getattr(centre, "student_total", 0),
        "front_desk_email": next((u.email for u in centre.staff.all()), ""),  # never the password
    }


def centre_list(status=None) -> tuple:
    qs = centres_qs()
    total = qs.count()
    if status:
        qs = qs.filter(status=status)
    items = [centre_full_payload(c) for c in qs]
    return items, total


def centre_by_id(pk: int):
    return centres_qs().filter(pk=pk).first()
