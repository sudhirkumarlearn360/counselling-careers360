import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient

from apps.accounts.models import LoginAttempt

pytestmark = pytest.mark.django_db
URL = "/api/1/auth/login"
BLANK = "Enter your work email and password"
WRONG = "That email and password don't match an account."
HELPDESK = "Three failed attempts — contact the IT helpdesk: 1800 572 9877 · it-support@careers360.com"


def login(email, password):
    return APIClient().post(URL, {"email": email, "password": password}, format="json")


@pytest.mark.parametrize(
    "email,password", [("", "desk123"), ("meera@careers360.com", ""), ("  ", "  "), (None, None)]
)
def test_cq1_blank_email_or_password_shows_exact_message(users, email, password):
    resp = login(email, password)
    assert resp.status_code == 400
    assert resp.json()["message"] == BLANK
    assert resp.json()["code"] == "credentials_required"


def test_cq1_missing_fields_shows_blank_message(users):
    resp = APIClient().post(URL, {}, format="json")
    assert resp.status_code == 400 and resp.json()["message"] == BLANK


def test_cq1_blank_does_not_count_as_a_failed_attempt(users):
    login("", "x")
    assert not LoginAttempt.objects.exists()


@pytest.mark.parametrize(
    "typed", ["MEERA@Careers360.com", "  meera@careers360.com  ", " Meera@CAREERS360.com"]
)
def test_cq1_email_is_case_insensitive_and_trimmed(users, typed):
    resp = login(typed, "desk123")
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["email"] == "meera@careers360.com"


def test_cq1_login_returns_tokens_and_user_envelope(users, centre):
    data = login("meera@careers360.com", "desk123").json()["data"]
    assert data["access"] and data["refresh"]
    user = data["user"]
    assert user["role"] == "counsellor"
    assert user["default_view"] == "my_queue"
    assert user["counsellor"] == users["counsellor"].counsellor_id
    assert user["centre"]["id"] == centre.id
    assert user["posting"]["desk_label"] == "Desk 1"
    assert data["failed_attempts"] == 0


def test_cq1_inactive_user_cannot_sign_in(users):
    users["reception"].is_active = False
    users["reception"].save()
    assert login("desk@careers360.com", "desk123").json()["message"] == WRONG


def test_cq2_inactive_user_response_identical_to_wrong_password(users):
    users["reception"].is_active = False
    users["reception"].save()
    inactive = login("desk@careers360.com", "desk123")
    wrong = login("meera@careers360.com", "nope")
    assert inactive.status_code == wrong.status_code == 400
    assert inactive.json() == wrong.json()


def test_cq2_overlong_email_is_invalid_credentials_and_not_recorded(users):
    resp = login("a" * 250 + "@x.com", "nope")
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_credentials" and resp.json()["message"] == WRONG
    assert not LoginAttempt.objects.exists()


def test_cq2_failure_record_retries_once_on_db_error(users, monkeypatch):
    import apps.accounts.services as svc

    real, calls = svc._bump_failure, []

    def flaky(email):
        calls.append(1)
        if len(calls) == 1:
            raise IntegrityError("race")
        return real(email)

    monkeypatch.setattr(svc, "_bump_failure", flaky)
    body = login("meera@careers360.com", "nope").json()
    assert len(calls) == 2 and body["data"]["failed_attempts"] == 1


def test_cq2_login_is_rate_limited_per_ip_with_standard_envelope(users, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "login": "3/min"},
    }
    statuses = [login("meera@careers360.com", "nope").status_code for _ in range(4)]
    assert statuses == [400, 400, 400, 429]
    body = login("meera@careers360.com", "desk123")
    assert body.status_code == 429
    assert body.json()["code"] == "throttled"
    assert body.json()["message"] == "Too many attempts — try again in a minute."
    assert isinstance(body.json()["data"]["retry_after"], int)


def test_cq2_wrong_password_and_unknown_email_give_identical_response(users):
    a = login("meera@careers360.com", "nope")
    b = login("ghost@careers360.com", "nope")
    assert a.status_code == b.status_code == 400
    assert a.json() == b.json()
    assert a.json()["message"] == WRONG
    assert a.json()["code"] == "invalid_credentials"


def test_cq2_unknown_email_still_runs_a_password_hash_check(users, monkeypatch):
    calls = []
    import apps.accounts.services as svc

    real = svc.check_password
    monkeypatch.setattr(svc, "check_password", lambda *a, **k: calls.append(1) or real(*a, **k))
    login("ghost@careers360.com", "nope")
    assert calls  # same work as for a real account, so timing does not reveal existence


def test_cq2_failed_attempts_counted_and_helpdesk_from_third(users):
    seen = []
    for _ in range(4):
        body = login("meera@careers360.com", "nope").json()
        seen.append((body["data"]["failed_attempts"], body["data"]["show_helpdesk"]))
    assert seen == [(1, False), (2, False), (3, True), (4, True)]


def test_cq2_helpdesk_notice_text_and_no_reset_link(users):
    for _ in range(3):
        body = login("meera@careers360.com", "nope").json()
    assert body["data"]["helpdesk_notice"] == HELPDESK
    # No reset flow in this release: the failure body carries only these keys, none a reset link/token.
    assert set(body["data"]) == {"failed_attempts", "show_helpdesk", "helpdesk_notice"}
    assert set(body) == {"code", "message", "data"}
    assert APIClient().post("/api/1/auth/reset-password", {}, format="json").status_code == 404
    assert APIClient().post("/api/1/auth/password-reset", {}, format="json").status_code == 404


def test_cq2_first_failures_have_no_helpdesk_notice(users):
    body = login("meera@careers360.com", "nope").json()
    assert body["data"]["helpdesk_notice"] is None


def test_cq2_counter_is_per_normalised_email(users):
    login("MEERA@careers360.com", "nope")
    body = login(" meera@careers360.com ", "nope").json()
    assert body["data"]["failed_attempts"] == 2
    assert LoginAttempt.objects.get().email == "meera@careers360.com"


def test_cq2_unknown_email_also_counts_and_shows_helpdesk(users):
    for _ in range(3):
        body = login("ghost@careers360.com", "nope").json()
    assert body["data"]["show_helpdesk"] is True


def test_cq2_counter_resets_on_success(users):
    login("meera@careers360.com", "nope")
    login("meera@careers360.com", "nope")
    ok = login("meera@careers360.com", "desk123")
    assert ok.status_code == 200 and ok.json()["data"]["failed_attempts"] == 0
    assert login("meera@careers360.com", "nope").json()["data"]["failed_attempts"] == 1


def test_cq2_success_after_helpdesk_still_signs_in(users):
    for _ in range(5):
        login("meera@careers360.com", "nope")
    assert login("meera@careers360.com", "desk123").status_code == 200
