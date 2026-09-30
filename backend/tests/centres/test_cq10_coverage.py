import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre
from apps.counsellors.models import Counsellor, Posting

pytestmark = pytest.mark.django_db


def planned_centre(city="Indore"):
    return Centre.objects.create(
        city=city, venue="V", date=timezone.localdate(), opens_at=dt.time(9), closes_at=dt.time(17)
    )


def test_cq10_detail_lists_covered_and_uncovered_streams(client_as, centre, counsellor, other_counsellor):
    d = client_as("ops_lead").get(f"/api/1/ops/centres/{centre.id}").json()["data"]
    assert d["covered_streams"] == ["PCM", "PCMB", "COM"]
    assert d["uncovered_streams"] == ["PCB", "HUM", "OTH"]


def test_cq10_coverage_counts_off_duty_postings(client_as, centre, counsellor, other_counsellor):
    assert other_counsellor.postings.get().duty == "off_duty"
    d = client_as("ops_lead").get(f"/api/1/ops/centres/{centre.id}").json()["data"]
    assert "COM" in d["covered_streams"]


def test_cq10_list_items_carry_coverage(client_as, centre, counsellor):
    items = client_as("ops_lead").get("/api/1/ops/centres").json()["data"]
    item = next(i for i in items if i["id"] == centre.id)
    assert item["covered_streams"] == ["PCM", "PCMB", "COM"]  # + the roster fixture's second counsellor
    assert item["uncovered_streams"] == ["PCB", "HUM", "OTH"]


def test_cq10_centre_with_no_postings_has_everything_uncovered(client_as):
    c = planned_centre()
    d = client_as("ops_lead").get(f"/api/1/ops/centres/{c.id}").json()["data"]
    assert d["covered_streams"] == [] and len(d["uncovered_streams"]) == 6


def test_cq10_go_live_with_uncovered_streams_needs_confirmation(client_as):
    c = planned_centre()
    who = Counsellor.objects.create(name="M", mobile="9000000001", streams=["PCM", "PCB", "PCMB"])
    Posting.objects.create(counsellor=who, centre=c, desk_label="Desk 1")
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{c.id}/go-live", {}, format="json")
    assert resp.status_code == 409
    j = resp.json()
    assert j["code"] == "needs_confirmation"
    assert j["message"] == "No counsellor covers Commerce, Humanities / Arts, Other. Go live anyway?"
    assert j["data"]["uncovered_streams"] == ["COM", "HUM", "OTH"]
    c.refresh_from_db()
    assert c.status == "planned"


def test_cq10_go_live_proceeds_with_confirm(client_as):
    c = planned_centre()
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{c.id}/go-live", {"confirm": True}, format="json")
    assert resp.status_code == 200
    c.refresh_from_db()
    assert c.status == "live"


def test_cq10_fully_covered_centre_goes_live_without_confirm(client_as):
    c = planned_centre()
    who = Counsellor.objects.create(
        name="All", mobile="9000000001", streams=["PCM", "PCB", "PCMB", "COM", "HUM", "OTH"]
    )
    Posting.objects.create(counsellor=who, centre=c, desk_label="Desk 1")
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{c.id}/go-live", {}, format="json")
    assert resp.status_code == 200


def test_cq10_centre_list_query_count_is_fixed(client_as, centre, django_assert_max_num_queries):
    client = client_as("ops_lead")
    for i in range(6):
        c = planned_centre(f"City{i}")
        who = Counsellor.objects.create(name=f"C{i}", mobile=f"90000000{i:02d}", streams=["PCM"])
        Posting.objects.create(counsellor=who, centre=c, desk_label="Desk 1")
    with django_assert_max_num_queries(5):
        resp = client.get("/api/1/ops/centres")
    assert resp.json()["count"] == 7 and resp.json()["total"] == 7
