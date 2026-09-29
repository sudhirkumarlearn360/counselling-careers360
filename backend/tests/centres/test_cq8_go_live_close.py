import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Posting
from apps.queue.models import AuditEvent, Student, StudentStatus
from apps.queue.services import close_centre

pytestmark = pytest.mark.django_db


@pytest.fixture
def planned(db):
    c = Centre.objects.create(
        city="Indore",
        venue="V",
        date=timezone.localdate(),
        opens_at=dt.time(9),
        closes_at=dt.time(17),
    )
    who = Counsellor.objects.create(
        name="All Streams", mobile="9000000001", streams=["PCM", "PCB", "PCMB", "COM", "HUM", "OTH"]
    )
    Posting.objects.create(counsellor=who, centre=c, desk_label="Desk 1")
    return c


def student(centre, counsellor, token, status, mobile):
    now = timezone.now()
    return Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token=token,
        name="Asha Rao",
        school="DPS",
        mobile=mobile,
        course="Eng",
        status=status,
        checkin_at=now,
        queue_at=now,
        help=["Other"],
    )


def test_cq8_go_live_from_planned_in_one_action(client_as, planned, users):
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{planned.id}/go-live", {}, format="json")
    assert resp.status_code == 200, resp.content
    assert resp.json()["data"]["status"] == "live"
    planned.refresh_from_db()
    assert planned.status == CentreStatus.LIVE
    ev = AuditEvent.objects.get(centre=planned, verb="centre_live")
    assert ev.actor == users["ops_lead"] and ev.student is None


def test_cq8_go_live_only_from_planned(client_as, centre):
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{centre.id}/go-live", {}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "not_planned"


def test_cq8_closed_centre_cannot_go_live_or_reopen(client_as, planned):
    planned.status = CentreStatus.CLOSED
    planned.save()
    resp = client_as("ops_lead").post(
        f"/api/1/ops/centres/{planned.id}/go-live", {"confirm": True}, format="json"
    )
    assert resp.status_code == 400
    planned.refresh_from_db()
    assert planned.status == CentreStatus.CLOSED
    resp = client_as("ops_lead").post(
        f"/api/1/ops/centres/{planned.id}/close", {"confirm": True}, format="json"
    )
    assert resp.status_code == 400


def test_cq8_close_preview_names_waiting_count(client_as, centre, counsellor):
    student(centre, counsellor, "PCM-01", StudentStatus.WAITING, "9811000001")
    student(centre, counsellor, "PCM-02", StudentStatus.WAITING, "9811000002")
    student(centre, counsellor, "PCM-03", StudentStatus.DONE, "9811000003")
    resp = client_as("ops_lead").get(f"/api/1/ops/centres/{centre.id}/close")
    assert resp.status_code == 200
    d = resp.json()["data"]
    assert d["waiting_count"] == 2
    assert d["message"] == "2 students are still waiting. They'll be marked not counselled."
    centre.refresh_from_db()
    assert centre.status == CentreStatus.LIVE  # preview changes nothing
    assert Student.objects.filter(status=StudentStatus.WAITING).count() == 2


def test_cq8_close_needs_confirm(client_as, centre, counsellor):
    student(centre, counsellor, "PCM-01", StudentStatus.WAITING, "9811000001")
    resp = client_as("ops_lead").post(f"/api/1/ops/centres/{centre.id}/close", {}, format="json")
    assert resp.status_code == 409
    assert resp.json()["code"] == "needs_confirmation"
    assert resp.json()["data"]["waiting_count"] == 1
    centre.refresh_from_db()
    assert centre.status == CentreStatus.LIVE


def test_cq8_close_marks_waiting_not_counselled_not_no_show(client_as, centre, counsellor, users):
    w = student(centre, counsellor, "PCM-01", StudentStatus.WAITING, "9811000001")
    called = student(centre, counsellor, "PCM-02", StudentStatus.CALLED, "9811000002")
    done = student(centre, counsellor, "PCM-03", StudentStatus.DONE, "9811000003")
    resp = client_as("ops_lead").post(
        f"/api/1/ops/centres/{centre.id}/close", {"confirm": True}, format="json"
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["data"]["not_counselled"] == 1
    for s in (w, called, done):
        s.refresh_from_db()
    assert (w.status, called.status, done.status) == (
        StudentStatus.NOT_COUNSELLED,
        StudentStatus.CALLED,
        StudentStatus.DONE,
    )
    centre.refresh_from_db()
    assert centre.status == CentreStatus.CLOSED
    ev = AuditEvent.objects.get(centre=centre, verb="centre_closed", student__isnull=True)
    assert ev.actor == users["ops_lead"] and ev.data["not_counselled"] == 1


def test_cq8_close_centre_service_returns_count_and_audits(centre, counsellor, users):
    student(centre, counsellor, "PCM-01", StudentStatus.WAITING, "9811000001")
    student(centre, counsellor, "PCM-02", StudentStatus.WAITING, "9811000002")
    assert close_centre(centre, users["ops_lead"]) == 2
    centre.refresh_from_db()
    assert centre.status == CentreStatus.CLOSED
    assert not Student.objects.filter(status=StudentStatus.WAITING).exists()


def test_cq8_cannot_close_planned_centre(client_as, planned):
    resp = client_as("ops_lead").post(
        f"/api/1/ops/centres/{planned.id}/close", {"confirm": True}, format="json"
    )
    assert resp.status_code == 400
