import pytest

pytestmark = pytest.mark.django_db

NAV = {
    "reception": ["Hall queue", "Add a student", "Hall board"],
    "counsellor": ["My queue", "Live session", "My students", "My centres"],
    "ops_lead": [
        "Live centres",
        "Centres & dates",
        "Counsellors",
        "All students",
        "Insights",
        "Hall queue",
        "Hall board",
    ],
}
DEFAULT = {"reception": "hall_queue", "counsellor": "my_queue", "ops_lead": "live_centres"}


@pytest.mark.parametrize("role", ["reception", "counsellor", "ops_lead"])
def test_cq3_nav_and_default_view_come_from_role(client_as, role):
    data = client_as(role).get("/api/1/auth/me").json()["data"]
    assert [i["label"] for i in data["nav"]] == NAV[role]
    assert data["nav"], "no role has an empty navigation"
    assert data["default_view"] == DEFAULT[role]
    assert data["default_view"] == data["nav"][0]["key"]


def test_cq3_ops_nav_has_no_desk_item(client_as):
    data = client_as("ops_lead").get("/api/1/auth/me").json()["data"]
    assert not any("desk" in i["key"] for i in data["nav"])  # CQ-5: never a permanent item


def test_cq1_reception_lands_on_their_centre(client_as, centre):
    data = client_as("reception").get("/api/1/auth/me").json()["data"]
    assert data["default_view"] == "hall_queue"
    assert data["centre"]["id"] == centre.id
    assert data["posting"] is None


def test_cq1_counsellor_context_is_todays_live_posting(client_as, centre):
    data = client_as("counsellor").get("/api/1/auth/me").json()["data"]
    assert data["centre"]["id"] == centre.id
    assert data["posting"]["desk_label"] == "Desk 1"
    assert data["posting"]["duty"] == "on_desk"


def test_cq1_counsellor_without_live_posting_has_no_context(client_as, centre):
    from apps.centres.models import CentreStatus

    centre.status = CentreStatus.PLANNED
    centre.save()
    data = client_as("counsellor").get("/api/1/auth/me").json()["data"]
    assert data["centre"] is None and data["posting"] is None


def test_cq1_counsellor_posting_ignores_other_dates(client_as, centre):
    import datetime as dt

    centre.date = centre.date + dt.timedelta(days=1)
    centre.save()
    assert client_as("counsellor").get("/api/1/auth/me").json()["data"]["posting"] is None


def test_cq1_ops_lead_has_no_centre_or_desk(client_as):
    data = client_as("ops_lead").get("/api/1/auth/me").json()["data"]
    assert data["centre"] is None and data["posting"] is None and data["counsellor"] is None


def test_cq1_me_requires_sign_in(client_as):
    resp = client_as("anonymous").get("/api/1/auth/me")
    assert resp.status_code == 401
    assert set(resp.json()) == {"code", "message", "data"}


def test_cq3_wrong_role_is_403_with_clear_code(client_as):
    resp = client_as("counsellor").get("/api/1/ops/live")
    assert resp.status_code == 403
    assert resp.json()["code"] == "role_not_allowed"
