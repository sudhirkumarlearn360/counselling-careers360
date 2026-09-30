import pytest
from rest_framework.test import APIClient

from apps.queue.models import Student

pytestmark = pytest.mark.django_db


def sign_in(email="meera@careers360.com", password="desk123"):
    return (
        APIClient()
        .post("/api/1/auth/login", {"email": email, "password": password}, format="json")
        .json()["data"]
    )


def test_cq4_logout_blacklists_refresh_token(users):
    tokens = sign_in()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code == 200
    resp = APIClient().post("/api/1/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert resp.status_code == 401
    assert set(resp.json()) == {"code", "message", "data"}


def test_cq4_refresh_issues_new_access_before_logout(users):
    tokens = sign_in()
    resp = APIClient().post("/api/1/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access"] and data["refresh"] and data["refresh"] != tokens["refresh"]


def test_cq4_logout_requires_refresh_token(users):
    tokens = sign_in()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    resp = client.post("/api/1/auth/logout", {}, format="json")
    assert resp.status_code == 400 and resp.json()["code"] == "refresh_required"


def test_cq4_logout_works_with_no_authorization_header(users):
    tokens = sign_in()
    assert (
        APIClient().post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code
        == 200
    )
    assert (
        APIClient().post("/api/1/auth/refresh", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


def test_cq4_logout_works_with_an_expired_access_token(users):
    import datetime as dt

    from rest_framework_simplejwt.tokens import AccessToken

    tokens = sign_in()
    expired = AccessToken.for_user(users["counsellor"])
    expired.set_exp(lifetime=-dt.timedelta(hours=1))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
    assert client.post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code == 200
    assert (
        APIClient().post("/api/1/auth/refresh", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


def test_cq4_invalid_token_still_200_and_same_body_as_valid(users):
    tokens = sign_in()
    good = APIClient().post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json")
    bad = APIClient().post("/api/1/auth/logout", {"refresh": "not.a.token"}, format="json")
    again = APIClient().post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json")
    assert good.status_code == bad.status_code == again.status_code == 200
    assert good.json() == bad.json() == again.json()


def test_cq4_logout_is_throttled(users, settings):
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "logout": "2/min"},
    }
    codes = [
        APIClient().post("/api/1/auth/logout", {"refresh": "x"}, format="json").status_code for _ in range(3)
    ]
    assert codes == [200, 200, 429]


def test_cq4_refresh_for_inactive_user_is_401_not_403(users):
    tokens = sign_in()
    users["counsellor"].is_active = False
    users["counsellor"].save()
    resp = APIClient().post("/api/1/auth/refresh", {"refresh": tokens["refresh"]}, format="json")
    assert resp.status_code == 401 and resp.json()["code"] == "token_not_valid"


def test_cq4_logout_twice_is_harmless(users):
    tokens = sign_in()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    for _ in range(2):
        assert (
            client.post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code
            == 200
        )


def test_cq4_logout_changes_no_student_state(users, centre, counsellor):
    import datetime as dt

    from django.utils import timezone

    from apps.queue.models import StudentStatus

    now = timezone.now()
    s = Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token="PCM-01",
        name="Asha Rao",
        school="DPS",
        mobile="9000000001",
        course="Engineering",
        status=StudentStatus.IN_SESSION,
        checkin_at=now,
        queue_at=now,
        started_at=now - dt.timedelta(minutes=5),
        help=["College selection"],
    )
    before = Student.objects.filter(pk=s.pk).values().get()
    tokens = sign_in()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    client.post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json")
    assert Student.objects.filter(pk=s.pk).values().get() == before
    sign_in()  # signing in again finds the session still in progress
    assert Student.objects.get(pk=s.pk).status == StudentStatus.IN_SESSION
