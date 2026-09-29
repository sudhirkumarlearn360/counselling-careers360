"""Cross-cutting engine rules: messaging never drives status, no deletes, duty never moves students."""

import pathlib
import re

import pytest
from django.test import override_settings

from apps.counsellors.models import Duty, Posting
from apps.counsellors.services import set_duty
from apps.messaging.models import Message
from apps.queue.models import AuditEvent, StudentStatus
from apps.queue.services import call_next, check_in, complete_session, release, start_session
from tests.queue.helpers import data, live_centre, post, raw_student

pytestmark = pytest.mark.django_db
APPS = pathlib.Path(__file__).resolve().parents[2] / "apps"


def test_cq58_stub_failure_does_not_block_any_transition():
    centre = live_centre()
    c = post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor
    mobile = "9811022001"
    with override_settings(MESSAGING_STUB_FAIL_TO=[mobile]):
        s = check_in(centre, data(mobile=mobile), "self")
        s = call_next(c, centre=centre).student
        s = start_session(s)
        assert complete_session(s) is None
    s.refresh_from_db()
    assert s.status == StudentStatus.DONE
    statuses = set(Message.objects.filter(student=s).values_list("status", flat=True))
    assert statuses == {Message.Status.FAILED}
    assert AuditEvent.objects.filter(student=s, verb="message_failed").count() == 3


def test_cq58_whatsapp_disabled_still_runs_transitions():
    centre = live_centre()
    centre.settings.whatsapp_enabled = False
    centre.settings.save()
    post(centre, "Meera Iyer", ["PCM"], "Desk 1")
    s = check_in(centre, data(), "self")
    s = release(s)
    assert s.status == StudentStatus.RELEASED
    msgs = Message.objects.filter(student=s)
    assert msgs.count() == 2 and {m.failure_reason for m in msgs} == {"disabled"}


def test_cq37_duty_change_never_moves_existing_students():
    centre = live_centre()
    p = post(centre, "Meera Iyer", ["PCM"], "Desk 1")
    s = raw_student(centre, p.counsellor, "PCM-01")
    before = (s.counsellor_id, s.queue_at, s.priority, s.status)
    set_duty(Posting.objects.get(pk=p.pk), Duty.OFF_DUTY)
    s.refresh_from_db()
    assert (s.counsellor_id, s.queue_at, s.priority, s.status) == before


def test_no_student_or_audit_deletes_in_engine_or_messaging():
    offenders = []
    for folder in ("queue/services", "messaging"):
        for path in (APPS / folder).rglob("*.py"):
            if "migrations" in path.parts:
                continue
            if re.search(r"\.delete\(", path.read_text()):
                offenders.append(str(path))
    for path in (APPS / "queue").glob("*.py"):
        if re.search(r"\.delete\(", path.read_text()):
            offenders.append(str(path))
    assert offenders == []
