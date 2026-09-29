"""Read queries for the queue app. Metric definitions follow counselqueue-queue-engine."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from django.utils import timezone

from apps.accounts.selectors import centre_payload
from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Posting
from apps.queue.models import ACTIVE_STATUSES, SessionRecord, Student, StudentStatus


def _local_day_bounds():
    start = timezone.make_aware(dt.datetime.combine(timezone.localdate(), dt.time.min))
    return start, start + dt.timedelta(days=1)


def live_overview() -> list:
    """Live centres with one card per posted counsellor (CQ-5). Four queries, however many desks."""
    centres = list(Centre.objects.filter(status=CentreStatus.LIVE).order_by("date", "city"))
    ids = [c.id for c in centres]
    postings = list(
        Posting.objects.filter(centre_id__in=ids).select_related("counsellor").order_by("desk_label", "id")
    )
    serving, waiting = {}, defaultdict(int)
    for s in Student.objects.filter(
        centre_id__in=ids, status__in=[StudentStatus.WAITING, *ACTIVE_STATUSES]
    ).values("centre_id", "counsellor_id", "token", "status"):
        key = (s["centre_id"], s["counsellor_id"])
        if s["status"] == StudentStatus.WAITING:
            waiting[key] += 1
        else:
            serving[key] = {"token": s["token"], "status": s["status"]}
    start, end = _local_day_bounds()
    durations = defaultdict(list)
    for r in SessionRecord.objects.filter(centre_id__in=ids, ended_at__gte=start, ended_at__lt=end).values(
        "centre_id", "counsellor_id", "started_at", "ended_at"
    ):
        durations[(r["centre_id"], r["counsellor_id"])].append(
            (r["ended_at"] - r["started_at"]).total_seconds()
        )

    cards = defaultdict(list)
    for p in postings:
        key = (p.centre_id, p.counsellor_id)
        secs = durations.get(key, [])
        avg = round(sum(secs) / len(secs) / 60, 1) if secs else p.counsellor.expected_session_min
        cards[p.centre_id].append(
            {
                "posting_id": p.id,
                "counsellor_id": p.counsellor_id,
                "name": p.counsellor.name,
                "streams": p.counsellor.streams,
                "desk_label": p.desk_label,
                "duty": p.duty,
                "serving": serving.get(key),
                "queue_length": waiting.get(key, 0),
                "avg_session_min": avg,
                "avg_session_n": len(secs),
                "counselled_today": len(secs),
                # The "open desk" control (CQ-5): pass as_counsellor to the desk/ endpoints.
                "open_desk": {"as_counsellor": p.counsellor_id, "centre_id": p.centre_id},
            }
        )
    return [{**centre_payload(c), "counsellors": cards[c.id]} for c in centres]


# --- Queue reads used by the engine (queue-engine: Queue order) --------------------------------------

QUEUE_ORDER = ("-priority", "queue_at", "id")


def waiting_queue(counsellor, centre):
    """A counsellor's queue at a centre: waiting students ordered by (-priority, queue_at, id)."""
    return Student.objects.filter(
        centre_id=getattr(centre, "pk", centre),
        counsellor_id=getattr(counsellor, "pk", counsellor),
        status=StudentStatus.WAITING,
    ).order_by(*QUEUE_ORDER)


def active_student(counsellor, centre):
    """The counsellor's called or in-session student at the centre, if any."""
    return (
        Student.objects.filter(
            centre_id=getattr(centre, "pk", centre),
            counsellor_id=getattr(counsellor, "pk", counsellor),
            status__in=ACTIVE_STATUSES,
        )
        .order_by("id")
        .first()
    )
