"""Ops records, CSV export, insights, delivery webhook (CQ-58…61)."""

import csv
import datetime as dt
import hashlib
import hmac
import io
import json

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.messaging.models import Message
from apps.queue.models import AuditEvent, SessionRecord
from tests.queue.helpers import live_centre, post, raw_student

pytestmark = pytest.mark.django_db
OPS = "/api/1/ops"
MIN = dt.timedelta(minutes=1)


@pytest.fixture
def records(centre, counsellor, other_counsellor):
    now = timezone.now()
    other = live_centre("Indore")
    asha = post(other, "Asha Nair", ["COM"], "Desk 1").counsellor
    a = raw_student(
        centre,
        counsellor,
        "PCM-01",
        name="Priya Nair",
        mobile="9811022001",
        status="done",
        called_at=now - 30 * MIN,
        queue_at=now - 40 * MIN,
        started_at=now - 29 * MIN,
        ended_at=now - 14 * MIN,
        outcome="ready",
        rating=5,
        clarity="Very clear",
        help=["College selection", "Cut-offs & college chances"],
        follow_up_on=timezone.localdate(),
    )
    SessionRecord.objects.create(
        student=a,
        counsellor=counsellor,
        centre=centre,
        queue_at=a.queue_at,
        called_at=a.called_at,
        started_at=a.started_at,
        ended_at=a.ended_at,
        outcome="ready",
    )
    raw_student(centre, counsellor, "PCM-02", name="=cmd|' /C calc'!A0", status="no_show", recalls=2)
    raw_student(
        centre,
        other_counsellor,
        "COM-01",
        name="Sahil",
        stream="COM",
        status="done",
        outcome=None,
        called_at=now - 5 * MIN,
        queue_at=now - 25 * MIN,
        started_at=now - 4 * MIN,
        ended_at=now - 1 * MIN,
        help=["Course selection"],
        clarity="Completely confused",
    )
    raw_student(other, asha, "COM-01", name="Indore Kid", stream="COM")
    return centre, other


def test_cq59_all_students_newest_first_with_filters_and_counts(client_as, records):
    centre, other = records
    c = client_as("ops_lead")
    body = c.get(f"{OPS}/students").json()
    assert body["count"] == 4 and body["total"] == 4
    assert {
        "token",
        "name",
        "mobile",
        "school",
        "stream",
        "course",
        "centre",
        "date",
        "counsellor",
        "wait_min",
        "session_min",
        "outcome",
        "status",
    } <= set(body["data"][0])
    f = c.get(f"{OPS}/students", {"stream": "COM", "centre": other.id}).json()
    assert f["count"] == 1 and f["total"] == 4 and f["data"][0]["name"] == "Indore Kid"
    assert c.get(f"{OPS}/students", {"q": "2001"}).json()["count"] == 1
    assert c.get(f"{OPS}/students", {"status": "done", "q": "priya"}).json()["count"] == 1
    assert c.get(f"{OPS}/students", {"q": "nobody"}).json() == {"data": [], "count": 0, "total": 4}


def test_cq59_only_ops_can_see_the_records(client_as, records):
    assert client_as("reception").get(f"{OPS}/students").status_code == 403
    assert client_as("counsellor").get(f"{OPS}/students").status_code == 403


def read_csv(response):
    return list(csv.reader(io.StringIO(response.content.decode())))


def test_cq60_export_reflects_filters_names_the_file_and_is_ops_only(client_as, records, users):
    centre, other = records
    r = client_as("ops_lead").get(f"{OPS}/students/export", {"centre": centre.id, "status": "done"})
    assert r.status_code == 200 and r["Content-Type"].startswith("text/csv")
    assert (
        r["Content-Disposition"]
        == f'attachment; filename="counselqueue_gwalior_{centre.date.isoformat()}.csv"'
    )
    rows = read_csv(r)
    assert rows[0][:4] == ["Token", "Name", "School", "Mobile"] and rows[0][-1] == "Notes"
    assert len(rows[0]) == 23 and len(rows) == 3 and {row[0] for row in rows[1:]} == {"PCM-01", "COM-01"}
    assert client_as("reception").get(f"{OPS}/students/export").status_code == 403
    assert client_as("counsellor").get(f"{OPS}/students/export").status_code == 403
    assert AuditEvent.objects.filter(verb="exported", actor=users["ops_lead"], centre=centre).exists()
    whole = client_as("ops_lead").get(f"{OPS}/students/export")
    assert "counselqueue_all_" in whole["Content-Disposition"] and len(read_csv(whole)) == 5


def test_cq60_export_neutralises_spreadsheet_formulas(client_as, records):
    rows = read_csv(client_as("ops_lead").get(f"{OPS}/students/export", {"q": "PCM-02"}))
    assert rows[1][1].startswith("'=cmd")


def test_cq61_insights_headline_demand_help_outcomes_rating_and_dashes(client_as, records):
    d = client_as("ops_lead").get(f"{OPS}/insights").json()["data"]
    h = d["headline"]
    assert h["counselled_or_queued"] == 3
    assert h["avg_wait"]["n"] == 2 and h["avg_wait"]["promise_min"] == 30
    assert (
        h["avg_session"]["n"] == 1
        and h["avg_session"]["target_min"] == 15
        and "(from 1)" in h["avg_session"]["label"]
    )
    assert h["no_show_rate"]["value"] == round(1 / 3, 3)
    assert [(x["stream"], x["count"]) for x in d["demand"]] == [("COM", 2), ("PCM", 2)]
    assert d["demand"][0]["share"] == 1.0 and d["demand"][0]["name"] == "Commerce"
    counts = {x["option"]: x["count"] for x in d["help"]}
    assert counts["Other"] == 2 and counts["College selection"] == 1 and counts["Course selection"] == 1
    assert d["help"][0]["option"] == "Other"  # ranked by count
    outcomes = {o["label"]: o["count"] for o in d["outcomes"]}
    assert outcomes["Ready to apply"] == 1 and outcomes["Not set"] == 1
    assert d["follow_ups"] == 1 and d["rating"] == {"avg": 5.0, "n": 1, "label": "5.0 (from 1)"}


def test_cq61_thin_data_shows_dashes_never_zero(client_as, centre, counsellor):
    d = client_as("ops_lead").get(f"{OPS}/insights", {"centre": centre.id}).json()["data"]
    assert d["headline"]["avg_wait"]["label"] == "—" and d["headline"]["avg_session"]["label"] == "—"
    assert (
        d["headline"]["no_show_rate"]["label"] == "—"
        and d["rating"]["label"] == "—"
        and d["rating"]["avg"] is None
    )
    assert client_as("ops_lead").get(f"{OPS}/insights", {"centre": 9999}).status_code == 404
    assert client_as("reception").get(f"{OPS}/insights").status_code == 403


def sign(body: bytes, secret="s3cret") -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@override_settings(MESSAGING_WEBHOOK_SECRET="s3cret")
def test_cq58_webhook_marks_failed_and_flags_the_student(client_as, centre, counsellor):
    s = raw_student(centre, counsellor, "PCM-01")
    m = Message.objects.create(
        student=s, template="turn_called", to=s.mobile, body="x", status="sent", provider_id="p-1"
    )
    body = json.dumps({"provider_id": "p-1", "status": "failed"}).encode()
    c = client_as("anonymous")
    bad = c.post(
        "/api/1/webhooks/messaging/status", body, content_type="application/json", HTTP_X_SIGNATURE="nope"
    )
    assert bad.status_code == 403
    ok = c.post(
        "/api/1/webhooks/messaging/status", body, content_type="application/json", HTTP_X_SIGNATURE=sign(body)
    )
    assert ok.status_code == 200
    m.refresh_from_db()
    assert m.status == "failed" and AuditEvent.objects.filter(student=s, verb="message_failed").exists()
    s.refresh_from_db()
    assert s.status == "waiting"  # delivery failure never changes status


def test_webhook_is_disabled_without_a_secret(client_as):
    r = client_as("anonymous").post("/api/1/webhooks/messaging/status", {}, format="json")
    assert r.status_code == 403


def test_cq59_centre_and_venue_filters_combine(client_as, records):
    c = client_as("ops_lead")
    assert c.get(f"{OPS}/students", {"city": "indore"}).json()["count"] == 1
    assert c.get(f"{OPS}/students", {"city": "Gwalior", "venue": "Hotel Landmark"}).json()["count"] == 3
    assert c.get(f"{OPS}/students", {"city": "Gwalior", "venue": "Nowhere"}).json()["count"] == 0
