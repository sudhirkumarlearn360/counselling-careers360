"""The mobile-number rules are shared with the frontend through shared/mobile_cases.json."""

import json
from pathlib import Path

import pytest

from apps.common.validators import normalise_mobile, valid_mobile

CASES = json.loads((Path(__file__).resolve().parents[2] / "shared" / "mobile_cases.json").read_text())


@pytest.mark.parametrize("raw, expected", CASES["valid"])
def test_every_way_of_writing_a_mobile_number_normalises_to_ten_digits(raw, expected):
    assert normalise_mobile(raw) == expected
    assert valid_mobile(raw)


@pytest.mark.parametrize("raw", CASES["invalid"])
def test_things_that_are_not_a_ten_digit_mobile_are_rejected(raw):
    assert not valid_mobile(raw)


def test_a_prefixed_number_finds_the_student_in_search(client_as, centre, counsellor):
    from tests.queue.helpers import raw_student

    s = raw_student(centre, counsellor, "PCM-01", mobile="9811022001")
    hall = (
        client_as("reception").get(f"/api/1/hall/centres/{centre.id}/queue", {"q": "+91 98110 22001"}).json()
    )
    assert [r["id"] for r in hall["data"]["rows"]] == [s.id]
    ops = client_as("ops_lead").get("/api/1/ops/students", {"q": "0 98110 22001"}).json()
    assert [r["id"] for r in ops["data"]] == [s.id]


def test_a_number_typed_with_country_code_can_check_in_and_is_stored_as_ten_digits(
    client_as, centre, counsellor
):
    r = client_as("reception").post(
        f"/api/1/hall/centres/{centre.id}/check-in",
        {"name": "Walk In", "mobile": "+91 (98110) 22001", "stream": "PCM", "help": ["Other"]},
        format="json",
    )
    assert r.status_code == 201 and r.json()["data"]["mobile"] == "9811022001"
    dup = client_as("reception").post(
        f"/api/1/hall/centres/{centre.id}/check-in",
        {"name": "Walk In", "mobile": "09811022001", "stream": "PCM", "help": ["Other"]},
        format="json",
    )
    assert dup.status_code == 409  # the same person, however the number is written
