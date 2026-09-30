"""CQ-21 / CQ-22: position, ETA and the average-session basis (queue-engine: Average session & ETA)."""

import datetime as dt

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.queue.models import StudentStatus
from apps.queue.services import avg_session, eta_for
from tests.queue.helpers import live_centre, post, raw_student, session_record

pytestmark = pytest.mark.django_db

NOW = "2026-09-29 06:30:00+00:00"  # 12:00 IST
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def desk():
    centre = live_centre(date=dt.date(2026, 9, 29))
    p = post(centre, "Meera", ["PCM"], "Desk 1", expected=10)
    return centre, p.counsellor


def queue_of(centre, c, n):
    base = timezone.now() - dt.timedelta(minutes=30)
    return [raw_student(centre, c, f"PCM-{i + 1:02d}", queue_at=base + i * MIN) for i in range(n)]


@freeze_time(NOW)
def test_cq22_first_in_queue_is_next_with_nobody_ahead(desk):
    centre, c = desk
    a, b = queue_of(centre, c, 2)
    eta = eta_for(a)
    assert (eta.ahead, eta.is_next, eta.minutes) == (0, True, 0)
    assert eta.at == timezone.now()


@freeze_time(NOW)
def test_cq21_position_counts_only_waiting_students_ahead_at_my_desk(desk):
    centre, c = desk
    other = post(centre, "Other", ["PCM"], "Desk 2").counsellor
    raw_student(centre, other, "PCM-90", queue_at=timezone.now() - dt.timedelta(hours=1))
    a, b, third = queue_of(centre, c, 3)
    eta = eta_for(third)
    assert (eta.ahead, eta.is_next, eta.minutes) == (2, False, 20)  # expected 10 min each
    assert eta.at == timezone.now() + 20 * MIN


@freeze_time(NOW)
def test_cq21_called_not_started_student_is_not_ahead_but_adds_a_full_session(desk):
    centre, c = desk
    raw_student(centre, c, "PCM-50", status=StudentStatus.CALLED, called_at=timezone.now())
    a, b = queue_of(centre, c, 2)
    assert (eta_for(a).ahead, eta_for(a).is_next, eta_for(a).minutes) == (0, True, 10)
    assert (eta_for(b).ahead, eta_for(b).minutes) == (1, 20)


@freeze_time(NOW)
def test_cq21_running_session_counts_its_remaining_time_with_a_two_minute_floor(desk):
    centre, c = desk
    cur = raw_student(
        centre, c, "PCM-50", status=StudentStatus.IN_SESSION, started_at=timezone.now() - 3 * MIN
    )
    (a,) = queue_of(centre, c, 1)
    assert eta_for(a).minutes == 7
    cur.started_at = timezone.now() - dt.timedelta(minutes=9, seconds=30)
    cur.save()
    assert eta_for(a).minutes == 2
    cur.started_at = timezone.now() - 40 * MIN  # overrun: still 2, never negative
    cur.save()
    assert eta_for(a).minutes == 2 and eta_for(a).ahead >= 0


@freeze_time(NOW)
def test_cq21_minutes_round_up(desk):
    centre, c = desk
    raw_student(
        centre,
        c,
        "PCM-50",
        status=StudentStatus.IN_SESSION,
        started_at=timezone.now() - dt.timedelta(minutes=3, seconds=30),
    )
    (a,) = queue_of(centre, c, 1)
    assert eta_for(a).minutes == 7  # 6.5 min remaining -> about 7


@freeze_time(NOW)
def test_cq21_avg_session_uses_today_session_records_else_expected(desk):
    centre, c = desk
    assert avg_session(c, centre) == 10 * MIN
    done = raw_student(centre, c, "PCM-40", status=StudentStatus.DONE)
    session_record(done, 6)
    session_record(done, 8)  # a requeued student keeps both sessions
    yesterday = timezone.now() - dt.timedelta(days=1)
    session_record(done, 60, ended_at=yesterday)  # not today: ignored
    elsewhere = live_centre("Indore", date=dt.date(2026, 9, 29))
    session_record(raw_student(elsewhere, c, "PCM-01", status=StudentStatus.DONE), 30)  # other centre
    assert avg_session(c, centre) == 7 * MIN
    (a, b) = queue_of(centre, c, 2)
    assert eta_for(b).minutes == 7


@freeze_time(NOW)
def test_cq21_non_waiting_student_has_no_eta(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-50", status=StudentStatus.CALLED)
    assert eta_for(s) is None


@freeze_time(NOW)
def test_cq21_position_updates_when_someone_ahead_leaves(desk):
    from apps.queue.services import release

    centre, c = desk
    a, b, third = queue_of(centre, c, 3)
    assert eta_for(third).ahead == 2
    release(a)
    assert eta_for(third).ahead == 1
