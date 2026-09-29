import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.queue.models import Student, StudentStatus

pytestmark = pytest.mark.django_db
URL = "/api/1/ops/centres"


_seq = iter(range(1, 10_000))


def body(**over):
    data = {
        "email": f"desk{next(_seq)}@careers360.com",
        "password": "frontdesk-1",
        "city": "Indore",
        "venue": "Hotel Fortune",
        "date": (timezone.localdate() + dt.timedelta(days=3)).isoformat(),
        "opens_at": "10:00",
        "closes_at": "18:00",
        "expected_students": 120,
    }
    data.update(over)
    return data


def post(client_as, **over):
    return client_as("ops_lead").post(URL, body(**over), format="json")


def test_cq6_creates_centre_with_all_fields_as_planned(client_as):
    resp = post(client_as)
    assert resp.status_code == 201, resp.content
    d = resp.json()["data"]
    assert (d["city"], d["venue"], d["opens_at"], d["closes_at"], d["expected_students"]) == (
        "Indore",
        "Hotel Fortune",
        "10:00",
        "18:00",
        120,
    )
    assert d["status"] == "planned"
    assert d["slug"]
    c = Centre.objects.get(pk=d["id"])
    assert c.settings and c.token_sequence.last_number == 0


@pytest.mark.parametrize("missing", ["city", "venue"])
def test_cq6_city_and_venue_are_required(client_as, missing):
    resp = post(client_as, **{missing: "  "})
    assert resp.status_code == 400
    assert resp.json()["message"] == "City and venue are both needed."


def test_cq6_closing_must_be_after_opening(client_as):
    for opens, closes in (("18:00", "10:00"), ("10:00", "10:00")):
        resp = post(client_as, opens_at=opens, closes_at=closes)
        assert resp.status_code == 400
        assert resp.json()["message"] == "Closing time must be later than opening time."


def test_cq6_date_times_and_expected_count_are_captured(client_as):
    for field in ("date", "opens_at", "closes_at", "expected_students"):
        data = body()
        del data[field]
        resp = client_as("ops_lead").post(URL, data, format="json")
        assert resp.status_code == 400, field
    assert not Centre.objects.filter(city="Indore").exists()


def test_cq6_planned_centre_accepts_no_checkins_status_is_planned(client_as):
    d = post(client_as).json()["data"]
    assert Centre.objects.get(pk=d["id"]).status == CentreStatus.PLANNED
    assert not Student.objects.filter(status=StudentStatus.WAITING).exists()


def test_cq6_duplicate_city_and_date_is_allowed_with_warning(client_as):
    first = post(client_as)
    assert first.json()["warnings"] == []
    second = post(client_as, venue="Another hall")
    assert second.status_code == 201
    date = body()["date"]
    msgs = [w["message"] for w in second.json()["warnings"]]
    assert msgs == [f"A centre in Indore on {date} already exists — you can still save."]
    assert Centre.objects.filter(city="Indore").count() == 2
    assert len({c.slug for c in Centre.objects.filter(city="Indore")}) == 2


def test_add_a_centre_creates_the_front_desk_login(client_as):
    from apps.accounts.models import Role, StaffUser

    resp = post(client_as, email="  Indore.Desk@Careers360.com ", password="frontdesk-1")
    assert resp.status_code == 201, resp.content
    d = resp.json()["data"]
    assert d["front_desk_email"] == "indore.desk@careers360.com" and "password" not in str(d)
    user = StaffUser.objects.get(email="indore.desk@careers360.com")
    assert user.role == Role.RECEPTION and user.centre_id == d["id"] and user.check_password("frontdesk-1")
    login = client_as("anonymous").post(
        "/api/1/auth/login", {"email": "indore.desk@careers360.com", "password": "frontdesk-1"}, format="json"
    )
    assert login.status_code == 200 and login.json()["data"]["user"]["centre"]["id"] == d["id"]


def test_add_a_centre_needs_a_valid_email_and_a_password(client_as, users):
    cases = [
        ({"email": "", "password": "frontdesk-1"}, "email", "Enter the front desk's email address."),
        ({"email": "nope", "password": "frontdesk-1"}, "email", "Enter the front desk's email address."),
        ({"email": "a@b.co", "password": "short"}, "password", "The password must be at least 8 characters."),
        (
            {"email": "desk@careers360.com", "password": "frontdesk-1"},
            "email",
            "That email already has an account.",
        ),
    ]
    for over, field, message in cases:
        resp = post(client_as, **over)
        assert resp.status_code == 400, (over, resp.content)
        assert (
            resp.json()["data"]["fields"][field] == [message]
            or resp.json()["data"]["fields"][field] == message
        )
    assert Centre.objects.count() == 0 or Centre.objects.filter(city="Indore").count() == 0


def test_editing_a_centre_can_reset_the_front_desk_password(client_as):
    created = post(client_as, email="indore.desk@careers360.com").json()["data"]
    r = client_as("ops_lead").patch(f"{URL}/{created['id']}", {"password": "new-password-1"}, format="json")
    assert r.status_code == 200, r.content
    ok = client_as("anonymous").post(
        "/api/1/auth/login",
        {"email": "indore.desk@careers360.com", "password": "new-password-1"},
        format="json",
    )
    assert ok.status_code == 200
