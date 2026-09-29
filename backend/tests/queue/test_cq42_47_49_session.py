"""CQ-42 consent gate, CQ-47 session timer, CQ-49 complete (and CQ-24 consent record)."""

import datetime as dt

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.messaging.models import Message
from apps.queue.exceptions import ConsentPending, InvalidTransition
from apps.queue.models import AuditEvent, SessionRecord, StudentStatus
from apps.queue.services import complete_session, record_consent, start_session
from apps.queue.services.metrics import session_timer
from tests.queue.helpers import live_centre, ops_lead, post, raw_student

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def desk():
    centre = live_centre()
    return centre, post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor


def test_cq42_start_blocked_while_consent_pending(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, consent="pending")
    with pytest.raises(ConsentPending) as err:
        start_session(s)
    assert err.value.message == "Consent is pending — record verbal consent or resend the request."
    s.refresh_from_db()
    assert s.status == StudentStatus.CALLED and s.started_at is None


def test_cq42_verbal_consent_is_attributed_to_the_counsellor_then_start_works(desk):
    centre, c = desk
    lead = ops_lead()
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED, consent="pending")
    s = record_consent(s, by=c, actor=lead, on_behalf_of=c)
    assert s.consent == "given" and s.consent_by == c and s.consent_at is not None
    ev = AuditEvent.objects.get(student=s, verb="consent_given")
    assert ev.actor == lead and ev.on_behalf_of == c and ev.data["by_counsellor_id"] == c.id
    s = start_session(s)
    assert s.status == StudentStatus.IN_SESSION and s.started_at is not None


def test_cq24_student_consent_has_no_consent_by(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", consent="pending")
    s = record_consent(s, by=None)
    assert s.consent == "given" and s.consent_by is None
    assert AuditEvent.objects.get(student=s, verb="consent_given").actor is None


@pytest.mark.parametrize("status", [StudentStatus.WAITING, StudentStatus.IN_SESSION, StudentStatus.DONE])
def test_cq42_start_requires_a_called_student(desk, status):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=status)
    with pytest.raises(InvalidTransition):
        start_session(s)


def test_cq47_start_writes_started_audit(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED)
    start_session(s)
    assert AuditEvent.objects.filter(student=s, verb="started").exists()


def test_cq47_timer_elapsed_target_and_over_target_with_my_waiting_count(desk):
    centre, c = desk
    with freeze_time("2026-09-29 06:30:00+00:00"):
        s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED)
        assert session_timer(s) is None  # no timer before start
        s = start_session(s)
        raw_student(centre, c, "PCM-02")
        raw_student(centre, c, "PCM-03")
    with freeze_time("2026-09-29 06:40:00+00:00"):
        t = session_timer(s)
        assert (t.elapsed_seconds, t.target_min, t.over_target, t.waiting) == (600, 15, False, 2)
    with freeze_time("2026-09-29 06:46:00+00:00"):
        t = session_timer(s)
        assert t.over_target is True and t.elapsed_seconds == 960
        s.refresh_from_db()
        assert s.status == StudentStatus.IN_SESSION  # never ended automatically


def test_cq49_complete_writes_session_record_and_names_next_token(desk):
    centre, c = desk
    lead = ops_lead()
    queue_at = timezone.now() - 20 * MIN
    s = raw_student(
        centre,
        c,
        "PCM-01",
        status=StudentStatus.IN_SESSION,
        queue_at=queue_at,
        called_at=timezone.now() - 12 * MIN,
        started_at=timezone.now() - 10 * MIN,
        outcome="ready",
    )
    raw_student(centre, c, "PCM-02")
    nxt = complete_session(s, actor=lead, on_behalf_of=c)
    assert nxt == "PCM-02"
    s.refresh_from_db()
    assert s.status == StudentStatus.DONE and s.ended_at is not None
    rec = SessionRecord.objects.get(student=s)
    assert (rec.counsellor, rec.centre, rec.outcome) == (c, centre, "ready")
    assert (rec.queue_at, rec.called_at, rec.started_at, rec.ended_at) == (
        s.queue_at,
        s.called_at,
        s.started_at,
        s.ended_at,
    )
    msg = Message.objects.get(student=s, template="session_done")
    assert msg.body.startswith("Thanks for meeting Meera Iyer. Your shortlist and next steps are on the way.")
    ev = AuditEvent.objects.get(student=s, verb="completed")
    assert ev.actor == lead and ev.on_behalf_of == c


def test_cq49_complete_with_empty_queue_returns_none(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.IN_SESSION, started_at=timezone.now())
    assert complete_session(s) is None


@pytest.mark.parametrize("status", [StudentStatus.CALLED, StudentStatus.WAITING, StudentStatus.DONE])
def test_cq49_cannot_complete_before_start(desk, status):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=status)
    with pytest.raises(InvalidTransition):
        complete_session(s)
    assert not SessionRecord.objects.exists()
