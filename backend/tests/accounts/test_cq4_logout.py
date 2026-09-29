import pytest
from rest_framework.test import APIClient

from apps.queue.models import Student  # noqa: F401  (logout must not touch student state)

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


def test_cq4_logout_requires_sign_in(users):
    tokens = sign_in()
    assert (
        APIClient().post("/api/1/auth/logout", {"refresh": tokens["refresh"]}, format="json").status_code
        == 401
    )


def test_cq4_cannot_blacklist_someone_elses_token(users):
    mine = sign_in()
    theirs = sign_in("desk@careers360.com")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {mine['access']}")
    assert client.post("/api/1/auth/logout", {"refresh": theirs["refresh"]}, format="json").status_code == 400
    assert (
        APIClient().post("/api/1/auth/refresh", {"refresh": theirs["refresh"]}, format="json").status_code
        == 200
    )


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
