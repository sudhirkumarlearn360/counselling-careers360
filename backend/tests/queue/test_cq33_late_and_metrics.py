"""CQ-33 late flag and the single Metrics definitions (CQ-13/38/61)."""

import datetime as dt

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.counsellors.models import Duty
from apps.queue.models import Student, StudentStatus
from apps.queue.services import call_next, is_late, mark_missed, metrics
from tests.queue.helpers import live_centre, post, raw_student, session_record

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)
NOW = "2026-09-29 06:30:00+00:00"


@pytest.fixture
def desk():
    centre = live_centre(date=dt.date(2026, 9, 29))
    return centre, post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor


@freeze_time(NOW)
def test_cq33_waiting_past_the_wait_promise_is_late(desk):
    centre, c = desk
    now = timezone.now()
    late = raw_student(centre, c, "PCM-01", queue_at=now - 31 * MIN)
    edge = raw_student(centre, c, "PCM-02", queue_at=now - 30 * MIN)
    fresh = raw_student(centre, c, "PCM-03", queue_at=now - 5 * MIN)
    assert (is_late(late), is_late(edge), is_late(fresh)) == (True, False, False)
    assert metrics.late_count(centre) == 1
    centre.settings.wait_sla_min = 4
    centre.settings.save()
    assert is_late(Student.objects.get(pk=fresh.pk)) is True


@freeze_time(NOW)
def test_cq33_flag_clears_on_call_and_rejoin_resets_the_clock(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", queue_at=timezone.now() - 45 * MIN)
    assert is_late(s)
    s = call_next(c, centre=centre).student
    assert not is_late(s)
    s = mark_missed(s)
    assert s.status == StudentStatus.WAITING and not is_late(s)


@freeze_time(NOW)
def test_cq13_wait_is_called_minus_queue_and_average_states_n(desk):
    centre, c = desk
    now = timezone.now()
    assert metrics.average_wait(centre) == metrics.Average(None, 0)
    assert metrics.format_minutes(metrics.average_wait(centre)) == "—"
    raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, queue_at=now - 20 * MIN, called_at=now)
    raw_student(
        centre, c, "PCM-02", status=StudentStatus.DONE, queue_at=now - 40 * MIN, called_at=now - 30 * MIN
    )
    w = raw_student(centre, c, "PCM-03", queue_at=now - 7 * MIN)  # waiting: not in the average
    avg = metrics.average_wait(centre)
    assert avg == metrics.Average(15 * 60, 2)
    assert metrics.format_minutes(avg) == "15 min (from 2)"
    assert metrics.wait_seconds(w) == 7 * 60


@freeze_time(NOW)
def test_cq38_counselled_today_and_session_length_from_session_records(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.DONE)
    session_record(s, 10)
    session_record(s, 20)  # requeued and seen again: two sessions
    session_record(s, 99, ended_at=timezone.now() - dt.timedelta(days=1))
    assert metrics.counselled_today(c, centre) == 2
    assert metrics.average_session_length(centre, c) == metrics.Average(15 * 60, 2)
    assert metrics.average_session_length(centre) == metrics.Average(15 * 60, 2)


def test_cq13_counsellors_on_site_counts_on_desk_and_on_break(desk):
    centre, _ = desk
    post(centre, "Break", ["COM"], "Desk 2", duty=Duty.ON_BREAK)
    post(centre, "Off", ["COM"], "Desk 3", duty=Duty.OFF_DUTY)
    assert metrics.counsellors_on_site(centre) == 2


def test_cq61_no_show_rate_and_counselled_or_queued(desk):
    centre, c = desk
    qs = Student.objects.filter(centre=centre)
    assert metrics.no_show_rate(qs) == metrics.Rate(None, 0, 0)
    for i, status in enumerate(
        ["waiting", "called", "in_session", "done", "done", "done", "no_show", "released", "not_counselled"]
    ):
        raw_student(centre, c, f"PCM-{i + 1:02d}", status=status)
    assert metrics.no_show_rate(qs) == metrics.Rate(0.25, 1, 4)
    assert metrics.counselled_or_queued(qs) == 6


def test_cq61_average_format_states_its_n():
    assert metrics.format_average("4.5", 12) == "4.5 (from 12)"
    assert metrics.format_average("4.5", 0) == "—"
