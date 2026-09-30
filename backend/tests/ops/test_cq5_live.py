import datetime as dt

import pytest
from django.utils import timezone

from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Duty, Posting
from apps.queue.models import SessionRecord, Student, StudentStatus

pytestmark = pytest.mark.django_db
URL = "/api/1/ops/live"


def student(centre, counsellor, token, status, mobile, **extra):
    now = timezone.now()
    return Student.objects.create(
        centre=centre,
        counsellor=counsellor,
        token=token,
        name="Asha Rao",
        school="DPS",
        mobile=mobile,
        course="Engineering",
        status=status,
        checkin_at=now,
        queue_at=now,
        help=["College selection"],
        **extra,
    )


def test_cq5_live_lists_only_live_centres_with_counsellor_cards(
    client_as, centre, counsellor, other_counsellor
):
    Centre.objects.create(
        city="Indore",
        venue="X",
        date=timezone.localdate(),
        opens_at=dt.time(10),
        closes_at=dt.time(17),
        status=CentreStatus.PLANNED,
    )
    body = client_as("ops_lead").get(URL).json()
    assert body["count"] == body["total"] == 1
    c = body["data"][0]
    assert (c["id"], c["city"], c["status"]) == (centre.id, "Gwalior", "live")
    cards = {x["counsellor_id"]: x for x in c["counsellors"]}
    card = cards[counsellor.id]
    assert card["name"] == "Meera Iyer" and card["desk_label"] == "Desk 1" and card["duty"] == "on_desk"
    assert card["posting_id"] == Posting.objects.get(counsellor=counsellor).id
    assert cards[other_counsellor.id]["duty"] == "off_duty"


def test_cq5_card_shows_serving_token_queue_length_and_open_desk_control(client_as, centre, counsellor):
    student(centre, counsellor, "PCM-01", StudentStatus.IN_SESSION, "9000000001")
    student(centre, counsellor, "PCM-02", StudentStatus.WAITING, "9000000002")
    student(centre, counsellor, "PCM-03", StudentStatus.WAITING, "9000000003")
    student(centre, counsellor, "PCM-04", StudentStatus.DONE, "9000000004")
    card = next(
        x
        for x in client_as("ops_lead").get(URL).json()["data"][0]["counsellors"]
        if x["counsellor_id"] == counsellor.id
    )
    assert card["serving"]["token"] == "PCM-01" and card["serving"]["status"] == "in_session"
    assert card["serving"]["name"]
    assert card["queue_length"] == 2
    assert card["open_desk"] == {"as_counsellor": counsellor.id, "centre_id": centre.id}


def test_cq5_card_without_serving_student_and_avg_falls_back_to_expected(client_as, centre, counsellor):
    card = next(
        x
        for x in client_as("ops_lead").get(URL).json()["data"][0]["counsellors"]
        if x["counsellor_id"] == counsellor.id
    )
    assert card["serving"] is None and card["queue_length"] == 0
    assert card["avg_session_min"] == 15 and card["avg_session_n"] == 0


def test_cq5_card_avg_session_from_session_records_today(client_as, centre, counsellor):
    now = timezone.now()
    s = student(centre, counsellor, "PCM-01", StudentStatus.DONE, "9000000001")
    for minutes in (10, 20):
        SessionRecord.objects.create(
            student=s,
            counsellor=counsellor,
            centre=centre,
            queue_at=now - dt.timedelta(hours=1),
            called_at=now - dt.timedelta(minutes=40),
            started_at=now - dt.timedelta(minutes=minutes),
            ended_at=now,
        )
    card = next(
        x
        for x in client_as("ops_lead").get(URL).json()["data"][0]["counsellors"]
        if x["counsellor_id"] == counsellor.id
    )
    assert card["avg_session_min"] == 15 and card["avg_session_n"] == 2


def test_cq5_live_is_ops_lead_only(client_as):
    assert client_as("anonymous").get(URL).status_code == 401
    for role in ("reception", "counsellor"):
        r = client_as(role).get(URL)
        assert r.status_code == 403 and r.json()["code"] == "role_not_allowed"


def test_cq5_live_query_count_is_flat(
    client_as, centre, counsellor, other_counsellor, django_assert_max_num_queries
):
    for i in range(6):
        student(centre, counsellor, f"PCM-{i:02d}", StudentStatus.WAITING, f"90000001{i:02d}")
    Posting.objects.filter(counsellor=other_counsellor).update(duty=Duty.ON_DESK)
    client = client_as("ops_lead")
    with django_assert_max_num_queries(8):
        assert client.get(URL).status_code == 200


def test_live_centre_summary_tiles_and_desk_card_details(client_as, centre, counsellor):
    """The live view's tiles: checked in (self vs desk), waiting/late, counselled, no-shows, capacity."""
    import datetime as dt

    from django.utils import timezone

    old = timezone.now() - dt.timedelta(minutes=45)
    centre.expected_students = 20
    centre.save()
    a = student(centre, counsellor, "PCM-01", StudentStatus.WAITING, "9000000001")
    a.queue_at = old
    a.save()
    student(centre, counsellor, "PCM-02", StudentStatus.DONE, "9000000002")
    b = student(centre, counsellor, "PCM-03", StudentStatus.NO_SHOW, "9000000003")
    b.source = "desk"
    b.save()
    data = client_as("ops_lead").get(URL).json()["data"][0]
    assert data["summary"] == {
        "checked_in": 3,
        "self_scan": 2,
        "at_desk": 1,
        "waiting": 1,
        "late": 1,
        "counselled": 1,
        "no_shows": 1,
        "planned": 20,
        "capacity_pct": 15,
    }
    card = data["counsellors"][0]
    assert card["queue_length"] == 1 and card["queue_late"] == 1
