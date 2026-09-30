"""CQ-25 release and CQ-36 requeue."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.exceptions import InvalidTransition, QueueClosed
from apps.queue.models import AuditEvent, SessionRecord, StudentStatus
from apps.queue.services import close_centre, release, requeue
from tests.queue.helpers import live_centre, post, raw_student, reception, session_record

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def desk():
    centre = live_centre()
    return centre, post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor


@pytest.mark.parametrize("status", [StudentStatus.WAITING, StudentStatus.CALLED])
def test_cq25_release_from_waiting_or_called(desk, status):
    centre, c = desk
    s = release(raw_student(centre, c, "PCM-01", status=status))
    assert s.status == StudentStatus.RELEASED
    assert Message.objects.get(student=s, template="released").body == (
        "Token PCM-01 is released. You can check in again before 18:00."
    )
    ev = AuditEvent.objects.get(student=s, verb="released")
    assert ev.actor is None  # the student acted


@pytest.mark.parametrize(
    "status", [StudentStatus.IN_SESSION, StudentStatus.DONE, StudentStatus.NO_SHOW, StudentStatus.RELEASED]
)
def test_cq25_release_refused_once_session_started_or_closed(desk, status):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=status)
    with pytest.raises(InvalidTransition):
        release(s)
    s.refresh_from_db()
    assert s.status == status


@pytest.mark.parametrize("status", [StudentStatus.NO_SHOW, StudentStatus.RELEASED, StudentStatus.DONE])
def test_cq36_requeue_keeps_token_restarts_clock_resets_recalls_and_audits(desk, status):
    centre, c = desk
    desk_user = reception(centre)
    old = timezone.now() - 60 * MIN
    s = raw_student(
        centre,
        c,
        "PCM-01",
        status=status,
        queue_at=old,
        called_at=old,
        started_at=old,
        ended_at=old + 10 * MIN,
        recalls=2,
        priority=5,
    )
    s = requeue(s, desk_user)
    assert s.status == StudentStatus.WAITING and s.token == "PCM-01"
    assert s.queue_at > old and s.recalls == 0 and s.priority == 0
    assert (s.called_at, s.started_at, s.ended_at) == (None, None, None)
    ev = AuditEvent.objects.get(student=s, verb="requeued")
    assert ev.actor == desk_user and ev.data["from"] == status and ev.at is not None


def test_cq36_requeue_keeps_earlier_session_records(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.DONE)
    rec = session_record(s, 12)
    requeue(s, None)
    assert list(SessionRecord.objects.filter(student=s)) == [rec]


@pytest.mark.parametrize(
    "status",
    [StudentStatus.WAITING, StudentStatus.CALLED, StudentStatus.IN_SESSION, StudentStatus.NOT_COUNSELLED],
)
def test_cq36_requeue_not_available_for_open_or_not_counselled(desk, status):
    centre, c = desk
    with pytest.raises(InvalidTransition):
        requeue(raw_student(centre, c, "PCM-01", status=status), None)


def test_cq36_requeue_refused_after_the_centre_closed(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.DONE)
    close_centre(centre)
    with pytest.raises(QueueClosed):
        requeue(s, None)
    s.refresh_from_db()
    assert s.status == StudentStatus.DONE
