import pytest

from apps.counsellors.models import Counsellor, Posting

pytestmark = pytest.mark.django_db
URL = "/api/1/ops/counsellors"


def body(centre, **over):
    data = {
        "name": "Priya Nair",
        "mobile": "+91 98110 22333",
        "streams": ["PCB", "HUM"],
        "centre_id": centre.id,
        "desk_label": "Desk 7",
    }
    data.update(over)
    return data


def test_cq9_creates_counsellor_with_posting_starting_off_duty(client_as, centre):
    resp = client_as("ops_lead").post(URL, body(centre), format="json")
    assert resp.status_code == 201, resp.content
    d = resp.json()["data"]
    assert d["mobile"] == "9811022333"  # normalised
    assert d["streams"] == ["PCB", "HUM"]
    assert d["expected_session_min"] == 15
    p = Posting.objects.get(counsellor_id=d["id"])
    assert (p.centre, p.desk_label, p.duty) == (centre, "Desk 7", "off_duty")
    assert d["postings"][0]["duty"] == "off_duty"


def test_cq9_counsellor_can_be_created_then_posted_later(client_as, centre):
    data = body(centre)
    del data["centre_id"], data["desk_label"]
    resp = client_as("ops_lead").post(URL, data, format="json")
    assert resp.status_code == 201
    cid = resp.json()["data"]["id"]
    assert resp.json()["data"]["postings"] == []
    resp = client_as("ops_lead").post(
        f"{URL}/{cid}/postings", {"centre_id": centre.id, "desk_label": "Desk 9"}, format="json"
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["data"]["duty"] == "off_duty"
    assert resp.json()["data"]["desk_label"] == "Desk 9"


@pytest.mark.parametrize(
    "over",
    [{"name": "  "}, {"streams": []}, {"streams": ["XYZ"]}, {"streams": "PCM"}],
)
def test_cq9_name_and_a_valid_stream_are_needed(client_as, centre, over):
    resp = client_as("ops_lead").post(URL, body(centre, **over), format="json")
    assert resp.status_code == 400
    assert resp.json()["message"] == "A name and at least one stream are needed."
    assert Counsellor.objects.filter(name="Priya Nair").count() == 0


def test_cq9_mobile_must_be_ten_digits(client_as, centre):
    resp = client_as("ops_lead").post(URL, body(centre, mobile="12345"), format="json")
    assert resp.status_code == 400
    assert resp.json()["message"] == "A 10-digit mobile number is needed."


def test_cq9_any_combination_including_all_six(client_as, centre):
    six = ["PCM", "PCB", "PCMB", "COM", "HUM", "OTH"]
    resp = client_as("ops_lead").post(URL, body(centre, streams=six), format="json")
    assert resp.status_code == 201
    assert resp.json()["data"]["streams"] == six


def test_cq9_desk_label_clash_is_rejected_naming_the_clash(client_as, centre, counsellor):
    resp = client_as("ops_lead").post(URL, body(centre, desk_label="Desk 1"), format="json")
    assert resp.status_code == 400
    assert resp.json()["message"] == "Desk 1 is already taken by Meera Iyer at this centre."
    assert resp.json()["code"] == "desk_clash"
    assert not Counsellor.objects.filter(name="Priya Nair").exists()  # nothing half-saved


def test_cq9_posting_endpoint_rejects_clash_too(client_as, centre, counsellor):
    third = Counsellor.objects.create(name="Third", mobile="9811022777", streams=["PCM"])
    resp = client_as("ops_lead").post(
        f"{URL}/{third.id}/postings", {"centre_id": centre.id, "desk_label": "desk 1"}, format="json"
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Desk 1 is already taken by Meera Iyer at this centre."


def test_cq9_edit_counsellor(client_as, counsellor):
    resp = client_as("ops_lead").patch(
        f"{URL}/{counsellor.id}",
        {"streams": ["COM"], "mobile": "09811022555", "name": "Meera I"},
        format="json",
    )
    assert resp.status_code == 200
    counsellor.refresh_from_db()
    assert (counsellor.streams, counsellor.mobile, counsellor.name) == (["COM"], "9811022555", "Meera I")
    r = client_as("ops_lead").patch(f"{URL}/{counsellor.id}", {"streams": []}, format="json")
    assert r.json()["message"] == "A name and at least one stream are needed."


def test_cq9_move_posting_to_another_desk_label_checks_clash(client_as, centre, counsellor, other_counsellor):
    p = other_counsellor.postings.get()
    resp = client_as("ops_lead").patch(f"/api/1/ops/postings/{p.id}", {"desk_label": "Desk 1"}, format="json")
    assert resp.status_code == 400
    assert resp.json()["message"] == "Desk 1 is already taken by Meera Iyer at this centre."
    resp = client_as("ops_lead").patch(f"/api/1/ops/postings/{p.id}", {"desk_label": "Desk 5"}, format="json")
    assert resp.status_code == 200
    p.refresh_from_db()
    assert p.desk_label == "Desk 5"
    assert p.duty == "off_duty"


def test_cq9_counsellor_already_posted_to_centre_is_rejected(client_as, centre, counsellor):
    resp = client_as("ops_lead").post(
        f"{URL}/{counsellor.id}/postings", {"centre_id": centre.id, "desk_label": "Desk 8"}, format="json"
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Meera Iyer is already posted to this centre."


def test_cq9_detail_and_404(client_as, counsellor):
    assert client_as("ops_lead").get(f"{URL}/{counsellor.id}").json()["data"]["name"] == "Meera Iyer"
    assert client_as("ops_lead").get(f"{URL}/999999").status_code == 404
    assert client_as("ops_lead").get(f"{URL}/999999/postings").status_code == 404
