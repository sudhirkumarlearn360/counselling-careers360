"""Check-in (CQ-19, CQ-20, CQ-29, CQ-30, CQ-54): duplicate check, assignment, numbering, confirmation."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.common.choices import Stream
from apps.common.exceptions import NeedsConfirmation
from apps.common.validators import normalise_mobile
from apps.counsellors.models import Counsellor, Duty
from apps.messaging.services import send_template
from apps.queue.exceptions import CentreNotLive, CounsellorNotOnDesk, DuplicateToken
from apps.queue.models import OPEN_STATUSES, AuditEvent, Consent, Source, Student
from apps.queue.services.assignment import assign_counsellor
from apps.queue.services.audit import record
from apps.queue.services.locks import centre_status, lock_desk, lock_sequence
from apps.queue.services.tokens import next_token

STREAM_LABELS = dict(Stream.choices)
DETAIL_FIELDS = ("name", "school", "email", "stream", "klass", "course", "clarity")
LIST_FIELDS = ("exams", "help")


def stream_warning(counsellor, stream: str) -> str:
    """The CQ-35 stream-mismatch prompt (also used for a manual desk pick, CQ-29)."""
    return f"{counsellor.name} doesn't cover {STREAM_LABELS.get(stream, stream)}. Move anyway?"


def _fmt_date(day) -> str:
    return f"{day.day} {day:%b %Y}"


def _refuse_unless_live(centre: Centre) -> None:
    status = centre_status(centre.pk)
    if status == CentreStatus.LIVE:
        return
    if status == CentreStatus.CLOSED:
        raise CentreNotLive(
            f"Check-in closed at {centre.closes_at:%H:%M}. Please see the front desk.",
            data={"status": status, "close_time": f"{centre.closes_at:%H:%M}"},
        )
    raise CentreNotLive(
        f"This centre isn't open for check-in — it runs on {_fmt_date(centre.date)}.",
        data={"status": status, "date": centre.date.isoformat()},
    )


def _manual_desk(centre, counsellor_id, stream: str, confirm: bool):
    """Reception picks the counsellor (CQ-29 after NoCounsellorFor*), with the stream warning."""
    counsellor = Counsellor.objects.get(pk=counsellor_id)
    posting = lock_desk(centre.pk, counsellor)
    if posting.duty != Duty.ON_DESK:  # a student must never be sent to an empty chair (CQ-37)
        raise CounsellorNotOnDesk(f"{counsellor.name} isn't on desk right now.")
    if not counsellor.covers(stream) and not confirm:
        raise NeedsConfirmation(stream_warning(counsellor, stream), data={"counsellor_id": counsellor.id})
    return posting


@transaction.atomic
def check_in(centre: Centre, data: dict, source: str, actor=None, *, confirm: bool = False) -> Student:
    """Issue a token. Input is already validated by the serializer; the mobile is normalised here.

    Lock order: the TokenSequence row first (serialises check-ins and close per centre), then the
    duplicate check, then assignment (locks postings), then numbering. `data["counsellor_id"]` is a
    manual pick and is honoured only for desk check-ins; `confirm=True` accepts its stream warning.
    Raises CentreNotLive, DuplicateToken, NoCounsellorOnDuty, NoCounsellorForStream, NeedsConfirmation.
    """
    lock_sequence(centre.pk)
    _refuse_unless_live(centre)
    mobile = normalise_mobile(data.get("mobile"))
    existing = (
        Student.objects.select_for_update()
        .filter(centre_id=centre.pk, mobile=mobile, status__in=OPEN_STATUSES)
        .order_by("id")
        .first()
    )
    if existing is not None:
        raise DuplicateToken(existing)

    stream = data.get("stream")
    manual = source == Source.DESK and data.get("counsellor_id")
    posting = (
        _manual_desk(centre, data["counsellor_id"], stream, confirm)
        if manual
        else assign_counsellor(centre, stream)
    )
    token = next_token(centre, stream)
    now = timezone.now()
    student = Student(
        centre=centre,
        counsellor=posting.counsellor,
        token=token,
        source=source,
        mobile=mobile,
        parent_mobile=normalise_mobile(data.get("parent_mobile")) if data.get("parent_mobile") else "",
        checkin_at=now,
        queue_at=now,
        consent=Consent.GIVEN if source == Source.SELF else Consent.PENDING,
        consent_at=now if source == Source.SELF else None,
    )
    for field in DETAIL_FIELDS:
        setattr(student, field, (data.get(field) or "").strip())
    for field in LIST_FIELDS:
        setattr(student, field, list(data.get(field) or []))
    student.save()
    record(
        student,
        AuditEvent.Verb.CHECKED_IN,
        actor,
        source=source,
        token=token,
        counsellor_id=posting.counsellor_id,
        desk=posting.desk_label,
        manual=bool(manual),
    )
    key = "token_confirm_self" if source == Source.SELF else "token_confirm_desk"
    send_template(student, key, desk=posting.desk_label)
    return student
