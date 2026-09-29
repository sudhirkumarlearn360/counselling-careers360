"""Counsellor desk API: queue, calling, session, edits, notes, ops-as-counsellor (CQ-5, 37…50)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.models import AuditEvent, Student
from tests.queue.helpers import live_centre, raw_student

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)
D = "/api/1/desk"


@pytest.fixture
def desk(centre, counsellor, other_counsellor):
    return centre, counsellor, other_counsellor


def test_cq38_queue_shows_figures_order_next_source_and_consent_flags(client_as, desk):
    centre, meera, _ = desk
    now = timezone.now()
    raw_student(centre, meera, "PCM-02", name="Second", queue_at=now - 5 * MIN)
    raw_student(
        centre, meera, "PCM-01", name="First", queue_at=now - 50 * MIN, source="desk", consent="pending"
    )
    d = client_as("counsellor").get(f"{D}/queue").json()["data"]
    assert [r["token"] for r in d["queue"]] == ["PCM-01", "PCM-02"]
    first = d["queue"][0]
    assert first["next"] is True and first["source"] == "desk" and first["consent_pending"] is True
    assert first["late"] is True and d["queue"][1]["next"] is False
    assert (
        d["figures"]["in_queue"] == 2
        and d["figures"]["late"] == 1
        and d["figures"]["target_session_min"] == 15
    )
    assert d["figures"]["avg_session_min"] is None and d["duty"] == "on_desk" and d["desk"] == "Desk 1"
    assert d["centre"]["venue"] == "Hotel Landmark" and d["next_token"] == "PCM-01"


def test_cq38_no_live_centre_is_a_message_not_an_error(client_as, users, counsellor):
    from apps.counsellors.models import Posting

    Posting.objects.filter(counsellor=counsellor).update(centre=live_centre("Indore", status="planned"))
    d = client_as("counsellor").get(f"{D}/queue").json()["data"]
    assert d["centre"] is None and d["message"] == "You're not posted to a live centre today."


def test_cq39_call_next_moves_to_the_live_session_and_blocks_a_second_call(client_as, desk):
    centre, meera, _ = desk
    raw_student(centre, meera, "PCM-01")
    raw_student(centre, meera, "PCM-02")
    c = client_as("counsellor")
    r = c.post(f"{D}/call-next")
    assert r.status_code == 200 and r.json()["data"]["called"] == "PCM-01"
    assert r.json()["data"]["current"]["token"] == "PCM-01" and r.json()["data"]["next_token"] is None
    again = c.post(f"{D}/call-next")
    assert (
        again.status_code == 409
        and again.json()["message"] == "Finish PCM-01 before calling the next student."
    )


def test_cq39_empty_queue_message(client_as, desk):
    r = client_as("counsellor").post(f"{D}/call-next")
    assert r.status_code == 400 and r.json()["message"].startswith("Your queue is clear")


def test_cq40_call_token_tolerates_case_and_warns_about_the_stream(client_as, desk):
    centre, meera, rahul = desk
    raw_student(centre, rahul, "COM-01", stream="COM")
    c = client_as("counsellor")
    assert c.post(f"{D}/call-token", {"token": ""}, format="json").status_code == 400
    assert c.post(f"{D}/call-token", {"token": "PCM-22"}, format="json").json()["message"] == (
        "No token PCM-22 at this centre today."
    )
    r = c.post(f"{D}/call-token", {"token": " com-01 "}, format="json")
    assert r.status_code == 200
    assert r.json()["data"]["warnings"][0]["message"] == "Meera Iyer doesn't cover Commerce."


def test_cq42_consent_gate_then_verbal_consent_unblocks_start(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01", consent="pending")
    c = client_as("counsellor")
    c.post(f"{D}/call-next")
    blocked = c.post(f"{D}/students/{s.id}/start")
    assert blocked.status_code == 400 and blocked.json()["message"].startswith("Consent is pending")
    assert c.post(f"{D}/students/{s.id}/consent-request").status_code == 200
    assert Message.objects.filter(student=s, template="consent_request").exists()
    ok = c.post(f"{D}/students/{s.id}/consent").json()["data"]
    assert ok["current"]["consent"] == "given" and ok["current"]["consent_by"] == "Meera Iyer"
    started = c.post(f"{D}/students/{s.id}/start").json()["data"]
    assert started["current"]["status"] == "in_session" and started["current"]["timer"]["target_min"] == 15


def test_cq43_44_intake_and_edits_keep_token_and_desk_when_the_stream_changes(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01", course="B.Tech", clarity="Very clear", exams=["JEE"])
    c = client_as("counsellor")
    d = c.get(f"{D}/students/{s.id}").json()["data"]
    assert d["course"] == "B.Tech" and d["exams"] == ["JEE"] and d["clarity"] == "Very clear"
    r = c.patch(
        f"{D}/students/{s.id}",
        {"stream": "COM", "home_city": "Gwalior", "budget": "4-8 L", "mobile": "+91 98110 22009"},
        format="json",
    )
    assert r.status_code == 200 and r.json()["message"] == "Saved."
    s.refresh_from_db()
    assert (s.token, s.counsellor_id, s.stream, s.mobile) == ("PCM-01", meera.id, "COM", "9811022009")
    assert AuditEvent.objects.filter(student=s, verb="edited").exists()


def test_cq44_edit_validation_names_the_field(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01")
    c = client_as("counsellor")
    r = c.patch(f"{D}/students/{s.id}", {"name": "", "mobile": "12", "parent_mobile": "9"}, format="json")
    f = r.json()["data"]["fields"]
    assert r.status_code == 400 and f["name"] == "Name is required."
    assert f["mobile"] == "A 10-digit mobile number is needed for the turn alert."
    assert f["parent_mobile"] == "Parent's number should be 10 digits."


def test_cq48_outcome_and_follow_up_rules(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01")
    c = client_as("counsellor")
    yesterday = (timezone.localdate() - dt.timedelta(days=1)).isoformat()
    bad = c.patch(f"{D}/students/{s.id}", {"follow_up_on": yesterday, "outcome": "maybe"}, format="json")
    f = bad.json()["data"]["fields"]
    assert f["follow_up_on"] == "Pick a follow-up date from today onwards." and f["outcome"]
    tomorrow = (timezone.localdate() + dt.timedelta(days=1)).isoformat()
    ok = c.patch(
        f"{D}/students/{s.id}",
        {"follow_up_on": tomorrow, "outcome": "ready", "colleges_discussed": "IIT Bhopal"},
        format="json",
    )
    assert ok.status_code == 200 and ok.json()["data"]["outcome"] == "ready"
    cleared = c.patch(f"{D}/students/{s.id}", {"outcome": None}, format="json")
    assert cleared.json()["data"]["outcome"] is None  # unset is a real value


def test_cq45_notes_time_ordered_with_author_empty_rejected_and_never_deleted(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01")
    c = client_as("counsellor")
    empty = c.post(f"{D}/students/{s.id}/notes", {"text": "   "}, format="json")
    assert empty.status_code == 400 and empty.json()["message"] == "Write something before adding a note."
    c.post(f"{D}/students/{s.id}/notes", {"text": "Wants govt college."}, format="json")
    r = c.post(f"{D}/students/{s.id}/notes", {"text": "Budget 8L."}, format="json")
    notes = r.json()["data"]["notes"]
    assert [n["text"] for n in notes] == ["Wants govt college.", "Budget 8L."]
    assert notes[0]["author"] == "Meera Iyer" and notes[0]["at"]
    assert c.delete(f"{D}/students/{s.id}/notes").status_code == 405


def test_cq46_47_49_missed_then_complete_names_the_next_token(client_as, desk):
    centre, meera, _ = desk
    a = raw_student(centre, meera, "PCM-01")
    raw_student(centre, meera, "PCM-02")
    c = client_as("counsellor")
    c.post(f"{D}/call-next")
    missed = c.post(f"{D}/students/{a.id}/missed").json()["data"]
    assert missed["current"] is None
    assert Student.objects.get(pk=a.pk).status == "waiting" and Student.objects.get(pk=a.pk).recalls == 1
    r = c.post(f"{D}/call-next").json()["data"]
    assert r["called"] == "PCM-02"
    b = Student.objects.get(token="PCM-02")
    c.post(f"{D}/students/{b.id}/start")
    done = c.post(f"{D}/students/{b.id}/complete").json()["data"]
    assert done["message"] == "Done. Next up: PCM-01." and done["next_token_after"] == "PCM-01"


def test_cq49_cannot_complete_before_start(client_as, desk):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01", status="called")
    assert client_as("counsellor").post(f"{D}/students/{s.id}/complete").status_code == 400


def test_cq41_pull_forward_and_top_student_has_no_control(client_as, desk):
    centre, meera, _ = desk
    now = timezone.now()
    top = raw_student(centre, meera, "PCM-01", queue_at=now - 9 * MIN)
    late = raw_student(centre, meera, "PCM-02", queue_at=now - 1 * MIN)
    c = client_as("counsellor")
    assert c.post(f"{D}/students/{top.id}/pull-forward").status_code == 400
    r = c.post(f"{D}/students/{late.id}/pull-forward")
    assert [q["token"] for q in r.json()["data"]["queue"]] == ["PCM-02", "PCM-01"]


def test_cq50_a_counsellor_cannot_open_another_counsellors_student(client_as, desk):
    centre, meera, rahul = desk
    theirs = raw_student(centre, rahul, "COM-01")
    c = client_as("counsellor")
    assert c.get(f"{D}/students/{theirs.id}").status_code == 404
    assert c.post(f"{D}/students/{theirs.id}/notes", {"text": "x"}, format="json").status_code == 404
    mine = raw_student(centre, meera, "PCM-01")
    rows = c.get(f"{D}/my-students").json()["data"]
    assert [r["token"] for r in rows] == ["PCM-01"] and rows[0]["id"] == mine.id
    centres = c.get(f"{D}/my-centres").json()["data"]
    assert centres[0]["live"] is True and centres[0]["desk"] == "Desk 1" and centres[0]["my_students"] == 1
    assert centres[0]["students"] == 2 and centres[0]["counsellors_on_site"] == 1


def test_cq5_ops_lead_works_a_desk_notes_are_authored_as_the_counsellor(client_as, desk, users):
    centre, meera, _ = desk
    s = raw_student(centre, meera, "PCM-01")
    lead = client_as("ops_lead")
    assert lead.get(f"{D}/queue").status_code == 400  # must choose a desk
    r = lead.post(f"{D}/students/{s.id}/notes?as_counsellor={meera.id}", {"text": "Lead note"}, format="json")
    assert r.status_code == 201 and r.json()["data"]["notes"][0]["author"] == "Meera Iyer"
    ev = AuditEvent.objects.get(student=s, verb="noted")
    assert ev.actor == users["ops_lead"] and ev.on_behalf_of == meera
    called = lead.post(f"{D}/call-next?as_counsellor={meera.id}")
    assert called.status_code == 200 and called.json()["data"]["current"]["token"] == "PCM-01"
    assert AuditEvent.objects.get(student=s, verb="called").on_behalf_of == meera


def test_cq5_a_counsellor_cannot_open_anothers_desk_and_reception_is_blocked(client_as, desk):
    _, meera, rahul = desk
    assert client_as("counsellor").get(f"{D}/queue?as_counsellor={rahul.id}").status_code == 403
    assert client_as("reception").get(f"{D}/queue").status_code == 403
    assert client_as("anonymous").get(f"{D}/queue").status_code == 401


def test_cq20_editing_a_mobile_cannot_create_a_second_open_token_for_the_same_number(client_as, desk):
    centre, meera, _ = desk
    raw_student(centre, meera, "PCM-01", mobile="9811022001")
    other = raw_student(centre, meera, "PCM-02", mobile="9811022002")
    r = client_as("counsellor").patch(
        f"{D}/students/{other.id}", {"mobile": "+91 98110 22001"}, format="json"
    )
    assert r.status_code == 409
    assert r.json()["message"] == "A token is already open for this number — PCM-01."
    other.refresh_from_db()
    assert other.mobile == "9811022002"
    # an unchanged mobile, or one whose token is finished, is fine
    ok = client_as("counsellor").patch(
        f"{D}/students/{other.id}", {"mobile": "9811022002", "budget": "4-8 L"}, format="json"
    )
    assert ok.status_code == 200
    raw_student(centre, meera, "PCM-03", mobile="9811022003", status="done")
    free = client_as("counsellor").patch(f"{D}/students/{other.id}", {"mobile": "9811022003"}, format="json")
    assert free.status_code == 200
