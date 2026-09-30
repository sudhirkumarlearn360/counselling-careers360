"""CQ-46 / CQ-56: missed call -> back in queue, then no-show at the recall limit."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.exceptions import InvalidTransition
from apps.queue.models import AuditEvent, StudentStatus
from apps.queue.services import call_next, mark_missed
from tests.queue.helpers import live_centre, post, raw_student

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def desk():
    centre = live_centre()
    return centre, post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor


def test_cq46_first_miss_returns_to_queue_with_clock_restarted(desk):
    centre, c = desk
    old = timezone.now() - 30 * MIN
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, queue_at=old, called_at=old, priority=4)
    s = mark_missed(s)
    assert s.status == StudentStatus.WAITING and s.recalls == 1
    assert s.queue_at > old and s.called_at is None and s.priority == 0
    assert Message.objects.get(student=s, template="missed_first").body == (
        "We called PCM-01 and missed you. You're back in the queue — next call is the last one."
    )
    assert AuditEvent.objects.get(student=s, verb="missed").data["recalls"] == 1


def test_cq46_second_miss_is_no_show_with_final_message(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, recalls=1)
    s = mark_missed(s)
    assert s.status == StudentStatus.NO_SHOW and s.recalls == 2
    assert Message.objects.get(student=s, template="missed_final").body == (
        "We called PCM-01 2 times. Visit the front desk to get back in the queue."
    )
    assert AuditEvent.objects.filter(student=s, verb="no_show").exists()


def test_cq46_recall_limit_comes_from_centre_settings(desk):
    centre, c = desk
    centre.settings.recall_limit = 3
    centre.settings.save()
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, recalls=1)
    assert mark_missed(s).status == StudentStatus.WAITING


def test_cq46_desk_is_free_to_call_next_after_either_miss(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED)
    nxt = raw_student(centre, c, "PCM-02", queue_at=timezone.now() - 5 * MIN)
    mark_missed(s)
    assert call_next(c, centre=centre).student == nxt  # the missed one rejoined behind


@pytest.mark.parametrize("status", [StudentStatus.WAITING, StudentStatus.IN_SESSION, StudentStatus.DONE])
def test_cq46_only_a_called_student_can_be_missed(desk, status):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=status)
    with pytest.raises(InvalidTransition):
        mark_missed(s)
