"""Builders shared by the queue-engine tests (plain functions so threads can use them too)."""

from __future__ import annotations

import datetime as dt
import itertools

from django.utils import timezone

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Duty, Posting
from apps.queue.models import SessionRecord, Student

_mobiles = itertools.count(9000000100)


def live_centre(city="Gwalior", **kw) -> Centre:
    values = {
        "city": city,
        "venue": "Hotel Landmark",
        "date": timezone.localdate(),
        "opens_at": dt.time(10, 0),
        "closes_at": dt.time(18, 0),
        "status": CentreStatus.LIVE,
    }
    values.update(kw)
    return Centre.objects.create(**values)


def post(centre, name, streams, desk, duty=Duty.ON_DESK, expected=15) -> Posting:
    c = Counsellor.objects.create(
        name=name, mobile=str(next(_mobiles)), streams=list(streams), expected_session_min=expected
    )
    return Posting.objects.create(counsellor=c, centre=centre, desk_label=desk, duty=duty)


def data(mobile=None, stream="PCM", **kw) -> dict:
    values = {
        "name": "Asha Rao",
        "school": "DPS Gwalior",
        "mobile": mobile or str(next(_mobiles)),
        "stream": stream,
        "klass": "Class 12",
        "course": "B.Tech",
        "exams": ["JEE"],
        "clarity": "Need help shortlisting",
        "help": ["College selection"],
    }
    values.update(kw)
    return values


def ops_lead(email="lead@careers360.com") -> StaffUser:
    return StaffUser.objects.create_user(email, "x-secret-1", name="Priya Lead", role=Role.OPS_LEAD)


def reception(centre, email="desk@careers360.com") -> StaffUser:
    return StaffUser.objects.create_user(
        email, "x-secret-1", name="Front Desk", role=Role.RECEPTION, centre=centre
    )


def session_record(student: Student, minutes: float, ended_at=None) -> SessionRecord:
    """A completed session of the given length, ending now (or at ended_at)."""
    end = ended_at or timezone.now()
    start = end - dt.timedelta(minutes=minutes)
    return SessionRecord.objects.create(
        student=student,
        counsellor=student.counsellor,
        centre=student.centre,
        queue_at=start - dt.timedelta(minutes=5),
        called_at=start,
        started_at=start,
        ended_at=end,
    )


def raw_student(centre, counsellor, token, status="waiting", **kw) -> Student:
    """A student row written directly (for setting up states the services would reach)."""
    now = timezone.now()
    values = {
        "centre": centre,
        "counsellor": counsellor,
        "token": token,
        "name": "Seeded Student",
        "mobile": str(next(_mobiles)),
        "stream": "PCM",
        "status": status,
        "checkin_at": now,
        "queue_at": now,
        "help": ["Other"],
        "consent": "given",
    }
    values.update(kw)
    return Student.objects.create(**values)
