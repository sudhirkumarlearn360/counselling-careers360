"""Public student API: landing, OTP, check-in, token page, release, consent, rating, board (CQ-12…28)."""

import datetime as dt

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.centres.models import CentreStatus
from apps.messaging.models import Message, OtpCode
from apps.queue.models import AuditEvent, Student, StudentStatus
from apps.queue.services import call_next, complete_session, start_session
from tests.queue.helpers import data, live_centre, post, raw_student

pytestmark = pytest.mark.django_db
API = "/api/1/public"


@pytest.fixture
def hall():
    centre = live_centre()
    meera = post(centre, "Meera Iyer", ["PCM", "PCMB"], "Desk 1")
    return centre, meera.counsellor


def verified(client, centre, mobile):
    # A second code for the same mobile is refused inside the resend wait, so age any earlier one.
    OtpCode.objects.filter(mobile=mobile).update(created_at=timezone.now() - dt.timedelta(minutes=2))
    assert (
        client.post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": mobile}, format="json").status_code
        == 200
    )
    r = client.post(
        f"{API}/centres/{centre.slug}/otp/verify", {"mobile": mobile, "code": "1234"}, format="json"
    )
    assert r.status_code == 200, r.content
    return r.json()["data"]["verification_id"]


def form(mobile, vid, **kw):
    body = data(mobile=mobile)
    body.update({"consent": True, "verification_id": vid})
    body.update(kw)
    return body


def check_in_via_api(client, centre, mobile="9811022001", **kw):
    vid = verified(client, centre, mobile)
    return client.post(f"{API}/centres/{centre.slug}/check-in", form(mobile, vid, **kw), format="json")


# --- CQ-12 / CQ-13 / CQ-14 landing -------------------------------------------------------------


def test_cq12_landing_names_the_centre_and_needs_no_login(hall):
    centre, _ = hall
    r = APIClient().get(f"{API}/centres/{centre.slug}")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["open"] is True and d["centre"]["city"] == "Gwalior" and d["centre"]["venue"] == "Hotel Landmark"
    assert d["centre"]["opens_at"] == "10:00" and d["centre"]["closes_at"] == "18:00"
    assert len(d["steps"]) == 3 and "All optional" in d["bring_note"]


def test_cq12_stale_staff_token_does_not_break_the_student_page(hall):
    centre, _ = hall
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert c.get(f"{API}/centres/{centre.slug}").status_code == 200


def test_cq12_planned_and_closed_centres_say_so():
    planned = live_centre(status=CentreStatus.PLANNED, date=timezone.localdate() + dt.timedelta(days=2))
    d = APIClient().get(f"{API}/centres/{planned.slug}").json()["data"]
    assert d["open"] is False and d["message"].startswith("This centre isn't open for check-in — it runs on")
    closed = live_centre("Indore", status=CentreStatus.CLOSED)
    d = APIClient().get(f"{API}/centres/{closed.slug}").json()["data"]
    assert d["message"] == "Check-in closed at 18:00. Please see the front desk."


def test_cq12_unknown_slug_is_404():
    assert APIClient().get(f"{API}/centres/nowhere-2026-01-01").status_code == 404


def test_cq13_hall_stats_dash_before_any_call_then_a_number(hall):
    centre, c = hall
    stats = APIClient().get(f"{API}/centres/{centre.slug}").json()["data"]["stats"]
    assert (
        stats["avg_wait_min"] is None and stats["avg_wait_label"] == "—" and stats["counsellors_on_site"] == 1
    )
    raw_student(centre, c, "PCM-01", queue_at=timezone.now() - dt.timedelta(minutes=10))
    call_next(c, centre=centre)
    stats = APIClient().get(f"{API}/centres/{centre.slug}").json()["data"]["stats"]
    assert stats["avg_wait_min"] == 10 and stats["waiting"] == 0


# --- CQ-18 OTP ------------------------------------------------------------------------------------


def test_cq18_otp_is_sent_to_whatsapp_and_stored_hashed(hall):
    centre, _ = hall
    c = APIClient()
    r = c.post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "+91 98110 22001"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["resend_after_sec"] == 30
    msg = Message.objects.get(template="otp_code")
    assert msg.to == "9811022001" and "1234" in msg.body and msg.student is None
    assert "1234" not in OtpCode.objects.get().code_hash


def test_cq18_bad_mobile_uses_the_exact_message(hall):
    centre, _ = hall
    r = APIClient().post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "12345"}, format="json")
    assert (
        r.status_code == 400
        and r.json()["message"] == "A 10-digit mobile number is needed for the turn alert."
    )


def test_cq18_otp_needs_a_live_centre():
    planned = live_centre(status=CentreStatus.PLANNED)
    r = APIClient().post(f"{API}/centres/{planned.slug}/otp/send", {"mobile": "9811022001"}, format="json")
    assert r.status_code == 400 and r.json()["code"] == "centre_not_live"


def test_cq18_wrong_code_then_retry_then_success(hall):
    centre, _ = hall
    c = APIClient()
    c.post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "9811022001"}, format="json")
    r = c.post(
        f"{API}/centres/{centre.slug}/otp/verify", {"mobile": "9811022001", "code": "0000"}, format="json"
    )
    assert r.status_code == 400 and r.json()["message"] == "That code doesn't match — check your WhatsApp"
    assert r.json()["data"]["attempts_left"] == 4
    ok = c.post(
        f"{API}/centres/{centre.slug}/otp/verify", {"mobile": "9811022001", "code": "1234"}, format="json"
    )
    assert ok.status_code == 200 and ok.json()["data"]["verification_id"]


@override_settings(OTP_MAX_ATTEMPTS=2)
def test_cq18_too_many_wrong_codes_invalidate_the_code(hall):
    centre, _ = hall
    c = APIClient()
    c.post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "9811022001"}, format="json")
    for _ in range(2):
        c.post(
            f"{API}/centres/{centre.slug}/otp/verify", {"mobile": "9811022001", "code": "0000"}, format="json"
        )
    r = c.post(
        f"{API}/centres/{centre.slug}/otp/verify", {"mobile": "9811022001", "code": "1234"}, format="json"
    )
    assert r.status_code == 400 and r.json()["code"] == "otp_expired"


def test_cq18_expired_code(hall):
    centre, _ = hall
    c = APIClient()
    c.post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "9811022001"}, format="json")
    OtpCode.objects.update(expires_at=timezone.now() - dt.timedelta(seconds=1))
    r = c.post(
        f"{API}/centres/{centre.slug}/otp/verify", {"mobile": "9811022001", "code": "1234"}, format="json"
    )
    assert r.json()["code"] == "otp_expired"


def test_cq18_resend_is_allowed_only_after_the_wait(hall):
    centre, _ = hall
    c = APIClient()
    url = f"{API}/centres/{centre.slug}/otp/send"
    assert c.post(url, {"mobile": "9811022001"}, format="json").status_code == 200
    r = c.post(url, {"mobile": "9811022001"}, format="json")
    assert (
        r.status_code == 429 and r.json()["code"] == "otp_resend_wait" and r.json()["data"]["retry_after"] > 0
    )
    OtpCode.objects.update(created_at=timezone.now() - dt.timedelta(seconds=31))
    assert c.post(url, {"mobile": "9811022001"}, format="json").status_code == 200
    assert OtpCode.objects.filter(invalidated_at__isnull=False).count() == 1  # the older code is superseded


# --- CQ-15…20 check-in ----------------------------------------------------------------------------


def test_cq19_check_in_issues_a_token_with_counsellor_desk_and_whatsapp(hall):
    centre, meera = hall
    r = check_in_via_api(APIClient(), centre)
    assert r.status_code == 201, r.content
    t = r.json()["data"]["token"]
    assert t["token"] == "PCM-01" and t["counsellor"] == "Meera Iyer" and t["desk"] == "Desk 1"
    assert t["venue"] == "Hotel Landmark" and t["name"] == "Asha Rao" and t["mobile"] == "9811022001"
    assert t["state"]["kind"] == "next" and t["consent"] == "given"
    s = Student.objects.get()
    assert s.access_key == r.json()["data"]["access_key"]
    assert Message.objects.filter(student=s, template="token_confirm_self").exists()
    assert AuditEvent.objects.filter(student=s, verb="checked_in", actor__isnull=True).exists()


def test_cq15_all_failing_fields_are_reported_together_and_nothing_is_issued(hall):
    centre, _ = hall
    c = APIClient()
    vid = verified(c, centre, "9811022001")
    body = {
        "name": "Al",
        "school": "",
        "mobile": "12",
        "parent_mobile": "99",
        "email": "nope",
        "stream": "ZZZ",
        "course": "",
        "help": [],
        "consent": False,
        "verification_id": vid,
    }
    r = c.post(f"{API}/centres/{centre.slug}/check-in", body, format="json")
    assert r.status_code == 400
    fields = r.json()["data"]["fields"]
    assert fields["name"] == "Enter your name (at least 3 letters)."
    assert fields["school"] == "Enter your school."
    assert fields["mobile"] == "A 10-digit mobile number is needed for the turn alert."
    assert fields["parent_mobile"] == "Parent's number should be 10 digits."
    assert fields["email"] == "That email doesn't look right."
    assert fields["stream"] and fields["course"] and fields["help"] and fields["consent"]
    assert not Student.objects.exists()


def test_cq17_consent_line_must_be_ticked(hall):
    centre, _ = hall
    r = check_in_via_api(APIClient(), centre, consent=False)
    assert r.status_code == 400
    assert r.json()["data"]["fields"]["consent"] == "Tick the consent line so a counsellor can advise you"


def test_cq18_token_is_not_issued_without_verification(hall):
    centre, _ = hall
    body = data(mobile="9811022001")
    body["consent"] = True
    r = APIClient().post(f"{API}/centres/{centre.slug}/check-in", body, format="json")
    assert r.status_code == 400 and r.json()["code"] == "verification_required"
    assert r.json()["message"] == "Verify your number first."


def test_cq18_verification_is_bound_to_the_verified_mobile(hall):
    centre, _ = hall
    c = APIClient()
    vid = verified(c, centre, "9811022001")
    r = c.post(f"{API}/centres/{centre.slug}/check-in", form("9999999999", vid), format="json")
    assert r.status_code == 400 and r.json()["code"] == "verification_required"
    assert not Student.objects.exists()


def test_cq18_verification_is_single_use_but_survives_a_failed_form(hall):
    centre, _ = hall
    c = APIClient()
    vid = verified(c, centre, "9811022001")
    bad = c.post(f"{API}/centres/{centre.slug}/check-in", form("9811022001", vid, name="Al"), format="json")
    assert bad.status_code == 400
    good = c.post(f"{API}/centres/{centre.slug}/check-in", form("9811022001", vid), format="json")
    assert good.status_code == 201
    student = Student.objects.get()
    student.status = StudentStatus.DONE  # a returning student may check in again, but not reuse the id
    student.save()
    again = c.post(f"{API}/centres/{centre.slug}/check-in", form("9811022001", vid), format="json")
    assert again.status_code == 400 and again.json()["code"] == "verification_required"


def test_cq20_duplicate_blocks_and_names_the_open_token_after_verification(hall):
    centre, _ = hall
    c = APIClient()
    first = check_in_via_api(c, centre).json()["data"]
    second = check_in_via_api(c, centre)
    assert second.status_code == 409
    body = second.json()
    assert body["message"] == "A token is already open for this number — PCM-01."
    assert body["data"]["access_key"] == first["access_key"]
    assert Student.objects.count() == 1


def test_cq20_a_finished_student_may_check_in_again_with_a_new_number(hall):
    centre, meera = hall
    c = APIClient()
    check_in_via_api(c, centre)
    s = call_next(meera, centre=centre).student
    start_session(s)
    complete_session(s)
    r = check_in_via_api(c, centre)
    assert r.status_code == 201 and r.json()["data"]["token"]["token"] == "PCM-02"


def test_cq12_check_in_refused_at_planned_and_closed_centres():
    for status in (CentreStatus.PLANNED, CentreStatus.CLOSED):
        centre = live_centre(city=f"C-{status}", status=status)
        r = APIClient().post(f"{API}/centres/{centre.slug}/otp/send", {"mobile": "9811022001"}, format="json")
        assert r.status_code == 400 and r.json()["code"] == "centre_not_live"


def test_cq19_no_counsellor_for_the_stream_is_a_clear_error(hall):
    centre, _ = hall
    r = check_in_via_api(APIClient(), centre, stream="COM")
    assert r.status_code == 400
    assert r.json()["message"] == "No counsellor for your stream is on desk yet — please see the front desk."


@override_settings(
    REST_FRAMEWORK={
        **__import__("django.conf", fromlist=["settings"]).settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            "login": "10/min",
            "logout": "30/min",
            "checkin": "2/min",
            "otp": "20/min",
        },
    }
)
def test_check_in_is_throttled_per_ip(hall):
    centre, _ = hall
    c = APIClient()
    codes = [c.post(f"{API}/centres/{centre.slug}/check-in", {}, format="json").status_code for _ in range(3)]
    assert codes == [400, 400, 429]


# --- CQ-21…28 the token page ------------------------------------------------------------------------


def test_cq21_position_and_estimate_update_and_are_approximate(hall):
    centre, meera = hall
    c = APIClient()
    a = check_in_via_api(c, centre, "9811000001").json()["data"]
    b = check_in_via_api(c, centre, "9811000002").json()["data"]
    assert a["token"]["state"]["kind"] == "next"
    st = c.get(f"{API}/tokens/{b['access_key']}").json()["data"]["state"]
    assert st["kind"] == "waiting" and st["ahead"] == 1 and st["approximate"] is True and st["minutes"] >= 15
    assert len(st["expected_at"]) == 5
    call_next(meera, centre=centre)  # the first student is called
    st = c.get(f"{API}/tokens/{b['access_key']}").json()["data"]["state"]
    assert st["kind"] == "next"


def test_cq23_27_called_in_session_done_and_no_show_states(hall):
    centre, meera = hall
    c = APIClient()
    a = check_in_via_api(c, centre).json()["data"]
    s = call_next(meera, centre=centre).student
    d = c.get(f"{API}/tokens/{a['access_key']}").json()["data"]
    assert (
        d["state"]["kind"] == "called" and d["desk"] == "Desk 1" and "two calls" in d["state"]["recall_hold"]
    )
    start_session(s)
    d = c.get(f"{API}/tokens/{a['access_key']}").json()["data"]
    assert d["state"]["kind"] == "in_session" and d["can_release"] is False
    complete_session(s)
    d = c.get(f"{API}/tokens/{a['access_key']}").json()["data"]
    assert d["state"]["kind"] == "done" and d["can_rate"] is True


def test_cq25_release_leaves_the_queue_and_confirms(hall):
    centre, _ = hall
    c = APIClient()
    a = check_in_via_api(c, centre, "9811000001").json()["data"]
    b = check_in_via_api(c, centre, "9811000002").json()["data"]
    r = c.post(f"{API}/tokens/{a['access_key']}/release")
    assert r.status_code == 200 and r.json()["data"]["status"] == "released"
    assert (
        Message.objects.get(template="released").body
        == "Token PCM-01 is released. You can check in again before 18:00."
    )
    assert c.get(f"{API}/tokens/{b['access_key']}").json()["data"]["state"]["kind"] == "next"
    again = c.post(f"{API}/tokens/{a['access_key']}/release")
    assert again.status_code == 400 and again.json()["code"] == "invalid_transition"


def test_cq24_student_confirms_desk_added_consent_on_their_phone(hall):
    centre, meera = hall
    s = raw_student(centre, meera, "PCM-05", consent="pending", source="desk")
    r = APIClient().post(f"{API}/tokens/{s.access_key}/consent")
    assert r.status_code == 200 and r.json()["data"]["consent"] == "given"
    s.refresh_from_db()
    assert s.consent_by is None and s.consent_at is not None


def test_cq28_rating_once_only_after_the_session(hall):
    centre, meera = hall
    s = raw_student(centre, meera, "PCM-01", status="in_session", started_at=timezone.now())
    c = APIClient()
    early = c.post(f"{API}/tokens/{s.access_key}/rating", {"rating": 5}, format="json")
    assert early.status_code == 400
    complete_session(s)
    assert c.post(f"{API}/tokens/{s.access_key}/rating", {"rating": 6}, format="json").status_code == 400
    ok = c.post(f"{API}/tokens/{s.access_key}/rating", {"rating": 4}, format="json")
    assert (
        ok.status_code == 200 and ok.json()["data"]["rating"] == 4 and ok.json()["data"]["can_rate"] is False
    )
    again = c.post(f"{API}/tokens/{s.access_key}/rating", {"rating": 5}, format="json")
    assert again.status_code == 409 and again.json()["message"] == "You've already rated this session."


def test_cq26_unknown_or_forged_access_keys_are_404(hall):
    assert APIClient().get(f"{API}/tokens/not-a-key").status_code == 404
    assert APIClient().get(f"{API}/tokens/abc.def").status_code == 404


def test_token_payload_never_leaks_other_students(hall):
    centre, meera = hall
    raw_student(centre, meera, "PCM-01", name="Someone Else", mobile="9000000001")
    mine = raw_student(centre, meera, "PCM-02", name="Me Myself", mobile="9000000002")
    body = APIClient().get(f"{API}/tokens/{mine.access_key}").content.decode()
    assert "Someone Else" not in body and "9000000001" not in body


# --- CQ-51…53 board ---------------------------------------------------------------------------------


def test_cq51_53_board_panels_states_and_recently_called(hall):
    centre, meera = hall
    post(centre, "Ravi Shah", ["COM"], "Desk 2", duty="on_break")
    post(centre, "Asha Nair", ["PCM"], "Desk 10", duty="off_duty")
    empty = APIClient().get(f"{API}/board/{centre.slug}").json()["data"]
    assert empty["recently_called"] == [] and empty["recently_called_empty"] == "Nothing called yet."
    assert [p["desk"] for p in empty["panels"]] == ["Desk 1", "Desk 2", "Desk 10"]  # natural desk order
    lines = {p["desk"]: p["line"] for p in empty["panels"]}
    assert lines == {"Desk 1": "queue clear", "Desk 2": "back shortly", "Desk 10": "Closed"}
    assert empty["panels"][0]["serving"] is None
    raw_student(centre, meera, "PCM-01")
    raw_student(centre, meera, "PCM-02")
    call_next(meera, centre=centre)
    board = APIClient().get(f"{API}/board/{centre.slug}").json()["data"]
    p = board["panels"][0]
    assert (p["serving"], p["next"], p["waiting"]) == ("PCM-01", "PCM-02", 1) and p["line"] == ""
    assert board["recently_called"] == ["PCM-01"] and board["total_waiting"] == 1
    assert "keep your phone on" in board["standing_line"]
    assert "Someone" not in str(board)  # tokens only, no names


def test_cq52_board_keeps_only_the_last_six_called(hall):
    centre, meera = hall
    now = timezone.now()
    for i in range(8):
        raw_student(centre, meera, f"PCM-{i + 1:02d}", status="done", called_at=now + dt.timedelta(minutes=i))
    board = APIClient().get(f"{API}/board/{centre.slug}").json()["data"]
    assert board["recently_called"] == [f"PCM-{i:02d}" for i in (8, 7, 6, 5, 4, 3)]
