import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre
from apps.counsellors.models import Posting
from apps.queue.models import Student, StudentStatus

pytestmark = pytest.mark.django_db
URL = "/api/1/desk/duty"


def test_cq37_counsellor_sets_own_duty_on_current_posting(client_as, counsellor):
    resp = client_as("counsellor").post(URL, {"duty": "on_break"}, format="json")
    assert resp.status_code == 200, resp.content
    assert resp.json()["data"]["duty"] == "on_break"
    assert Posting.objects.get(counsellor=counsellor).duty == "on_break"


def test_cq37_all_three_states_and_nothing_else(client_as, counsellor):
    for duty in ("on_desk", "on_break", "off_duty"):
        assert client_as("counsellor").post(URL, {"duty": duty}, format="json").status_code == 200
    for bad in ("busy", "", None):
        resp = client_as("counsellor").post(URL, {"duty": bad}, format="json")
        assert resp.status_code == 400
    assert Posting.objects.get(counsellor=counsellor).duty == "off_duty"


def test_cq37_duty_change_never_moves_students(client_as, centre, counsellor, other_counsellor):
    now = timezone.now()
    s = Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token="PCM-01",
        name="Asha Rao",
        school="DPS",
        mobile="9811000001",
        course="Eng",
        status=StudentStatus.WAITING,
        checkin_at=now,
        queue_at=now,
        help=["Other"],
    )
    client_as("counsellor").post(URL, {"duty": "off_duty"}, format="json")
    s.refresh_from_db()
    assert (s.counsellor_id, s.status, s.queue_at) == (counsellor.id, StudentStatus.WAITING, now)


def test_cq37_ops_lead_sets_duty_for_a_counsellor_with_audit(client_as, users, counsellor):
    from apps.queue.models import AuditEvent

    resp = client_as("ops_lead").post(
        f"{URL}?as_counsellor={counsellor.id}", {"duty": "on_break"}, format="json"
    )
    assert resp.status_code == 200
    ev = AuditEvent.objects.get(verb="edited", centre=counsellor.postings.get().centre)
    assert ev.data["duty"] == "on_break"
    assert ev.actor == users["ops_lead"] and ev.on_behalf_of == counsellor


def test_cq37_no_live_posting_today_is_a_clear_error(client_as, users):
    from apps.counsellors.models import Counsellor

    c = Counsellor.objects.create(name="Nobody", mobile="9000000009", streams=["PCM"])
    planned = Centre.objects.create(
        city="X",
        venue="V",
        date=timezone.localdate() + dt.timedelta(days=1),
        opens_at=dt.time(9),
        closes_at=dt.time(17),
    )
    Posting.objects.create(counsellor=c, centre=planned, desk_label="D")
    resp = client_as("ops_lead").post(f"{URL}?as_counsellor={c.id}", {"duty": "on_desk"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["code"] == "no_live_posting"
