"""CSV export of the (filtered) student records (CQ-60). Ops lead only; every export is audited."""

from __future__ import annotations

import csv
import io

from django.utils import timezone

from apps.queue.models import AuditEvent

COLUMNS = [
    "Token",
    "Name",
    "School",
    "Mobile",
    "Parent contact",
    "Email",
    "Stream",
    "Class",
    "Targeted course",
    "Entrance exams",
    "Clarity",
    "Help wanted",
    "City",
    "Date",
    "Counsellor",
    "Check-in time",
    "Call time",
    "Wait (min)",
    "Session length (min)",
    "Status",
    "Outcome",
    "Follow-up date",
    "Notes",
]
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def safe(value) -> str:
    """Neutralise spreadsheet formula injection: a cell starting with = + - @ gets a leading quote."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def _mins(delta):
    return "" if delta is None else round(delta.total_seconds() / 60)


def _time(when):
    return timezone.localtime(when).strftime("%H:%M") if when else ""


def filename(centre, today) -> str:
    if centre is not None:
        return f"counselqueue_{centre.city.lower().replace(' ', '-')}_{centre.date.isoformat()}.csv"
    return f"counselqueue_all_{today.isoformat()}.csv"


def build_csv(students) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    for s in students.prefetch_related("notes"):
        wait = (s.called_at - s.queue_at) if s.called_at else None
        session = (s.ended_at - s.started_at) if s.ended_at and s.started_at else None
        notes = " | ".join(
            f"{timezone.localtime(n.created_at):%H:%M} {n.author_name}: {n.text}" for n in s.notes.all()
        )
        row = [
            s.token,
            s.name,
            s.school,
            s.mobile,
            s.parent_mobile,
            s.email,
            s.stream,
            s.klass,
            s.course,
            "; ".join(s.exams or []),
            s.clarity,
            "; ".join(s.help or []),
            s.centre.city,
            s.centre.date.isoformat(),
            s.counsellor.name,
            _time(s.checkin_at),
            _time(s.called_at),
            _mins(wait),
            _mins(session),
            s.status,
            s.outcome or "",
            s.follow_up_on.isoformat() if s.follow_up_on else "",
            notes,
        ]
        writer.writerow([safe(v) for v in row])
    return out.getvalue()


def audit_export(students, actor, params, count) -> None:
    centre_ids = set(students.values_list("centre_id", flat=True))
    AuditEvent.objects.bulk_create(
        [
            AuditEvent(
                centre_id=cid,
                verb=AuditEvent.Verb.EXPORTED,
                actor=actor,
                data={"filters": dict(params), "count": count},
            )
            for cid in sorted(centre_ids)
        ]
    )
