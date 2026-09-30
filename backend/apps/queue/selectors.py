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
    centres = list(
        Centre.objects.select_related("settings").filter(status=CentreStatus.LIVE).order_by("date", "city")
    )
    ids = [c.id for c in centres]
    postings = list(
        Posting.objects.filter(centre_id__in=ids).select_related("counsellor").order_by("desk_label", "id")
    )
    now = timezone.now()
    sla = {c.id: dt.timedelta(minutes=c.settings.wait_sla_min) for c in centres}
    serving, waiting, late = {}, defaultdict(int), defaultdict(int)
    summary = defaultdict(lambda: defaultdict(int))
    for s in Student.objects.filter(centre_id__in=ids).values(
        "centre_id", "counsellor_id", "token", "name", "status", "source", "queue_at"
    ):
        key = (s["centre_id"], s["counsellor_id"])
        sm = summary[s["centre_id"]]
        sm["checked_in"] += 1
        sm["self_scan" if s["source"] == "self" else "at_desk"] += 1
        if s["status"] == StudentStatus.DONE:
            sm["counselled"] += 1
        elif s["status"] == StudentStatus.NO_SHOW:
            sm["no_shows"] += 1
        elif s["status"] == StudentStatus.WAITING:
            waiting[key] += 1
            sm["waiting"] += 1
            if now - s["queue_at"] > sla[s["centre_id"]]:
                late[key] += 1
                sm["late"] += 1
        elif s["status"] in ACTIVE_STATUSES:
            serving[key] = {"token": s["token"], "name": s["name"], "status": s["status"]}
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
                "queue_late": late.get(key, 0),
                "avg_session_min": avg,
                "avg_session_n": len(secs),
                "counselled_today": len(secs),
                # The "open desk" control (CQ-5): pass as_counsellor to the desk/ endpoints.
                "open_desk": {"as_counsellor": p.counsellor_id, "centre_id": p.centre_id},
            }
        )
    out = []
    for c in centres:
        sm = summary[c.id]
        planned = c.expected_students
        out.append(
            {
                **centre_payload(c),
                "summary": {
                    "checked_in": sm["checked_in"],
                    "self_scan": sm["self_scan"],
                    "at_desk": sm["at_desk"],
                    "waiting": sm["waiting"],
                    "late": sm["late"],
                    "counselled": sm["counselled"],
                    "no_shows": sm["no_shows"],
                    "planned": planned,
                    "capacity_pct": round(100 * sm["checked_in"] / planned) if planned else None,
                },
                "counsellors": cards[c.id],
            }
        )
    return out


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
