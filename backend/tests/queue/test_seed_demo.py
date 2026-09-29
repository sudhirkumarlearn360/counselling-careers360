import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Duty, Posting
from apps.queue.models import SessionRecord, Student, StudentStatus, TokenSequence

pytestmark = pytest.mark.django_db


def counts():
    return (
        Centre.objects.count(),
        Counsellor.objects.count(),
        Posting.objects.count(),
        StaffUser.objects.count(),
        Student.objects.count(),
        SessionRecord.objects.count(),
    )


@override_settings(DEBUG=True)
def test_seed_demo_creates_prototype_data_and_is_idempotent():
    call_command("seed_demo")
    first = counts()
    call_command("seed_demo")
    assert counts() == first == (3, 5, 5, 7, 9, 1)

    today = timezone.localdate()
    gwalior = Centre.objects.get(city="Gwalior")
    assert gwalior.status == CentreStatus.LIVE and gwalior.date == today
    assert Centre.objects.get(city="Indore").date == today + timezone.timedelta(days=2)
    assert Centre.objects.get(city="Jaipur").date == today + timezone.timedelta(days=5)
    assert TokenSequence.objects.get(centre=gwalior).last_number == 9

    aditi = Posting.objects.get(counsellor__name="Aditi Sharma")
    assert (aditi.centre, aditi.desk_label, aditi.duty) == (gwalior, "Desk 3", Duty.ON_BREAK)

    done = Student.objects.get(centre=gwalior, token="PCB-01")
    assert done.status == StudentStatus.DONE and done.rating == 5 and done.outcome == "ready"
    assert done.session_records.get().counsellor.name == "Rahul Verma"
    assert Student.objects.get(token="PCB-04").source == "desk"
    assert Student.objects.get(token="PCB-04").consent == "pending"


@override_settings(DEBUG=True)
def test_seed_demo_users_and_debug_passwords():
    call_command("seed_demo")
    admin = StaffUser.objects.get(email="admin@careers360.com")
    assert admin.role == Role.OPS_LEAD and admin.check_password("admin123")
    reception = StaffUser.objects.get(email="reception@careers360.com")
    assert reception.role == Role.RECEPTION and reception.centre.city == "Gwalior"
    assert reception.check_password("desk123")
    meera = StaffUser.objects.get(email="meera@careers360.com")
    assert meera.role == Role.COUNSELLOR and meera.counsellor.name == "Meera Iyer"
    assert meera.check_password("desk123")


@override_settings(DEBUG=False, SEED_ADMIN_PASSWORD="", SEED_STAFF_PASSWORD="")
def test_seed_demo_outside_debug_sets_no_known_passwords():
    call_command("seed_demo")
    admin = StaffUser.objects.get(email="admin@careers360.com")
    assert not admin.check_password("admin123")
    assert not admin.has_usable_password()


@override_settings(DEBUG=True)
def test_seed_demo_reset_reseeds_students_without_rewinding_tokens():
    call_command("seed_demo")
    gwalior = Centre.objects.get(city="Gwalior")
    TokenSequence.objects.filter(centre=gwalior).update(last_number=14)
    Student.objects.filter(token="PCM-03").update(name="Changed")
    call_command("seed_demo", "--reset")
    assert Student.objects.get(token="PCM-03").name == "Sahil Yadav"
    assert Student.objects.count() == 9
    assert TokenSequence.objects.get(centre=gwalior).last_number == 14
