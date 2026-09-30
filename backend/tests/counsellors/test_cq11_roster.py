import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre
from apps.counsellors.models import Counsellor, Posting

pytestmark = pytest.mark.django_db
URL = "/api/1/ops/counsellors"


def make_centre(city, days=0, **kw):
    return Centre.objects.create(
        city=city,
        venue="V",
        date=timezone.localdate() + dt.timedelta(days=days),
        opens_at=dt.time(9),
        closes_at=dt.time(17),
        **kw,
    )


def test_cq11_list_shows_each_counsellors_postings(client_as, centre, counsellor, other_counsellor):
    later = make_centre("Jaipur", days=4)
    Posting.objects.create(counsellor=counsellor, centre=later, desk_label="Desk 3")
    resp = client_as("ops_lead").get(URL)
    assert resp.status_code == 200
    j = resp.json()
    assert (j["count"], j["total"]) == (2, 2)
    meera = next(c for c in j["data"] if c["id"] == counsellor.id)
    assert [(p["city"], p["date"], p["desk_label"], p["centre_id"]) for p in meera["postings"]] == [
        ("Gwalior", centre.date.isoformat(), "Desk 1", centre.id),
        ("Jaipur", later.date.isoformat(), "Desk 3", later.id),
    ]


def test_cq11_second_posting_same_date_allowed_with_warning_naming_other_city(client_as, centre, counsellor):
    other = make_centre("Indore")
    resp = client_as("ops_lead").post(
        f"{URL}/{counsellor.id}/postings", {"centre_id": other.id, "desk_label": "Desk 1"}, format="json"
    )
    assert resp.status_code == 201
    w = resp.json()["warnings"]
    assert [x["message"] for x in w] == [
        f"Meera Iyer is already posted to Gwalior on {centre.date.isoformat()}."
    ]
    assert Posting.objects.filter(counsellor=counsellor).count() == 2


def test_cq11_no_warning_on_a_different_date(client_as, counsellor):
    other = make_centre("Indore", days=2)
    resp = client_as("ops_lead").post(
        f"{URL}/{counsellor.id}/postings", {"centre_id": other.id, "desk_label": "Desk 1"}, format="json"
    )
    assert resp.status_code == 201
    assert resp.json()["warnings"] == []


def test_cq11_moving_a_posting_onto_a_busy_date_warns(client_as, centre, counsellor):
    free = make_centre("Kota", days=3)
    p = Posting.objects.create(counsellor=counsellor, centre=free, desk_label="Desk 1")
    busy = make_centre("Indore")
    resp = client_as("ops_lead").patch(f"/api/1/ops/postings/{p.id}", {"centre_id": busy.id}, format="json")
    assert resp.status_code == 200, resp.content
    msgs = [w["message"] for w in resp.json()["warnings"]]
    assert msgs == [f"Meera Iyer is already posted to Gwalior on {centre.date.isoformat()}."]
    p.refresh_from_db()
    assert p.centre == busy


def test_cq11_creating_counsellor_with_posting_on_busy_date_warns(client_as, centre, counsellor):
    """Same person can't be created twice, so the warning path for create is via postings only;
    a brand-new counsellor never conflicts."""
    other = make_centre("Indore")
    resp = client_as("ops_lead").post(
        URL,
        {
            "name": "New One",
            "mobile": "9811099999",
            "streams": ["PCM"],
            "centre_id": other.id,
            "desk_label": "D",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert resp.json()["warnings"] == []


def test_cq11_postings_list_for_counsellor(client_as, counsellor):
    j = client_as("ops_lead").get(f"{URL}/{counsellor.id}/postings").json()
    assert (j["count"], j["total"]) == (1, 1)
    assert j["data"][0]["desk_label"] == "Desk 1"


def test_cq11_list_query_count_is_fixed(client_as, centre, django_assert_max_num_queries):
    client = client_as("ops_lead")
    for i in range(6):
        c = Counsellor.objects.create(name=f"N{i}", mobile=f"90000000{i:02d}", streams=["PCM"])
        Posting.objects.create(counsellor=c, centre=make_centre(f"City{i}", days=i + 1), desk_label="D")
    with django_assert_max_num_queries(5):
        resp = client.get(URL)
    assert resp.json()["count"] == 8
