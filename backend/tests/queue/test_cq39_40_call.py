"""CQ-39 call next, CQ-40 call by token, CQ-23/55 turn alert."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.exceptions import DeskBusy, QueueEmpty, TokenNotCallable, TokenNotFound
from apps.queue.models import AuditEvent, StudentStatus
from apps.queue.services import call_next, call_token
from tests.queue.helpers import live_centre, ops_lead, post, raw_student

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def hall():
    centre = live_centre()
    meera = post(centre, "Meera Iyer", ["PCM", "PCMB"], "Desk 1")
    ravi = post(centre, "Ravi Shah", ["COM"], "Desk 2")
    return centre, meera.counsellor, ravi.counsellor


def test_cq39_call_next_calls_the_longest_waiting_student(hall):
    centre, meera, _ = hall
    now = timezone.now()
    later = raw_student(centre, meera, "PCM-02", queue_at=now - 5 * MIN)
    first = raw_student(centre, meera, "PCM-01", queue_at=now - 10 * MIN)
    result = call_next(meera, centre=centre)
    assert result.student == first and result.warnings == []
    first.refresh_from_db()
    later.refresh_from_db()
    assert first.status == StudentStatus.CALLED and first.called_at is not None
    assert later.status == StudentStatus.WAITING
    assert AuditEvent.objects.filter(student=first, verb="called").exists()
    msg = Message.objects.get(student=first, template="turn_called")
    assert msg.body == "It's your turn. Please go to Desk 1 — Meera Iyer. Your place is held for two calls."


def test_cq39_priority_beats_queue_time(hall):
    centre, meera, _ = hall
    now = timezone.now()
    raw_student(centre, meera, "PCM-01", queue_at=now - 10 * MIN)
    pulled = raw_student(centre, meera, "PCM-02", queue_at=now - 1 * MIN, priority=1)
    assert call_next(meera, centre=centre).student == pulled


def test_cq39_call_next_with_empty_queue(hall):
    centre, meera, ravi = hall
    raw_student(centre, ravi, "COM-01")  # another desk's student is not mine
    with pytest.raises(QueueEmpty) as err:
        call_next(meera, centre=centre)
    assert err.value.message == "Your queue is clear — new check-ins land here as students scan in."


@pytest.mark.parametrize("busy_status", [StudentStatus.CALLED, StudentStatus.IN_SESSION])
def test_cq39_busy_desk_blocks_call_next_and_call_token_naming_the_token(hall, busy_status):
    centre, meera, _ = hall
    raw_student(centre, meera, "PCM-05", status=busy_status)
    waiting = raw_student(centre, meera, "PCM-06")
    for call in (lambda: call_next(meera, centre=centre), lambda: call_token(meera, "PCM-06", centre=centre)):
        with pytest.raises(DeskBusy) as err:
            call()
        assert err.value.message == "Finish PCM-05 before calling the next student."
    waiting.refresh_from_db()
    assert waiting.status == StudentStatus.WAITING


def test_cq23_turn_called_asks_for_consent_when_pending(hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-01", consent="pending")
    call_next(meera, centre=centre)
    body = Message.objects.get(student=s, template="turn_called").body
    assert body.endswith(
        "Your place is held for two calls. "
        "Reply YES to confirm you're here and consent to your details being used for counselling."
    )


def test_cq40_call_token_is_case_and_space_tolerant(hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-07")
    assert call_token(meera, "  pcm-07 ", centre=centre).student == s


def test_cq40_unknown_token(hall):
    centre, meera, _ = hall
    other = live_centre("Indore")
    raw_student(other, post(other, "X", ["PCM"], "Desk 1").counsellor, "PCM-22")  # other centre
    with pytest.raises(TokenNotFound) as err:
        call_token(meera, " pcm-22", centre=centre)
    assert err.value.message == "No token PCM-22 at this centre today."


def test_cq40_done_token_names_the_time_it_was_counselled(hall):
    centre, meera, _ = hall
    ended = timezone.make_aware(dt.datetime.combine(timezone.localdate(), dt.time(11, 5)))
    raw_student(centre, meera, "PCM-03", status=StudentStatus.DONE, ended_at=ended)
    with pytest.raises(TokenNotCallable) as err:
        call_token(meera, "PCM-03", centre=centre)
    assert err.value.message == "Token PCM-03 was already counselled at 11:05."


@pytest.mark.parametrize(
    "status,message",
    [
        (StudentStatus.RELEASED, "Token PCM-04 was released — requeue it to call."),
        (StudentStatus.NO_SHOW, "Token PCM-04 was marked no-show — requeue it to call."),
        (StudentStatus.NOT_COUNSELLED, "Token PCM-04 wasn't counselled before closing."),
    ],
)
def test_cq40_closed_tokens_explain_the_route(hall, status, message):
    centre, meera, _ = hall
    raw_student(centre, meera, "PCM-04", status=status)
    with pytest.raises(TokenNotCallable) as err:
        call_token(meera, "PCM-04", centre=centre)
    assert err.value.message == message
    assert err.value.data["status"] == status


@pytest.mark.parametrize("status", [StudentStatus.CALLED, StudentStatus.IN_SESSION])
def test_cq40_token_active_at_another_desk(hall, status):
    centre, meera, ravi = hall
    raw_student(centre, ravi, "COM-01", status=status, stream="COM")
    with pytest.raises(TokenNotCallable) as err:
        call_token(meera, "COM-01", centre=centre)
    assert err.value.message == "Token COM-01 is already with Ravi Shah at Desk 2."


def test_cq40_cross_desk_call_reassigns_notifies_and_warns_on_stream(hall):
    centre, meera, ravi = hall
    s = raw_student(centre, ravi, "COM-01", stream="COM", priority=2)
    lead = ops_lead()
    result = call_token(meera, "com-01", centre=centre, actor=lead, on_behalf_of=meera)
    s.refresh_from_db()
    assert s.counsellor == meera and s.status == StudentStatus.CALLED
    assert result.warnings == [
        {"code": "stream_not_covered", "message": "Meera Iyer doesn't cover Commerce."}
    ]
    templates = list(Message.objects.filter(student=s).values_list("template", flat=True))
    assert templates == ["desk_changed", "turn_called"]
    assert Message.objects.get(student=s, template="desk_changed").body == (
        "You've been moved to Meera Iyer, Desk 1. Token COM-01 stays the same."
    )
    moved = AuditEvent.objects.get(student=s, verb="moved")
    assert moved.data["from_counsellor_id"] == ravi.id and moved.data["to_counsellor_id"] == meera.id
    called = AuditEvent.objects.get(student=s, verb="called")
    assert called.actor == lead and called.on_behalf_of == meera


def test_cq40_cross_desk_call_within_stream_has_no_warning(hall):
    centre, meera, _ = hall
    other = post(centre, "Asha", ["PCM"], "Desk 3").counsellor
    raw_student(centre, other, "PCM-09")
    assert call_token(meera, "PCM-09", centre=centre).warnings == []


def test_cq39_call_next_uses_current_live_posting_by_default(hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-01")
    assert call_next(meera).student == s
