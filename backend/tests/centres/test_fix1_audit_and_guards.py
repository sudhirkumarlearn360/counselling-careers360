import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Posting
from apps.queue.models import AuditEvent, Student, StudentStatus

pytestmark = pytest.mark.django_db


def waiting(centre, counsellor, token, mobile):
    now = timezone.now()
    return Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token=token,
        name="Asha Rao",
        school="DPS",
        mobile=mobile,
        course="Eng",
        status=StudentStatus.WAITING,
        checkin_at=now,
        queue_at=now,
        help=["Other"],
    )


def test_cq8_close_writes_a_per_student_audit_row(client_as, users, centre, counsellor):
    a = waiting(centre, counsellor, "PCM-01", "9811000001")
    b = waiting(centre, counsellor, "PCM-02", "9811000002")
    client_as("ops_lead").post(f"/api/1/ops/centres/{centre.id}/close", {"confirm": True}, format="json")
    for s in (a, b):
        ev = AuditEvent.objects.get(student=s, verb="centre_closed")
        assert ev.actor == users["ops_lead"] and ev.centre == centre
        assert ev.data == {"to": "not_counselled"}
    assert AuditEvent.objects.filter(centre=centre, verb="centre_closed", student__isnull=True).count() == 1


def test_cq8_second_close_on_closed_centre_is_refused(client_as, centre):
    url = f"/api/1/ops/centres/{centre.id}/close"
    assert client_as("ops_lead").post(url, {"confirm": True}, format="json").status_code == 200
    resp = client_as("ops_lead").post(url, {"confirm": True}, format="json")
    assert resp.status_code == 400 and resp.json()["code"] == "not_live"
    assert AuditEvent.objects.filter(centre=centre, verb="centre_closed", student__isnull=True).count() == 1


def test_cq8_go_live_writes_centre_live_audit_with_uncovered(client_as, users):
    c = Centre.objects.create(
        city="Y", venue="V", date=timezone.localdate(), opens_at=dt.time(9), closes_at=dt.time(17)
    )
    client_as("ops_lead").post(f"/api/1/ops/centres/{c.id}/go-live", {"confirm": True}, format="json")
    ev = AuditEvent.objects.get(centre=c, verb="centre_live")
    assert ev.actor == users["ops_lead"] and len(ev.data["uncovered_streams"]) == 6


def test_cq7_centre_edit_writes_audit_row_naming_fields(client_as, users, centre):
    client_as("ops_lead").patch(f"/api/1/ops/centres/{centre.id}", {"venue": "New"}, format="json")
    ev = AuditEvent.objects.get(centre=centre, verb="edited")
    assert ev.actor == users["ops_lead"] and ev.data == {"fields": ["venue"]}


def test_cq9_posting_desk_edit_at_closed_centre_is_refused(client_as, centre, counsellor):
    p = counsellor.postings.get()
    centre.status = CentreStatus.CLOSED
    centre.save()
    resp = client_as("ops_lead").patch(f"/api/1/ops/postings/{p.id}", {"desk_label": "Desk 9"}, format="json")
    assert resp.status_code == 400 and resp.json()["code"] == "centre_closed"
    p.refresh_from_db()
    assert p.desk_label == "Desk 1"


def test_cq9_posting_creation_at_closed_centre_is_refused(client_as, centre):
    centre.status = CentreStatus.CLOSED
    centre.save()
    c = Counsellor.objects.create(name="Z", mobile="9811000077", streams=["PCM"])
    resp = client_as("ops_lead").post(
        f"/api/1/ops/counsellors/{c.id}/postings", {"centre_id": centre.id, "desk_label": "D"}, format="json"
    )
    assert resp.status_code == 400 and resp.json()["code"] == "centre_closed"
    assert not Posting.objects.filter(counsellor=c).exists()
