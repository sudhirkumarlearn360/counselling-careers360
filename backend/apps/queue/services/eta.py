"""Average session, position and ETA (CQ-21, CQ-22) and the late flag (CQ-33). Read-only."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

from django.utils import timezone

from apps.counsellors.services import current_live_posting
from apps.queue.models import StudentStatus
from apps.queue.selectors import active_student, waiting_queue
from apps.queue.services.metrics import average_session_length

MIN_REMAINING = dt.timedelta(minutes=2)


@dataclass(frozen=True)
class Eta:
    ahead: int  # waiting students in front of me at my desk; never negative
    is_next: bool  # show "You're next" instead of the position block
    minutes: int  # always shown as approximate ("about")
    at: dt.datetime


def avg_session(counsellor, centre=None) -> dt.timedelta:
    """Mean session length today at this centre, from SessionRecord; else `expected_session_min`."""
    if centre is None:
        posting = current_live_posting(counsellor)
        centre = posting.centre if posting else None
    if centre is not None:
        avg = average_session_length(centre, counsellor)
        if avg.n:
            return dt.timedelta(seconds=avg.seconds)
    return dt.timedelta(minutes=counsellor.expected_session_min)


def eta_for(student, now=None):
    """Eta for a waiting student, or None if the student is not waiting."""
    if student.status != StudentStatus.WAITING:
        return None
    now = now or timezone.now()
    ids = list(waiting_queue(student.counsellor_id, student.centre_id).values_list("id", flat=True))
    if student.id not in ids:  # changed since the caller loaded it
        return None
    pos = ids.index(student.id)
    avg = avg_session(student.counsellor, student.centre)
    current = active_student(student.counsellor_id, student.centre_id)
    if current is None:
        remaining = dt.timedelta(0)
    elif current.status == StudentStatus.IN_SESSION and current.started_at is not None:
        remaining = max(MIN_REMAINING, avg - (now - current.started_at))
    else:
        remaining = avg
    minutes = math.ceil((remaining + pos * avg).total_seconds() / 60)
    return Eta(ahead=pos, is_next=pos == 0, minutes=minutes, at=now + dt.timedelta(minutes=minutes))


def is_late(student, now=None) -> bool:
    """Waiting longer than the centre's wait promise, measured from queue_at (resets on rejoin)."""
    if student.status != StudentStatus.WAITING:
        return False
    sla = dt.timedelta(minutes=student.centre.settings.wait_sla_min)
    return (now or timezone.now()) - student.queue_at > sla
