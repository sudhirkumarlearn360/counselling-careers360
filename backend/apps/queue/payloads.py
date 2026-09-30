"""Response shapes for the student, hall and desk screens (reads only).

Student-facing payloads (`token_payload`, `board_payload`, `public_centre_payload`) never include
another student's name or mobile. Polling endpoints use a fixed number of queries per panel.
"""

from __future__ import annotations

import datetime as dt
import re

from django.db.models import Q
from django.utils import timezone

from apps.accounts.selectors import centre_payload
from apps.centres.models import CentreStatus
from apps.common.choices import (
    Exam,  # noqa: F401  (kept for callers that import from here)
    Stream,
)
from apps.common.validators import normalise_mobile, valid_mobile
from apps.counsellors.models import Duty, Posting
from apps.messaging.models import Message
from apps.queue.models import (
    ACTIVE_STATUSES,
    OPEN_STATUSES,
    AuditEvent,
    SessionRecord,
    Student,
    StudentStatus,
)
from apps.queue.selectors import waiting_queue
from apps.queue.services import metrics
from apps.queue.services.checkin import _fmt_date
from apps.queue.services.eta import avg_session, eta_for

STREAM_NAMES = dict(Stream.choices)
NO_DATA = "—"
BOARD_STANDING_LINE = "Scan the code at the entrance to check in — keep your phone on for your turn alert."
NOTHING_CALLED = "Nothing called yet."


def natural_key(label: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", label or "")]


def minutes_since(when, now=None) -> int:
    return max(0, int(((now or timezone.now()) - when).total_seconds() // 60))


def _hhmm(when) -> str:
    return timezone.localtime(when).strftime("%H:%M")


def open_message(centre) -> tuple:
    """(is_open, message) for the QR landing (CQ-12)."""
    if centre.status == CentreStatus.LIVE:
        return True, ""
    if centre.status == CentreStatus.CLOSED:
        return False, f"Check-in closed at {centre.closes_at:%H:%M}. Please see the front desk."
    return False, f"This centre isn't open for check-in — it runs on {_fmt_date(centre.date)}."


def public_centre_payload(centre) -> dict:
    is_open, message = open_message(centre)
    avg = metrics.average_wait(centre)
    waiting = Student.objects.filter(centre_id=centre.pk, status=StudentStatus.WAITING).count()
    return {
        "centre": {**centre_payload(centre), "front_desk_phone": centre.front_desk_phone},
        "open": is_open,
        "message": message,
        "stats": {
            "waiting": waiting,
            "counsellors_on_site": metrics.counsellors_on_site(centre),
            # A dash, never zero, before anyone has been called (CQ-13).
            "avg_wait_min": round(avg.seconds / 60) if avg.n else None,
            "avg_wait_label": f"{round(avg.seconds / 60)} min" if avg.n else NO_DATA,
        },
        "steps": [
            "Fill in your details",
            "Receive your token on WhatsApp",
            "Sit anywhere until you're called",
        ],
        "bring": ["Marksheets", "Entrance scorecard", "Photo ID", "A parent or guardian"],
        "bring_note": "All optional — come as you are.",
    }


def _desk_of(student) -> str:
    return (
        Posting.objects.filter(centre_id=student.centre_id, counsellor_id=student.counsellor_id)
        .values_list("desk_label", flat=True)
        .first()
        or ""
    )


def token_payload(student, now=None) -> dict:
    """The student's live token page (CQ-19, 21-28)."""
    now = now or timezone.now()
    s, centre, c = student, student.centre, student.counsellor
    state = {"kind": s.status}
    if s.status == StudentStatus.WAITING:
        eta = eta_for(s, now)
        if eta is not None and eta.is_next:
            state = {"kind": "next"}
        elif eta is not None:
            state = {
                "kind": "waiting",
                "ahead": eta.ahead,
                "minutes": eta.minutes,
                "expected_at": _hhmm(eta.at),
                "approximate": True,
            }
    elif s.status in (StudentStatus.CALLED, StudentStatus.IN_SESSION):
        state = {"kind": s.status, "recall_hold": "Your place is held for two calls."}
    return {
        "token": s.token,
        "status": s.status,
        "state": state,
        "stream": s.stream,
        "stream_name": STREAM_NAMES.get(s.stream, s.stream),
        "name": s.name,
        "mobile": s.mobile,
        "counsellor": c.name,
        "desk": _desk_of(s),
        "venue": centre.venue,
        "city": centre.city,
        "date": centre.date.isoformat(),
        "closes_at": centre.closes_at.strftime("%H:%M"),
        "front_desk_phone": centre.front_desk_phone,
        "checked_in_at": _hhmm(s.checkin_at),
        "consent": s.consent,
        "source": s.source,
        "rating": s.rating,
        "can_release": s.status in (StudentStatus.WAITING, StudentStatus.CALLED),
        "can_rate": s.status == StudentStatus.DONE and s.rating is None,
        "centre_status": centre.status,
        "centre_slug": centre.slug,
    }


def board_payload(centre, now=None) -> dict:
    """The hall display (CQ-51-53): one panel per counsellor, recently called, standing line."""
    now = now or timezone.now()
    postings = list(Posting.objects.filter(centre_id=centre.pk).select_related("counsellor"))
    postings.sort(key=lambda p: (natural_key(p.desk_label), p.id))
    rows = Student.objects.filter(centre_id=centre.pk, status__in=OPEN_STATUSES).order_by(
        "-priority", "queue_at", "id"
    )
    serving, waiting = {}, {}
    for s in rows:
        if s.status in ACTIVE_STATUSES:
            serving[s.counsellor_id] = s.token
        else:
            waiting.setdefault(s.counsellor_id, []).append(s.token)
    recent = list(
        Student.objects.filter(centre_id=centre.pk, called_at__isnull=False)
        .order_by("-called_at", "-id")
        .values_list("token", flat=True)[:6]
    )
    panels = []
    for p in postings:
        queue = waiting.get(p.counsellor_id, [])
        if p.duty == Duty.OFF_DUTY:
            line = "Closed"
        elif p.duty == Duty.ON_BREAK:
            line = "back shortly"
        elif not queue and p.counsellor_id not in serving:
            line = "queue clear"
        else:
            line = ""
        panels.append(
            {
                "desk": p.desk_label,
                "counsellor": p.counsellor.name,
                "duty": p.duty,
                "serving": serving.get(p.counsellor_id),  # None renders as a dimmed dash
                "next": queue[0] if queue and p.duty == Duty.ON_DESK else None,
                "waiting": len(queue),
                "line": line,
            }
        )
    total_waiting = sum(len(v) for v in waiting.values())
    return {
        "centre": {**centre_payload(centre)},
        "now": timezone.localtime(now).strftime("%H:%M"),
        "total_waiting": total_waiting,
        "panels": panels,
        "recently_called": recent,
        "recently_called_empty": NOTHING_CALLED if not recent else "",
        "standing_line": BOARD_STANDING_LINE,
    }


# --- Hall queue (reception, CQ-31-34, CQ-58) ----------------------------------------------------


def _failed_turn_alert_ids(student_ids) -> set:
    """Students whose latest turn_called message failed (CQ-58)."""
    latest = {}
    for sid, status in (
        Message.objects.filter(student_id__in=student_ids, template=Message.Template.TURN_CALLED)
        .order_by("id")
        .values_list("student_id", "status")
    ):
        latest[sid] = status
    return {sid for sid, st in latest.items() if st == Message.Status.FAILED}


def _row(s, desks, failed, now) -> dict:
    return {
        "id": s.id,
        "token": s.token,
        "name": s.name,
        "mobile": s.mobile,
        "stream": s.stream,
        "status": s.status,
        "source": s.source,
        "counsellor": {
            "id": s.counsellor_id,
            "name": s.counsellor.name,
            "desk": desks.get(s.counsellor_id, ""),
        },
        "checked_in_at": _hhmm(s.checkin_at),
        "waited_min": minutes_since(s.queue_at, now) if s.status == StudentStatus.WAITING else None,
        "late": s.status == StudentStatus.WAITING
        and (now - s.queue_at) > dt.timedelta(minutes=s.centre.settings.wait_sla_min),
        "consent_pending": s.consent == "pending",
        "recalls": s.recalls,
        "alert_failed": s.id in failed,
        "alert_failed_message": "WhatsApp didn't reach them — turn alert. Call out their token."
        if s.id in failed
        else "",
    }


def search_filter(qs, q: str):
    q = (q or "").strip()
    if not q:
        return qs
    cond = Q(name__icontains=q) | Q(mobile__icontains=q) | Q(token__icontains=q)
    number = normalise_mobile(q)
    if valid_mobile(number) and number != q:  # "+91 98110 22001" finds 9811022001
        cond |= Q(mobile=number)
    return qs.filter(cond)


def hall_payload(centre, q: str = "", counsellor_id=None, now=None) -> dict:
    """Open students (or every status when searching) plus the counsellor tabs with live/late counts."""
    now = now or timezone.now()
    postings = list(Posting.objects.filter(centre_id=centre.pk).select_related("counsellor"))
    postings.sort(key=lambda p: (natural_key(p.desk_label), p.id))
    desks = {p.counsellor_id: p.desk_label for p in postings}
    base = Student.objects.filter(centre_id=centre.pk).select_related("counsellor", "centre__settings")
    open_rows = list(base.filter(status__in=OPEN_STATUSES).order_by("checkin_at", "id"))
    sla = dt.timedelta(minutes=centre.settings.wait_sla_min)
    counts, lates = {}, {}
    for s in open_rows:
        counts[s.counsellor_id] = counts.get(s.counsellor_id, 0) + 1
        if s.status == StudentStatus.WAITING and now - s.queue_at > sla:
            lates[s.counsellor_id] = lates.get(s.counsellor_id, 0) + 1
    tabs = [
        {
            "key": "all",
            "label": "All students",
            "counsellor_id": None,
            "count": len(open_rows),
            "late": sum(lates.values()),
        }
    ]
    for p in postings:  # off-duty desks with students still get a tab; empty desks show 0
        tabs.append(
            {
                "key": f"c{p.counsellor_id}",
                "label": f"{p.counsellor.name} · {p.desk_label}",
                "counsellor_id": p.counsellor_id,
                "duty": p.duty,
                "count": counts.get(p.counsellor_id, 0),
                "late": lates.get(p.counsellor_id, 0),
            }
        )
    q = (q or "").strip()
    if q:  # search covers every status and takes precedence over the tab
        rows = list(search_filter(base, q).order_by("checkin_at", "id"))
    else:
        rows = [s for s in open_rows if counsellor_id in (None, s.counsellor_id)]
    failed = _failed_turn_alert_ids([s.id for s in rows])
    return {
        "centre": {**centre_payload(centre), "front_desk_phone": centre.front_desk_phone},
        "header": {
            "waiting": sum(1 for s in open_rows if s.status == StudentStatus.WAITING),
            "late": sum(lates.values()),
            "wait_promise_min": centre.settings.wait_sla_min,
        },
        "tabs": tabs,
        "rows": [_row(s, desks, failed, now) for s in rows],
        "query": q,
        "count": len(rows),
    }


# --- Student record (hall / desk) ---------------------------------------------------------------


def student_detail(s, now=None) -> dict:
    now = now or timezone.now()
    desk = _desk_of(s)
    return {
        "id": s.id,
        "token": s.token,
        "status": s.status,
        "source": s.source,
        "name": s.name,
        "school": s.school,
        "mobile": s.mobile,
        "parent_mobile": s.parent_mobile,
        "email": s.email,
        "stream": s.stream,
        "stream_name": STREAM_NAMES.get(s.stream, s.stream),
        "klass": s.klass,
        "course": s.course,
        "exams": s.exams,
        "clarity": s.clarity,
        "help": s.help,
        "consent": s.consent,
        "consent_at": s.consent_at.isoformat() if s.consent_at else None,
        "consent_by": s.consent_by.name if s.consent_by_id else None,
        "counsellor": {"id": s.counsellor_id, "name": s.counsellor.name, "desk": desk},
        "checked_in_at": _hhmm(s.checkin_at),
        "called_at": s.called_at.isoformat() if s.called_at else None,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "recalls": s.recalls,
        "rating": s.rating,
        "outcome": s.outcome,
        "follow_up_on": s.follow_up_on.isoformat() if s.follow_up_on else None,
        "colleges_discussed": s.colleges_discussed,
        "home_city": s.home_city,
        "target_exam": s.target_exam,
        "budget": s.budget,
        "accompanied_by": s.accompanied_by,
        "notes": [
            {"id": n.id, "text": n.text, "author": n.author_name, "at": n.created_at.isoformat()}
            for n in s.notes.all()
        ],
        "timer": _timer(s, now),
    }


def _timer(s, now):
    t = metrics.session_timer(s, now)
    return (
        None
        if t is None
        else {
            "elapsed_seconds": t.elapsed_seconds,
            "target_min": t.target_min,
            "over_target": t.over_target,
            "waiting": t.waiting,
        }
    )


def hall_student_detail(s) -> dict:
    audit = [
        {
            "verb": e.verb,
            "at": e.at.isoformat(),
            "actor": e.actor.name if e.actor_id else "Student",
            "data": e.data,
        }
        for e in AuditEvent.objects.filter(student=s).select_related("actor").order_by("at", "id")
    ]
    messages = [
        {
            "id": m.id,
            "template": m.template,
            "status": m.status,
            "at": m.created_at.isoformat(),
            "failure_reason": m.failure_reason,
        }
        for m in s.messages.all()
    ]
    return {**student_detail(s), "audit": audit, "messages": messages}


# --- Counsellor desk (CQ-37, 38, 50) ------------------------------------------------------------


def desk_payload(counsellor, centre, now=None) -> dict:
    now = now or timezone.now()
    posting = Posting.objects.filter(centre_id=centre.pk, counsellor_id=counsellor.pk).first()
    queue = list(waiting_queue(counsellor, centre).select_related("centre__settings"))
    current = (
        Student.objects.filter(centre_id=centre.pk, counsellor_id=counsellor.pk, status__in=ACTIVE_STATUSES)
        .select_related("counsellor", "consent_by", "centre__settings")
        .prefetch_related("notes")
        .first()
    )
    sla = dt.timedelta(minutes=centre.settings.wait_sla_min)
    avg = metrics.average_session_length(centre, counsellor)
    hall_waiting = Student.objects.filter(centre_id=centre.pk, status=StudentStatus.WAITING).count()
    return {
        "centre": {**centre_payload(centre), "front_desk_phone": centre.front_desk_phone},
        "desk": posting.desk_label if posting else "",
        "duty": posting.duty if posting else Duty.OFF_DUTY,
        "counsellor": {"id": counsellor.id, "name": counsellor.name},
        "figures": {
            "in_queue": len(queue),
            "waiting_hall": hall_waiting,
            "counselled_today": metrics.counselled_today(counsellor, centre),
            "ready_today": SessionRecord.objects.filter(
                centre_id=centre.pk, counsellor_id=counsellor.pk, outcome="ready"
            ).count(),
            "avg_session_min": round(avg.seconds / 60) if avg.n else None,
            "target_session_min": centre.settings.target_session_min,
            "late": sum(1 for s in queue if now - s.queue_at > sla),
            "wait_promise_min": centre.settings.wait_sla_min,
        },
        "next_token": queue[0].token if queue and current is None else None,
        "current": student_detail(current, now) if current else None,
        "queue": [
            {
                "id": s.id,
                "token": s.token,
                "name": s.name,
                "stream": s.stream,
                "klass": s.klass,
                "waited_min": minutes_since(s.queue_at, now),
                "source": s.source,
                "consent_pending": s.consent == "pending",
                "late": now - s.queue_at > sla,
                "next": i == 0,
            }
            for i, s in enumerate(queue)
        ],
    }


def my_students(counsellor, centre_id=None) -> list:
    qs = Student.objects.filter(counsellor_id=counsellor.pk).select_related("centre")
    if centre_id:
        qs = qs.filter(centre_id=centre_id)
    out = []
    for s in qs.order_by("-checkin_at", "-id"):
        wait = metrics.wait_seconds(s)
        session = (s.ended_at - s.started_at).total_seconds() if s.ended_at and s.started_at else None
        out.append(
            {
                "id": s.id,
                "token": s.token,
                "name": s.name,
                "mobile": s.mobile,
                "school": s.school,
                "course": s.course,
                "stream": s.stream,
                "status": s.status,
                "outcome": s.outcome,
                "centre": s.centre.city,
                "wait_min": round(wait / 60) if wait is not None else None,
                "session_min": round(session / 60) if session is not None else None,
            }
        )
    return out


def my_centres(counsellor) -> list:
    today = timezone.localdate()
    out = []
    for p in (
        Posting.objects.filter(counsellor_id=counsellor.pk).select_related("centre").order_by("centre__date")
    ):
        c = p.centre
        out.append(
            {
                "centre": {**centre_payload(c)},
                "desk": p.desk_label,
                "live": c.status == CentreStatus.LIVE and c.date == today,
                "upcoming": c.date > today,
                "students": Student.objects.filter(centre_id=c.pk).count(),
                "my_students": Student.objects.filter(centre_id=c.pk, counsellor_id=counsellor.pk).count(),
                "counsellors_on_site": metrics.counsellors_on_site(c),
            }
        )
    return out


def avg_session_minutes(counsellor, centre) -> int:
    return round(avg_session(counsellor, centre).total_seconds() / 60)
