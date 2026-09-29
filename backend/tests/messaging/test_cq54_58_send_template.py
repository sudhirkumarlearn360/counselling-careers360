"""send_template, templates and the StubProvider (counselqueue-messaging; CQ-54..58)."""

import pytest
from django.test import override_settings

from apps.messaging import services as messaging
from apps.messaging.models import Message
from apps.messaging.providers.base import SendResult
from apps.messaging.providers.stub import StubProvider
from apps.messaging.templates import TEMPLATES, render
from apps.queue.models import AuditEvent, StudentStatus
from tests.queue.helpers import raw_student

pytestmark = pytest.mark.django_db

VARS = {
    "city": "Gwalior",
    "token": "PCM-07",
    "counsellor": "Meera Iyer",
    "desk": "Desk 1",
    "link": "http://localhost:5173/t/abc",
    "code": "4821",
    "minutes": 10,
    "recalls": 2,
    "close_time": "18:00",
}

EXPECTED = {
    "otp_code": "Your Careers360 check-in code is 4821. It expires in 10 minutes.",
    "token_confirm_self": (
        "Careers360 Gwalior: you're in the queue. Token PCM-07, counsellor Meera Iyer at Desk 1. "
        "We'll message you when it's your turn. Track live: http://localhost:5173/t/abc"
    ),
    "token_confirm_desk": (
        "Careers360 Gwalior: our front desk has checked you in. Token PCM-07, counsellor Meera Iyer at "
        "Desk 1. Reply YES to confirm it's you and allow us to use these details for counselling. "
        "We'll message you when it's your turn. Track live: http://localhost:5173/t/abc"
    ),
    "consent_request": (
        "Careers360: please confirm it's you and allow us to use your details for counselling — "
        "reply YES or open http://localhost:5173/t/abc"
    ),
    "turn_called": ("It's your turn. Please go to Desk 1 — Meera Iyer. Your place is held for two calls."),
    "missed_first": (
        "We called PCM-07 and missed you. You're back in the queue — next call is the last one."
    ),
    "missed_final": "We called PCM-07 2 times. Visit the front desk to get back in the queue.",
    "desk_changed": "You've been moved to Meera Iyer, Desk 1. Token PCM-07 stays the same.",
    "released": "Token PCM-07 is released. You can check in again before 18:00.",
    "session_done": (
        "Thanks for meeting Meera Iyer. Your shortlist and next steps are on the way. "
        "Rate this session 1–5: http://localhost:5173/t/abc"
    ),
}


def test_cq54_all_ten_template_keys_exist_and_match_message_choices():
    assert set(TEMPLATES) == set(EXPECTED) == set(Message.Template.values)


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_cq54_template_bodies_are_verbatim(key):
    assert render(key, **VARS) == EXPECTED[key]


def test_cq55_turn_called_adds_consent_ask_when_pending():
    body = render("turn_called", consent_pending=True, **VARS)
    assert body == (
        "It's your turn. Please go to Desk 1 — Meera Iyer. Your place is held for two calls. "
        "Reply YES to confirm you're here and consent to your details being used for counselling."
    )


def test_cq58_stub_provider_sends_and_fails_for_listed_numbers():
    assert StubProvider().send("9811022001", "hi").status == "sent"
    with override_settings(MESSAGING_STUB_FAIL_TO=["9811022001"]):
        result = StubProvider().send("9811022001", "hi")
    assert isinstance(result, SendResult) and result.status == "failed"


def test_cq54_send_template_creates_a_sent_message_with_the_live_link(centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01")
    msg = messaging.send_template(s, "token_confirm_self")
    assert msg.pk and msg.status == Message.Status.SENT and msg.provider_id
    assert msg.to == s.mobile and msg.student == s and msg.template == "token_confirm_self"
    assert msg.body == (
        "Careers360 Gwalior: you're in the queue. Token PCM-01, counsellor Meera Iyer at Desk 1. "
        f"We'll message you when it's your turn. Track live: http://localhost:5173/t/{s.access_key}"
    )


@override_settings(FRONTEND_BASE_URL="https://q.careers360.com/")
def test_cq26_link_uses_frontend_base_url(centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01")
    msg = messaging.send_template(s, "consent_request")
    assert msg.body.endswith(f"open https://q.careers360.com/t/{s.access_key}")


def test_cq58_stub_failure_records_failed_message_and_audit(centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01")
    with override_settings(MESSAGING_STUB_FAIL_TO=[s.mobile]):
        msg = messaging.send_template(s, "turn_called")
    assert msg.status == Message.Status.FAILED
    assert AuditEvent.objects.filter(student=s, verb="message_failed").exists()


class Boom:
    def send(self, to, body):
        raise RuntimeError("provider down")


@override_settings(MESSAGING_PROVIDER="tests.messaging.test_cq54_58_send_template.Boom")
def test_cq58_provider_exception_becomes_a_failed_message(centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01")
    msg = messaging.send_template(s, "turn_called")
    assert msg.status == Message.Status.FAILED and "provider down" in msg.failure_reason


def test_cq58_whatsapp_disabled_records_failed_disabled_without_calling_provider(centre, counsellor):
    centre.settings.whatsapp_enabled = False
    centre.settings.save()
    s = raw_student(centre, counsellor, "PCM-01")
    with override_settings(MESSAGING_PROVIDER="tests.messaging.test_cq54_58_send_template.Boom"):
        msg = messaging.send_template(s, "turn_called")
    assert msg.status == Message.Status.FAILED and msg.failure_reason == "disabled"
    assert msg.provider_id == ""


def test_cq58_messaging_never_changes_student_status(centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01", status=StudentStatus.CALLED, priority=3)
    before = (s.status, s.queue_at, s.priority, s.counsellor_id)
    with override_settings(MESSAGING_STUB_FAIL_TO=[s.mobile]):
        for key in EXPECTED:
            if key != "otp_code":
                messaging.send_template(s, key)
    s.refresh_from_db()
    assert (s.status, s.queue_at, s.priority, s.counsellor_id) == before
