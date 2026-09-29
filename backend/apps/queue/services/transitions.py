"""Every student status change (queue-engine skill, "Transitions"). The only writer of status,
counsellor, queue_at and priority.

Each service is atomic and takes locks in the one fixed order: TokenSequence -> postings (by id) ->
student. Taking the sequence lock first serialises desk actions with check-in and close per centre,
and means the first plain read in the transaction opens its snapshot after any competing commit.
`actor` is the StaffUser who acted (None = the student); `on_behalf_of` is the counsellor whose desk an
ops lead is working (CQ-5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.centres.exceptions import CentreNotLive
from apps.centres.models import Centre, CentreStatus
from apps.common.exceptions import NeedsConfirmation
from apps.counsellors.models import Posting
from apps.counsellors.services import current_live_posting
from apps.messaging.services import send_template
from apps.queue.exceptions import (
    ConsentPending,
    DeskBusy,
    InvalidTransition,
    QueueClosed,
    QueueEmpty,
    TokenNotCallable,
    TokenNotFound,
)
from apps.queue.models import (
    ACTIVE_STATUSES,
    AuditEvent,
    Consent,
    SessionRecord,
    Student,
    StudentStatus,
)
from apps.queue.selectors import waiting_queue
from apps.queue.services.audit import record
from apps.queue.services.checkin import STREAM_LABELS, stream_warning
from apps.queue.services.locks import (
    centre_status,
    lock_desk,
    lock_postings,
    lock_sequence,
    lock_student,
)

Verb = AuditEvent.Verb


@dataclass
class CallResult:
    student: Student
    warnings: list = field(default_factory=list)


def _centre_for(counsellor, centre):
    """The centre a desk action applies to: the given one, else the counsellor's live posting today."""
    if centre is not None:
        return centre
    posting = current_live_posting(counsellor)
    if posting is None:
        raise InvalidTransition(f"{counsellor.name} isn't posted to a live centre today.")
    return posting.centre


def _require(student: Student, allowed, what: str) -> None:
    if student.status not in allowed:
        raise InvalidTransition(f"Token {student.token} can't be {what} (it is {student.status}).")


# --- Calling (CQ-39, CQ-40) --------------------------------------------------------------------


def _busy_guard(counsellor, centre_id) -> None:
    busy = (
        Student.objects.filter(centre_id=centre_id, counsellor_id=counsellor.id, status__in=ACTIVE_STATUSES)
        .order_by("id")
        .first()
    )
    if busy is not None:
        raise DeskBusy(f"Finish {busy.token} before calling the next student.", data={"token": busy.token})


def _do_call(student: Student, counsellor, actor, on_behalf_of) -> list:
    """Reassign to `counsellor` if needed, mark called, notify. The desk and student are already locked."""
    warnings = []
    if student.counsellor_id != counsellor.id:
        if not counsellor.covers(student.stream):
            stream = STREAM_LABELS.get(student.stream, student.stream)
            warnings.append(
                {"code": "stream_not_covered", "message": f"{counsellor.name} doesn't cover {stream}."}
            )
        previous = student.counsellor_id
        student.counsellor = counsellor
        student.priority = 0
        record(
            student,
            Verb.MOVED,
            actor,
            on_behalf_of,
            from_counsellor_id=previous,
            to_counsellor_id=counsellor.id,
            via="call_token",
        )
        student.save(update_fields=["counsellor", "priority", "updated_at"])
        send_template(student, "desk_changed")
    student.status = StudentStatus.CALLED
    student.called_at = timezone.now()
    student.save(update_fields=["status", "called_at", "updated_at"])
    record(student, Verb.CALLED, actor, on_behalf_of, counsellor_id=counsellor.id)
    send_template(student, "turn_called")
    return warnings


def call_next(counsellor, centre=None, actor=None, on_behalf_of=None) -> CallResult:
    """Call the longest-waiting student at this desk (CQ-39)."""
    centre = _centre_for(counsellor, centre)
    with transaction.atomic():
        lock_sequence(centre.pk)
        lock_desk(centre.pk, counsellor)
        _busy_guard(counsellor, centre.pk)
        first = waiting_queue(counsellor, centre).select_for_update(of=("self",)).first()
        if first is None:
            raise QueueEmpty()
        student = lock_student(first.pk)
        return CallResult(student, _do_call(student, counsellor, actor, on_behalf_of))


_NOT_CALLABLE = {
    StudentStatus.RELEASED: "Token {token} was released — requeue it to call.",
    StudentStatus.NO_SHOW: "Token {token} was marked no-show — requeue it to call.",
    StudentStatus.NOT_COUNSELLED: "Token {token} wasn't counselled before closing.",
}


def call_token(counsellor, raw_token, centre=None, actor=None, on_behalf_of=None) -> CallResult:
    """Call the token a student read out (CQ-40); reassigns it to this desk if it was elsewhere."""
    centre = _centre_for(counsellor, centre)
    token = str(raw_token).strip().upper()
    with transaction.atomic():
        lock_sequence(centre.pk)
        lock_desk(centre.pk, counsellor)
        _busy_guard(counsellor, centre.pk)
        found = Student.objects.filter(centre_id=centre.pk, token=token).values_list("pk", flat=True).first()
        if found is None:
            raise TokenNotFound(f"No token {token} at this centre today.")
        student = lock_student(found)
        status = student.status
        if status == StudentStatus.DONE:
            at = timezone.localtime(student.ended_at) if student.ended_at else None
            when = f" at {at:%H:%M}" if at else ""
            raise TokenNotCallable(f"Token {token} was already counselled{when}.", data={"status": status})
        if status in _NOT_CALLABLE:
            raise TokenNotCallable(_NOT_CALLABLE[status].format(token=token), data={"status": status})
        if status in ACTIVE_STATUSES:  # a different desk's active student (this desk is not busy)
            desk = (
                Posting.objects.filter(centre_id=centre.pk, counsellor_id=student.counsellor_id)
                .values_list("desk_label", flat=True)
                .first()
            )
            raise TokenNotCallable(
                f"Token {token} is already with {student.counsellor.name} at {desk}.",
                data={"status": status},
            )
        return CallResult(student, _do_call(student, counsellor, actor, on_behalf_of))


# --- The session (CQ-42, CQ-47, CQ-49) ---------------------------------------------------------


@transaction.atomic
def start_session(student, actor=None, on_behalf_of=None) -> Student:
    lock_sequence(student.centre_id)
    s = lock_student(student.pk)
    _require(s, (StudentStatus.CALLED,), "started")
    if s.consent != Consent.GIVEN:
        raise ConsentPending()
    s.status = StudentStatus.IN_SESSION
    s.started_at = timezone.now()
    s.save(update_fields=["status", "started_at", "updated_at"])
    record(s, Verb.STARTED, actor, on_behalf_of)
    return s


@transaction.atomic
def complete_session(student, actor=None, on_behalf_of=None):
    """Finish the session, write its SessionRecord. Returns the next waiting token at this desk, or None."""
    lock_sequence(student.centre_id)
    s = lock_student(student.pk)
    _require(s, (StudentStatus.IN_SESSION,), "completed")
    s.status = StudentStatus.DONE
    s.ended_at = timezone.now()
    s.save(update_fields=["status", "ended_at", "updated_at"])
    SessionRecord.objects.create(
        student=s,
        counsellor_id=s.counsellor_id,
        centre_id=s.centre_id,
        queue_at=s.queue_at,
        called_at=s.called_at,
        started_at=s.started_at,
        ended_at=s.ended_at,
        outcome=s.outcome,
    )
    record(s, Verb.COMPLETED, actor, on_behalf_of)
    send_template(s, "session_done")
    nxt = waiting_queue(s.counsellor_id, s.centre_id).values_list("token", flat=True).first()
    return nxt


# --- Missing, leaving, coming back (CQ-25, CQ-36, CQ-46) ---------------------------------------


@transaction.atomic
def mark_missed(student, actor=None, on_behalf_of=None) -> Student:
    """A called student didn't turn up: back in the queue, then no-show at the recall limit.

    After the centre closed there is no queue to rejoin, so the miss ends as `not_counselled`.
    """
    lock_sequence(student.centre_id)
    closed = centre_status(student.centre_id) == CentreStatus.CLOSED
    s = lock_student(student.pk)
    _require(s, (StudentStatus.CALLED,), "marked missed")
    s.recalls += 1
    limit = s.centre.settings.recall_limit
    if closed:
        s.status, s.called_at, s.priority = StudentStatus.NOT_COUNSELLED, None, 0
        s.save(update_fields=["status", "recalls", "called_at", "priority", "updated_at"])
        record(s, Verb.MISSED, actor, on_behalf_of, recalls=s.recalls, to="not_counselled")
    elif s.recalls >= limit:
        s.status, s.called_at, s.priority = StudentStatus.NO_SHOW, None, 0
        s.save(update_fields=["status", "recalls", "called_at", "priority", "updated_at"])
        record(s, Verb.MISSED, actor, on_behalf_of, recalls=s.recalls)
        record(s, Verb.NO_SHOW, actor, on_behalf_of, recalls=s.recalls)
        send_template(s, "missed_final")
    else:
        s.status, s.called_at, s.priority = StudentStatus.WAITING, None, 0
        s.queue_at = timezone.now()
        s.save(update_fields=["status", "recalls", "called_at", "priority", "queue_at", "updated_at"])
        record(s, Verb.MISSED, actor, on_behalf_of, recalls=s.recalls)
        send_template(s, "missed_first")
    return s


@transaction.atomic
def release(student, actor=None, on_behalf_of=None) -> Student:
    """The student gives up their turn (CQ-25); only while waiting or called."""
    lock_sequence(student.centre_id)
    s = lock_student(student.pk)
    _require(s, (StudentStatus.WAITING, StudentStatus.CALLED), "released")
    s.status, s.called_at, s.priority = StudentStatus.RELEASED, None, 0
    s.save(update_fields=["status", "called_at", "priority", "updated_at"])
    record(s, Verb.RELEASED, actor, on_behalf_of)
    send_template(s, "released")
    return s


@transaction.atomic
def requeue(student, actor=None, on_behalf_of=None) -> Student:
    """Put a no-show, released or completed student back in the queue with the same token (CQ-36)."""
    lock_sequence(student.centre_id)
    closed = centre_status(student.centre_id) == CentreStatus.CLOSED
    s = lock_student(student.pk)
    _require(s, (StudentStatus.NO_SHOW, StudentStatus.RELEASED, StudentStatus.DONE), "requeued")
    if closed:
        raise QueueClosed()
    previous = s.status
    s.status, s.recalls, s.priority = StudentStatus.WAITING, 0, 0
    s.queue_at = timezone.now()
    s.called_at = s.started_at = s.ended_at = None
    s.save(
        update_fields=[
            "status",
            "recalls",
            "priority",
            "queue_at",
            "called_at",
            "started_at",
            "ended_at",
            "updated_at",
        ]
    )
    record(s, Verb.REQUEUED, actor, on_behalf_of, **{"from": previous})
    return s


# --- Reordering (CQ-35, CQ-41) -----------------------------------------------------------------


@transaction.atomic
def move(student, counsellor, actor=None, confirm: bool = False, on_behalf_of=None) -> Student:
    """Move a waiting student to another counsellor at the same centre, keeping token and queue_at."""
    lock_sequence(student.centre_id)
    postings = lock_postings(student.centre_id, [student.counsellor_id, counsellor.id])
    s = lock_student(student.pk)
    _require(s, (StudentStatus.WAITING,), "moved")
    if counsellor.id == s.counsellor_id or counsellor.id not in postings:
        raise InvalidTransition(f"Token {s.token} can't be moved to {counsellor.name}.")
    if not counsellor.covers(s.stream) and not confirm:
        raise NeedsConfirmation(stream_warning(counsellor, s.stream), data={"counsellor_id": counsellor.id})
    previous = s.counsellor_id
    s.counsellor, s.priority = counsellor, 0
    s.save(update_fields=["counsellor", "priority", "updated_at"])
    record(s, Verb.MOVED, actor, on_behalf_of, from_counsellor_id=previous, to_counsellor_id=counsellor.id)
    send_template(s, "desk_changed")
    return s


@transaction.atomic
def pull_forward(student, actor=None, on_behalf_of=None) -> Student:
    """Make a waiting student next at their desk; everyone else keeps their relative order (CQ-41)."""
    lock_sequence(student.centre_id)
    lock_postings(student.centre_id, [student.counsellor_id])
    s = lock_student(student.pk)
    _require(s, (StudentStatus.WAITING,), "pulled forward")
    queue = list(waiting_queue(s.counsellor_id, s.centre_id).values_list("id", "priority"))
    if not queue or queue[0][0] == s.id:
        raise InvalidTransition(f"Token {s.token} is already next.")
    s.priority = max(p for _, p in queue) + 1
    s.save(update_fields=["priority", "updated_at"])
    record(s, Verb.PULLED_FORWARD, actor, on_behalf_of, priority=s.priority)
    return s


# --- Closing (CQ-8) ----------------------------------------------------------------------------


@transaction.atomic
def close_centre(centre: Centre, actor=None) -> int:
    """Waiting students become `not_counselled` (never no_show), the centre is closed. Returns the count.

    Takes the TokenSequence lock first, like check-in, so no token is issued after the close commits.
    Called or in-session students are left alone so a session in progress is never cut off.
    """
    lock_sequence(centre.pk)
    locked = Centre.objects.select_for_update().get(pk=centre.pk)
    if locked.status != CentreStatus.LIVE:
        raise CentreNotLive()
    waiting = Student.objects.select_for_update().filter(centre=locked, status=StudentStatus.WAITING)
    ids = list(waiting.order_by("id").values_list("id", "token"))
    if ids:
        now = timezone.now()
        AuditEvent.objects.bulk_create(
            [
                AuditEvent(
                    student_id=sid,
                    centre=locked,
                    verb=Verb.CENTRE_CLOSED,
                    actor=actor,
                    at=now,
                    data={"to": "not_counselled"},
                )
                for sid, _ in ids
            ],
            batch_size=500,
        )
        Student.objects.filter(pk__in=[i for i, _ in ids]).update(
            status=StudentStatus.NOT_COUNSELLED, updated_at=timezone.now()
        )
    locked.status = CentreStatus.CLOSED
    locked.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        centre=locked,
        verb=Verb.CENTRE_CLOSED,
        actor=actor,
        data={"not_counselled": len(ids), "tokens": [t for _, t in ids]},
    )
    centre.status = CentreStatus.CLOSED
    return len(ids)
