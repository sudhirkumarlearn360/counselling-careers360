"""The single Metrics definitions (queue-engine "Metrics"). Every screen and export uses these.

Read-only. "Today" is `timezone.localdate()` (IST).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.utils import timezone

from apps.counsellors.models import Duty, Posting
from apps.queue.models import SessionRecord, Student, StudentStatus

NO_DATA = "—"


@dataclass(frozen=True)
class Average:
    seconds: float | None  # None when n == 0
    n: int


@dataclass(frozen=True)
class Rate:
    value: float | None  # None when the denominator is 0
    numerator: int
    denominator: int


@dataclass(frozen=True)
class SessionTimer:
    elapsed_seconds: int
    target_min: int
    over_target: bool
    waiting: int  # students still waiting for this counsellor (shown when over target, CQ-47)


def day_bounds(day: dt.date = None):
    day = day or timezone.localdate()
    start = timezone.make_aware(dt.datetime.combine(day, dt.time.min))
    return start, start + dt.timedelta(days=1)


def _mean(values) -> Average:
    values = list(values)
    return Average(sum(values) / len(values) if values else None, len(values))


def format_average(value, n: int) -> str:
    """ "{value} (from {n})", or "—" when there is nothing to average."""
    return NO_DATA if not n else f"{value} (from {n})"


def format_minutes(avg: Average) -> str:
    if not avg.n or avg.seconds is None:
        return NO_DATA
    return format_average(f"{round(avg.seconds / 60)} min", avg.n)


# --- Wait ---------------------------------------------------------------------------------------


def wait_seconds(student: Student, now=None) -> float | None:
    """called_at − queue_at once called; now − queue_at while waiting; None otherwise."""
    if student.called_at is not None:
        return (student.called_at - student.queue_at).total_seconds()
    if student.status == StudentStatus.WAITING:
        return ((now or timezone.now()) - student.queue_at).total_seconds()
    return None


def average_wait(centre, day: dt.date = None) -> Average:
    """Mean of called_at − queue_at over the centre's students called today (CQ-13)."""
    start, end = day_bounds(day)
    rows = Student.objects.filter(centre_id=centre.pk, called_at__gte=start, called_at__lt=end).values_list(
        "called_at", "queue_at"
    )
    return _mean((called - queued).total_seconds() for called, queued in rows)


# --- Sessions -----------------------------------------------------------------------------------


def _records_today(centre, counsellor=None, day: dt.date = None):
    start, end = day_bounds(day)
    qs = SessionRecord.objects.filter(centre_id=centre.pk, ended_at__gte=start, ended_at__lt=end)
    if counsellor is not None:
        qs = qs.filter(counsellor_id=counsellor.pk)
    return qs


def average_session_length(centre, counsellor=None, day: dt.date = None) -> Average:
    """Mean of ended_at − started_at over today's SessionRecords (CQ-21/38/61)."""
    rows = _records_today(centre, counsellor, day).values_list("started_at", "ended_at")
    return _mean((end - start).total_seconds() for start, end in rows)


def counselled_today(counsellor, centre, day: dt.date = None) -> int:
    """Count of today's SessionRecords for the counsellor at the centre (CQ-38)."""
    return _records_today(centre, counsellor, day).count()


def session_timer(student: Student, now=None) -> SessionTimer | None:
    """Elapsed / target for the running session (CQ-47). None before the session starts."""
    if student.status != StudentStatus.IN_SESSION or student.started_at is None:
        return None
    elapsed = int(((now or timezone.now()) - student.started_at).total_seconds())
    target = student.centre.settings.target_session_min
    waiting = Student.objects.filter(
        centre_id=student.centre_id, counsellor_id=student.counsellor_id, status=StudentStatus.WAITING
    ).count()
    return SessionTimer(elapsed, target, elapsed > target * 60, waiting)


# --- Centre and cohort figures ------------------------------------------------------------------


def counsellors_on_site(centre) -> int:
    """Postings on desk or on a break (CQ-13)."""
    return Posting.objects.filter(centre_id=centre.pk, duty__in=[Duty.ON_DESK, Duty.ON_BREAK]).count()


def late_count(centre, now=None) -> int:
    """Waiting students past the wait promise (CQ-33). Same rule as `is_late`."""
    limit = (now or timezone.now()) - dt.timedelta(minutes=centre.settings.wait_sla_min)
    return Student.objects.filter(
        centre_id=centre.pk, status=StudentStatus.WAITING, queue_at__lt=limit
    ).count()


def no_show_rate(students) -> Rate:
    """no_show / (done + no_show) over a Student queryset (CQ-61); value None when nobody finished."""
    no_show = students.filter(status=StudentStatus.NO_SHOW).count()
    done = students.filter(status=StudentStatus.DONE).count()
    denominator = done + no_show
    return Rate(no_show / denominator if denominator else None, no_show, denominator)


COUNSELLED_OR_QUEUED = (
    StudentStatus.WAITING,
    StudentStatus.CALLED,
    StudentStatus.IN_SESSION,
    StudentStatus.DONE,
)


def counselled_or_queued(students) -> int:
    """Students with status in (waiting, called, in_session, done) (CQ-61)."""
    return students.filter(status__in=COUNSELLED_OR_QUEUED).count()
