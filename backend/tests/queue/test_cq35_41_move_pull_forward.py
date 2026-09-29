"""CQ-35 move to another counsellor, CQ-41 pull forward."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.common.exceptions import NeedsConfirmation
from apps.messaging.models import Message
from apps.queue.exceptions import InvalidTransition
from apps.queue.models import AuditEvent, StudentStatus
from apps.queue.selectors import waiting_queue
from apps.queue.services import move, pull_forward
from tests.queue.helpers import live_centre, ops_lead, post, raw_student, reception

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def hall():
    centre = live_centre()
    meera = post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor
    asha = post(centre, "Asha Nair", ["PCM"], "Desk 3").counsellor
    ravi = post(centre, "Ravi Shah", ["COM"], "Desk 2").counsellor
    return centre, meera, asha, ravi


def test_cq35_move_keeps_token_and_original_queue_time_and_notifies(hall):
    centre, meera, asha, _ = hall
    now = timezone.now()
    raw_student(centre, asha, "PCM-05", queue_at=now - 5 * MIN)
    s = raw_student(centre, meera, "PCM-02", queue_at=now - 20 * MIN, priority=3)
    who = reception(centre)
    s = move(s, asha, who)
    assert s.counsellor == asha and s.token == "PCM-02" and s.priority == 0
    assert s.queue_at == now - 20 * MIN
    assert [x.token for x in waiting_queue(asha, centre)] == ["PCM-02", "PCM-05"]  # not at the back
    assert Message.objects.get(student=s, template="desk_changed").body == (
        "You've been moved to Asha Nair, Desk 3. Token PCM-02 stays the same."
    )
    ev = AuditEvent.objects.get(student=s, verb="moved")
    assert ev.actor == who and ev.data["from_counsellor_id"] == meera.id


def test_cq35_move_to_uncovered_stream_needs_confirmation(hall):
    centre, meera, _, ravi = hall
    s = raw_student(centre, meera, "PCM-02")
    with pytest.raises(NeedsConfirmation) as err:
        move(s, ravi, None)
    assert err.value.message == "Ravi Shah doesn't cover Science – PCM. Move anyway?"
    s.refresh_from_db()
    assert s.counsellor == meera
    assert move(s, ravi, None, confirm=True).counsellor == ravi


@pytest.mark.parametrize(
    "status", [StudentStatus.IN_SESSION, StudentStatus.CALLED, StudentStatus.DONE, StudentStatus.RELEASED]
)
def test_cq35_only_waiting_students_can_be_moved(hall, status):
    centre, meera, asha, _ = hall
    with pytest.raises(InvalidTransition):
        move(raw_student(centre, meera, "PCM-02", status=status), asha, None)


def test_cq35_cannot_move_to_the_current_counsellor_or_another_centre(hall):
    centre, meera, _, _ = hall
    s = raw_student(centre, meera, "PCM-02")
    with pytest.raises(InvalidTransition):
        move(s, meera, None)
    far = live_centre("Indore")
    outsider = post(far, "Outsider", ["PCM"], "Desk 1").counsellor
    with pytest.raises(InvalidTransition):
        move(s, outsider, None)


def test_cq41_pull_forward_makes_student_next_and_keeps_others_order(hall):
    centre, meera, _, _ = hall
    now = timezone.now()
    tokens = ["PCM-01", "PCM-02", "PCM-03", "PCM-04"]
    rows = [raw_student(centre, meera, t, queue_at=now - (10 - i) * MIN) for i, t in enumerate(tokens)]
    lead = ops_lead()
    s = pull_forward(rows[2], lead, on_behalf_of=meera)
    assert s.priority == 1
    assert [x.token for x in waiting_queue(meera, centre)] == ["PCM-03", "PCM-01", "PCM-02", "PCM-04"]
    s4 = pull_forward(rows[3], lead)
    assert s4.priority == 2
    assert [x.token for x in waiting_queue(meera, centre)] == ["PCM-04", "PCM-03", "PCM-01", "PCM-02"]
    ev = AuditEvent.objects.filter(student=rows[2], verb="pulled_forward").get()
    assert ev.actor == lead and ev.on_behalf_of == meera


def test_cq41_top_student_cannot_be_pulled_forward(hall):
    centre, meera, _, _ = hall
    now = timezone.now()
    top = raw_student(centre, meera, "PCM-01", queue_at=now - 10 * MIN)
    raw_student(centre, meera, "PCM-02", queue_at=now - 5 * MIN)
    with pytest.raises(InvalidTransition):
        pull_forward(top, None)


def test_cq41_only_waiting_students_can_be_pulled(hall):
    centre, meera, _, _ = hall
    with pytest.raises(InvalidTransition):
        pull_forward(raw_student(centre, meera, "PCM-01", status=StudentStatus.CALLED), None)
