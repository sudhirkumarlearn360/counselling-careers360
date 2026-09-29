"""CQ-20 / CQ-30: one open token per normalised mobile per centre."""

import pytest

from apps.queue.exceptions import DuplicateToken
from apps.queue.models import Student, StudentStatus, TokenSequence
from apps.queue.services import check_in
from tests.queue.helpers import data, live_centre, post, raw_student

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    centre = live_centre()
    p = post(centre, "Meera", ["PCM"], "Desk 1")
    return centre, p


@pytest.mark.parametrize("status", [StudentStatus.WAITING, StudentStatus.CALLED, StudentStatus.IN_SESSION])
def test_cq20_open_token_same_mobile_is_rejected_naming_the_token(setup, status):
    centre, p = setup
    existing = raw_student(centre, p.counsellor, "PCM-07", status=status, mobile="9811022001")
    TokenSequence.objects.filter(centre=centre).update(last_number=7)
    with pytest.raises(DuplicateToken) as err:
        check_in(centre, data(mobile="+91 98110-22001"), "self")  # normalised before the check
    assert err.value.message == "A token is already open for this number — PCM-07."
    assert err.value.existing == existing
    assert err.value.data["token"] == "PCM-07" and err.value.data["student_id"] == existing.id
    assert Student.objects.count() == 1
    assert TokenSequence.objects.get(centre=centre).last_number == 7


def test_cq30_desk_check_in_uses_the_same_duplicate_rule(setup):
    centre, _ = setup
    first = check_in(centre, data(mobile="9811022001"), "self")
    with pytest.raises(DuplicateToken) as err:
        check_in(centre, data(mobile="09811022001"), "desk")
    assert err.value.existing == first


@pytest.mark.parametrize(
    "status",
    [StudentStatus.DONE, StudentStatus.RELEASED, StudentStatus.NO_SHOW, StudentStatus.NOT_COUNSELLED],
)
def test_cq20_closed_token_may_check_in_again_with_a_new_number(setup, status):
    centre, p = setup
    raw_student(centre, p.counsellor, "PCM-01", status=status, mobile="9811022001")
    TokenSequence.objects.filter(centre=centre).update(last_number=1)
    s = check_in(centre, data(mobile="9811022001"), "self")
    assert s.token == "PCM-02"


def test_cq20_same_mobile_at_another_centre_is_fine(setup):
    centre, _ = setup
    check_in(centre, data(mobile="9811022001"), "self")
    other = live_centre("Indore")
    post(other, "Asha", ["PCM"], "Desk 1")
    s = check_in(other, data(mobile="9811022001"), "self")
    assert s.token == "PCM-01" and s.centre == other
