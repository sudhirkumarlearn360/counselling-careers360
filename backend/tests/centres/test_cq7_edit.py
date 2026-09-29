import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.queue.models import Student, StudentStatus

pytestmark = pytest.mark.django_db


def url(c):
    return f"/api/1/ops/centres/{c.id}"


def make(status):
    return Centre.objects.create(
        city="Jaipur",
        venue="Old venue",
        date=timezone.localdate() + dt.timedelta(days=5),
        opens_at=dt.time(9),
        closes_at=dt.time(17),
        expected_students=50,
        status=status,
    )


@pytest.mark.parametrize("status", [CentreStatus.PLANNED, CentreStatus.LIVE])
def test_cq7_all_fields_editable_on_planned_and_live(client_as, status):
    c = make(status)
    new_date = (timezone.localdate() + dt.timedelta(days=9)).isoformat()
    resp = client_as("ops_lead").patch(
        url(c),
        {
            "city": "Kota",
            "venue": "New venue",
            "date": new_date,
            "opens_at": "08:30",
            "closes_at": "16:00",
            "expected_students": 75,
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    c.refresh_from_db()
    assert (c.city, c.venue, c.date.isoformat(), c.expected_students) == ("Kota", "New venue", new_date, 75)
    assert (c.opens_at, c.closes_at) == (dt.time(8, 30), dt.time(16))
    assert c.status == status


def test_cq7_closed_centre_cannot_be_edited(client_as):
    c = make(CentreStatus.CLOSED)
    resp = client_as("ops_lead").patch(url(c), {"venue": "X"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "centre_closed"


def test_cq7_edit_keeps_the_same_validation(client_as):
    c = make(CentreStatus.PLANNED)
    r = client_as("ops_lead").patch(url(c), {"venue": ""}, format="json")
    assert r.json()["message"] == "City and venue are both needed."
    r = client_as("ops_lead").patch(url(c), {"closes_at": "08:00"}, format="json")
    assert r.json()["message"] == "Closing time must be later than opening time."


def test_cq7_editing_live_centre_leaves_tokens_queue_and_postings(client_as, centre, counsellor):
    now = timezone.now()
    s = Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token="PCM-01",
        name="Asha Rao",
        school="DPS",
        mobile="9811022999",
        course="Eng",
        status=StudentStatus.WAITING,
        checkin_at=now,
        queue_at=now,
        priority=3,
        help=["Other"],
    )
    centre.token_sequence.last_number = 4
    centre.token_sequence.save()
    slug, postings = centre.slug, list(centre.postings.values_list("id", "desk_label", "duty"))
    resp = client_as("ops_lead").patch(
        url(centre), {"venue": "Moved venue", "city": "Gwalior Fort"}, format="json"
    )
    assert resp.status_code == 200
    centre.refresh_from_db()
    s.refresh_from_db()
    assert centre.slug == slug and resp.json()["data"]["slug"] == slug
    assert centre.token_sequence.last_number == 4
    assert (s.token, s.status, s.queue_at, s.priority, s.counsellor_id) == (
        "PCM-01",
        StudentStatus.WAITING,
        now,
        3,
        counsellor.id,
    )
    assert list(centre.postings.values_list("id", "desk_label", "duty")) == postings


def test_cq7_edit_into_duplicate_city_date_warns(client_as, centre):
    other = make(CentreStatus.PLANNED)
    resp = client_as("ops_lead").patch(
        url(other), {"city": "Gwalior", "date": centre.date.isoformat()}, format="json"
    )
    assert resp.status_code == 200
    assert "already exists" in resp.json()["warnings"][0]["message"]


def test_cq7_unknown_centre_is_404(client_as):
    assert client_as("ops_lead").patch("/api/1/ops/centres/999999", {}, format="json").status_code == 404
