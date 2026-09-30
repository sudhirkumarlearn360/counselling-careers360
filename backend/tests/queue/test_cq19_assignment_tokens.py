"""CQ-19: assignment rule and STREAM-NN token numbering (queue-engine: Assignment, Token numbering)."""

import pytest

from apps.counsellors.models import Duty
from apps.messaging.models import Message
from apps.queue.exceptions import CentreNotLive, NoCounsellorForStream, NoCounsellorOnDuty
from apps.queue.models import AuditEvent, Student, StudentStatus, TokenSequence
from apps.queue.services import (
    assign_counsellor,
    call_next,
    check_in,
    close_centre,
    mark_missed,
    next_token,
    release,
)
from tests.queue.helpers import data, live_centre, ops_lead, post, raw_student, session_record

pytestmark = pytest.mark.django_db


# --- Assignment ---------------------------------------------------------------------------------


def test_cq19_assigns_an_on_desk_counsellor_covering_the_stream():
    centre = live_centre()
    post(centre, "Off Duty", ["PCM"], "Desk 1", duty=Duty.OFF_DUTY)
    post(centre, "On Break", ["PCM"], "Desk 2", duty=Duty.ON_BREAK)
    post(centre, "Commerce", ["COM"], "Desk 3")
    pcm = post(centre, "Science", ["PCM", "PCB"], "Desk 4")
    assert assign_counsellor(centre, "PCM") == pcm


def test_cq19_lowest_load_wins_and_active_student_counts_as_load():
    centre = live_centre()
    a = post(centre, "A", ["PCM"], "Desk 1")
    b = post(centre, "B", ["PCM"], "Desk 2")
    raw_student(centre, a.counsellor, "PCM-01")
    raw_student(centre, b.counsellor, "PCM-02", status=StudentStatus.IN_SESSION)
    raw_student(centre, b.counsellor, "PCM-03")
    assert assign_counsellor(centre, "PCM") == a  # A load 1, B load 2 (1 waiting + in session)


def test_cq19_equal_load_prefers_faster_average_session():
    centre = live_centre()
    post(centre, "Slow", ["PCM"], "Desk 1", expected=10)
    fast = post(centre, "Fast", ["PCM"], "Desk 2", expected=20)
    done = raw_student(centre, fast.counsellor, "PCM-01", status=StudentStatus.DONE)
    session_record(done, minutes=5)  # actual avg 5 min beats slow's expected 10
    assert assign_counsellor(centre, "PCM") == fast


def test_cq19_equal_load_and_avg_falls_back_to_desk_label():
    centre = live_centre()
    post(centre, "Zed", ["PCM"], "Desk 10")
    two = post(centre, "Amy", ["PCM"], "Desk 2")
    assert assign_counsellor(centre, "PCM") == two  # natural order: Desk 2 before Desk 10


def test_cq19_strict_stream_routing_raises_no_counsellor_for_stream():
    centre = live_centre()
    post(centre, "Commerce", ["COM"], "Desk 1")
    post(centre, "Science off duty", ["PCM"], "Desk 2", duty=Duty.OFF_DUTY)
    with pytest.raises(NoCounsellorForStream) as err:
        assign_counsellor(centre, "PCM")
    assert err.value.message == ("No counsellor for your stream is on desk yet — please see the front desk.")


def test_cq19_nobody_on_desk_raises_no_counsellor_on_duty():
    centre = live_centre()
    post(centre, "Break", ["PCM"], "Desk 1", duty=Duty.ON_BREAK)
    with pytest.raises(NoCounsellorOnDuty) as err:
        assign_counsellor(centre, "PCM")
    assert err.value.message == "No counsellor is on desk yet — please see the front desk."


def test_cq19_assignment_reads_postings_at_this_centre_only():
    here, there = live_centre("Gwalior"), live_centre("Indore")
    elsewhere = post(there, "Elsewhere", ["PCM"], "Desk 1")
    local = post(here, "Local", ["COM"], "Desk 1")
    # The PCM counsellor on desk at another centre is never a candidate here.
    with pytest.raises(NoCounsellorForStream):
        assign_counsellor(here, "PCM")
    assert assign_counsellor(there, "PCM") == elsewhere and assign_counsellor(here, "COM") == local


def test_cq19_check_in_does_not_fall_back_to_an_uncovered_counsellor():
    centre = live_centre()
    post(centre, "Commerce", ["COM"], "Desk 1")
    with pytest.raises(NoCounsellorForStream):
        check_in(centre, data(stream="HUM"), "self")
    assert not Student.objects.exists()
    assert TokenSequence.objects.get(centre=centre).last_number == 0  # no number burnt


# --- Check-in -----------------------------------------------------------------------------------


def test_cq19_check_in_issues_token_with_counsellor_and_confirmation():
    centre = live_centre()
    p = post(centre, "Meera Iyer", ["PCM"], "Desk 1")
    s = check_in(centre, data(mobile="+91 98110 22001", stream="PCM"), "self")
    assert s.token == "PCM-01" and s.counsellor == p.counsellor and s.status == StudentStatus.WAITING
    assert s.mobile == "9811022001" and s.source == "self"
    assert s.consent == "given" and s.consent_at is not None and s.consent_by is None
    assert s.queue_at == s.checkin_at
    msg = Message.objects.get(student=s)
    assert (
        msg.template == "token_confirm_self" and "Token PCM-01, counsellor Meera Iyer at Desk 1." in msg.body
    )
    ev = AuditEvent.objects.get(student=s, verb="checked_in")
    assert ev.actor is None and ev.data["token"] == "PCM-01"


def test_cq29_desk_check_in_is_consent_pending_with_desk_confirmation_and_actor():
    centre = live_centre()
    post(centre, "Meera Iyer", ["PCM"], "Desk 1")
    lead = ops_lead()
    s = check_in(centre, data(), "desk", actor=lead)
    assert s.source == "desk" and s.consent == "pending" and s.consent_at is None
    assert Message.objects.get(student=s).template == "token_confirm_desk"
    assert AuditEvent.objects.get(student=s, verb="checked_in").actor == lead


def test_cq29_desk_check_in_can_pick_a_counsellor_manually_with_stream_confirmation():
    from apps.common.exceptions import NeedsConfirmation

    centre = live_centre()
    post(centre, "Science", ["PCM"], "Desk 1")
    com = post(centre, "Ravi Commerce", ["COM"], "Desk 2")
    with pytest.raises(NeedsConfirmation) as err:
        check_in(centre, data(stream="PCM", counsellor_id=com.counsellor_id), "desk")
    assert err.value.message == "Ravi Commerce doesn't cover Science – PCM. Move anyway?"
    s = check_in(centre, data(stream="PCM", counsellor_id=com.counsellor_id), "desk", confirm=True)
    assert s.counsellor == com.counsellor


def test_cq12_check_in_refused_when_centre_is_not_live():
    centre = live_centre(status="planned")
    post(centre, "Meera", ["PCM"], "Desk 1")
    with pytest.raises(CentreNotLive) as err:
        check_in(centre, data(), "self")
    assert err.value.message.startswith("This centre isn't open for check-in — it runs on ")
    close = live_centre("Indore")
    post(close, "Meera", ["PCM"], "Desk 1")
    close_centre(close)
    with pytest.raises(CentreNotLive) as err:
        check_in(close, data(), "self")
    assert err.value.message == "Check-in closed at 18:00. Please see the front desk."


# --- Token numbering ----------------------------------------------------------------------------


def test_cq19_next_token_is_stream_prefixed_and_shared_across_streams():
    centre = live_centre()
    assert next_token(centre, "PCM") == "PCM-01"
    assert next_token(centre, "COM") == "COM-02"
    assert next_token(centre, "PCM") == "PCM-03"


def test_cq19_token_number_grows_past_99():
    centre = live_centre()
    TokenSequence.objects.filter(centre=centre).update(last_number=99)
    assert next_token(centre, "PCM") == "PCM-100"


def test_cq19_numbers_never_repeat_after_release_no_show_and_close():
    centre = live_centre()
    p = post(centre, "Meera", ["PCM"], "Desk 1")
    a = check_in(centre, data(mobile="9000000001"), "self")
    release(a)
    b = check_in(centre, data(mobile="9000000001"), "self")  # same number, released -> new token
    call_next(p.counsellor, centre=centre)
    mark_missed(b)
    call_next(p.counsellor, centre=centre)
    mark_missed(b)  # no-show
    c = check_in(centre, data(mobile="9000000001"), "self")
    close_centre(centre)
    tokens = [a.token, b.token, c.token]
    assert tokens == ["PCM-01", "PCM-02", "PCM-03"]
    assert TokenSequence.objects.get(centre=centre).last_number == 3
    assert Student.objects.filter(centre=centre).count() == 3
