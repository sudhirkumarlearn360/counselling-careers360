"""Front-desk API: hall queue, tabs, search, desk check-in, move, requeue, student record (CQ-29…36, 58)."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.models import Student
from apps.queue.services import call_next
from tests.queue.helpers import live_centre, raw_student

pytestmark = pytest.mark.django_db
MIN = dt.timedelta(minutes=1)
H = "/api/1/hall"


@pytest.fixture
def hall(centre, counsellor, other_counsellor):
    """Gwalior is live with Meera (on desk, PCM/PCMB) and Rahul (off duty, COM)."""
    return centre, counsellor, other_counsellor


def queue(client, centre, **params):
    return client.get(f"{H}/centres/{centre.id}/queue", params)


def test_cq31_hall_lists_open_students_earliest_first_with_status_and_flags(client_as, hall):
    centre, meera, _ = hall
    now = timezone.now()
    raw_student(centre, meera, "PCM-02", name="Later", checkin_at=now - 5 * MIN, queue_at=now - 5 * MIN)
    raw_student(
        centre,
        meera,
        "PCM-01",
        name="Earlier",
        checkin_at=now - 40 * MIN,
        queue_at=now - 40 * MIN,
        consent="pending",
        source="desk",
    )
    raw_student(centre, meera, "PCM-09", status="done")  # not in the hall list
    body = queue(client_as("reception"), centre).json()
    rows = body["data"]["rows"]
    assert [r["token"] for r in rows] == ["PCM-01", "PCM-02"]
    first = rows[0]
    assert (
        first["counsellor"]["desk"] == "Desk 1" and first["status"] == "waiting" and first["waited_min"] == 40
    )
    assert first["consent_pending"] is True and first["late"] is True and rows[1]["late"] is False
    assert body["data"]["header"]["late"] == 1 and body["data"]["header"]["waiting"] == 2


def test_cq32_tabs_all_first_then_each_counsellor_in_desk_order_with_counts_and_late(client_as, hall):
    centre, meera, rahul = hall
    now = timezone.now()
    raw_student(centre, meera, "PCM-01", queue_at=now - 45 * MIN)
    raw_student(centre, rahul, "COM-01")  # off-duty desk with a student still gets a tab
    tabs = queue(client_as("reception"), centre).json()["data"]["tabs"]
    assert [t["key"] for t in tabs] == ["all", f"c{meera.id}", f"c{rahul.id}"]
    assert tabs[0]["label"] == "All students" and tabs[0]["count"] == 2 and tabs[0]["late"] == 1
    assert (tabs[1]["count"], tabs[1]["late"]) == (1, 1) and (tabs[2]["count"], tabs[2]["late"]) == (1, 0)


def test_cq32_empty_desk_still_has_a_zero_tab_and_selecting_a_tab_filters(client_as, hall):
    centre, meera, rahul = hall
    raw_student(centre, meera, "PCM-01")
    body = queue(client_as("reception"), centre, counsellor=rahul.id).json()["data"]
    assert [t["count"] for t in body["tabs"]] == [1, 1, 0] and body["rows"] == []
    body = queue(client_as("reception"), centre, counsellor=meera.id).json()["data"]
    assert [r["token"] for r in body["rows"]] == ["PCM-01"]


def test_cq33_a_missed_student_is_measured_from_the_rejoin(client_as, hall):
    centre, meera, _ = hall
    old = timezone.now() - 90 * MIN
    s = raw_student(centre, meera, "PCM-01", status="called", checkin_at=old, queue_at=old, called_at=old)
    from apps.queue.services import mark_missed

    mark_missed(s)
    row = queue(client_as("reception"), centre).json()["data"]["rows"][0]
    assert row["late"] is False and row["waited_min"] == 0


def test_cq34_search_finds_any_status_by_name_token_or_last_four_and_overrides_the_tab(client_as, hall):
    centre, meera, rahul = hall
    raw_student(centre, meera, "PCM-01", name="Priya Nair", mobile="9811022001", status="done")
    raw_student(centre, rahul, "COM-02", name="Sahil Yadav", mobile="9000010003")
    c = client_as("reception")
    for q, expected in (
        ("Priya", ["PCM-01"]),
        ("pcm-01", ["PCM-01"]),
        ("2001", ["PCM-01"]),
        ("0003", ["COM-02"]),
    ):
        body = queue(c, centre, q=q, counsellor=rahul.id).json()
        assert [r["token"] for r in body["data"]["rows"]] == expected and body["count"] == len(expected)
    assert queue(c, centre, q="zzzz").json()["count"] == 0


def test_cq58_a_failed_turn_alert_is_flagged_in_the_hall_queue(client_as, hall, settings):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-01", mobile="9811099999")
    settings.MESSAGING_STUB_FAIL_TO = ["9811099999"]
    call_next(meera, centre=centre)
    row = queue(client_as("reception"), centre).json()["data"]["rows"][0]
    assert row["alert_failed"] is True and "turn alert" in row["alert_failed_message"]
    assert Student.objects.get(pk=s.pk).status == "called"  # delivery failure never changes status
    settings.MESSAGING_STUB_FAIL_TO = []
    mid = Message.objects.get(student=s, template="turn_called").id
    r = client_as("reception").post(f"{H}/students/{s.id}/messages/{mid}/resend")
    assert r.status_code == 200
    assert queue(client_as("reception"), centre).json()["data"]["rows"][0]["alert_failed"] is False


def test_hall_is_scoped_to_the_receptionists_centre_and_closed_to_counsellors(client_as, hall):
    centre, _, _ = hall
    other = live_centre("Indore")
    assert queue(client_as("reception"), other).status_code == 404
    assert queue(client_as("ops_lead"), other).status_code == 200
    assert queue(client_as("counsellor"), centre).status_code == 403
    assert queue(client_as("anonymous"), centre).status_code == 401


def desk_form(**kw):
    body = {"name": "Walk In", "mobile": "98 110 33002", "stream": "PCM", "help": ["College selection"]}
    body.update(kw)
    return body


def test_cq29_desk_check_in_needs_only_name_mobile_and_help_and_records_source(client_as, hall):
    centre, meera, _ = hall
    r = client_as("reception").post(f"{H}/centres/{centre.id}/check-in", desk_form(), format="json")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["message"] == "Token PCM-01 issued to Meera Iyer, Desk 1."
    assert body["data"]["source"] == "desk" and body["data"]["consent"] == "pending"
    assert body["data"]["mobile"] == "9811033002"
    msg = Message.objects.get(template="token_confirm_desk")
    assert "Reply YES to confirm it's you" in msg.body


def test_cq29_desk_reports_all_failing_fields_together(client_as, hall):
    centre, _, _ = hall
    r = client_as("reception").post(
        f"{H}/centres/{centre.id}/check-in", {"name": "", "mobile": "1", "parent_mobile": "5"}, format="json"
    )
    assert r.status_code == 400
    assert set(r.json()["data"]["fields"]) >= {"name", "mobile", "parent_mobile", "help", "stream"}


def test_cq30_duplicate_names_the_open_token_and_issues_nothing(client_as, hall):
    centre, _, _ = hall
    c = client_as("reception")
    c.post(f"{H}/centres/{centre.id}/check-in", desk_form(), format="json")
    r = c.post(f"{H}/centres/{centre.id}/check-in", desk_form(), format="json")
    assert r.status_code == 409 and r.json()["message"] == "A token is already open for this number — PCM-01."
    assert Student.objects.count() == 1 and r.json()["data"]["student_id"]


def test_cq29_desk_pick_for_an_uncovered_stream_needs_confirmation(client_as, hall):
    centre, meera, rahul = hall
    from apps.counsellors.models import Duty, Posting

    Posting.objects.filter(counsellor=rahul).update(duty=Duty.ON_DESK)
    c = client_as("reception")
    body = desk_form(counsellor_id=rahul.id)
    r = c.post(f"{H}/centres/{centre.id}/check-in", body, format="json")
    assert r.status_code == 409 and r.json()["code"] == "needs_confirmation"
    assert r.json()["message"] == "Rahul Sen doesn't cover Science – PCM. Move anyway?"
    ok = c.post(f"{H}/centres/{centre.id}/check-in", {**body, "confirm": True}, format="json")
    assert ok.status_code == 201 and ok.json()["data"]["counsellor"]["name"] == "Rahul Sen"


def test_cq35_move_warns_then_moves_and_keeps_the_token(client_as, hall):
    centre, meera, rahul = hall
    s = raw_student(centre, meera, "PCM-02")
    c = client_as("reception")
    warn = c.post(f"{H}/students/{s.id}/move", {"counsellor_id": rahul.id}, format="json")
    assert warn.status_code == 409 and warn.json()["code"] == "needs_confirmation"
    ok = c.post(f"{H}/students/{s.id}/move", {"counsellor_id": rahul.id, "confirm": True}, format="json")
    assert ok.status_code == 200 and ok.json()["data"]["token"] == "PCM-02"
    assert ok.json()["data"]["counsellor"]["name"] == "Rahul Sen"
    assert Message.objects.filter(student=s, template="desk_changed").exists()


def test_cq36_requeue_a_no_show_records_who_and_when(client_as, hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-01", status="no_show", recalls=2)
    r = client_as("reception").post(f"{H}/students/{s.id}/requeue")
    assert r.status_code == 200 and r.json()["data"]["status"] == "waiting"
    ev = [e for e in r.json()["data"]["audit"] if e["verb"] == "requeued"][0]
    assert ev["actor"] == "Front Desk" and ev["at"] and ev["data"]["from"] == "no_show"
    assert client_as("reception").post(f"{H}/students/{s.id}/requeue").status_code == 400  # already waiting


def test_student_record_has_audit_trail_and_messages(client_as, hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-01")
    call_next(meera, centre=centre)
    d = client_as("reception").get(f"{H}/students/{s.id}").json()["data"]
    assert [e["verb"] for e in d["audit"]] == ["called"] and d["messages"][0]["template"] == "turn_called"


def test_hall_check_in_with_an_unknown_or_bad_counsellor_id_is_a_clear_400_not_a_500(client_as, hall):
    centre, _, _ = hall
    c = client_as("reception")
    for bad in (99999, "abc", -1):
        r = c.post(f"{H}/centres/{centre.id}/check-in", desk_form(counsellor_id=bad), format="json")
        assert r.status_code == 400, (bad, r.content)
        assert r.json()["data"]["fields"]["counsellor_id"] == "Pick a counsellor."


def test_hall_move_with_an_unknown_or_bad_counsellor_id_is_a_clear_400(client_as, hall):
    centre, meera, _ = hall
    s = raw_student(centre, meera, "PCM-02")
    for bad in (99999, "abc", None):
        r = client_as("reception").post(f"{H}/students/{s.id}/move", {"counsellor_id": bad}, format="json")
        assert r.status_code == 400 and r.json()["data"]["fields"]["counsellor_id"] == "Pick a counsellor."


def test_cq29_a_manual_pick_must_be_on_desk(client_as, hall):
    centre, meera, rahul = hall  # Rahul is off duty
    r = client_as("reception").post(
        f"{H}/centres/{centre.id}/check-in", desk_form(stream="COM", counsellor_id=rahul.id), format="json"
    )
    assert r.status_code == 400 and r.json()["code"] == "counsellor_not_on_desk"
    assert r.json()["message"] == "Rahul Sen isn't on desk right now."
    assert not Student.objects.exists()
