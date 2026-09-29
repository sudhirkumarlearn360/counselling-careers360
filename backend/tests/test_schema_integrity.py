"""Fix round 2: nothing is deleted (PROTECT everywhere), constraints, collations, admin guards."""

import datetime as dt
from unittest import mock

import pytest
from django.contrib import admin
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreSettings
from apps.counsellors.models import Counsellor
from apps.messaging.models import Message, OtpCode
from apps.queue.models import AuditEvent, Note, SessionRecord, Student
from tests.test_models import make_centre, make_counsellor, make_student

pytestmark = pytest.mark.django_db


@pytest.fixture
def world():
    centre = make_centre()
    counsellor = make_counsellor()
    student = make_student(centre, counsellor)
    return centre, counsellor, student


def session(student, **kw):
    now = timezone.now()
    fields = dict(
        student=student,
        counsellor=student.counsellor,
        centre=student.centre,
        called_at=now,
        queue_at=student.queue_at,
        started_at=now,
        ended_at=now + dt.timedelta(minutes=12),
    )
    fields.update(kw)
    return SessionRecord.objects.create(**fields)


# --- 12. notes ----------------------------------------------------------------


def test_cq45_empty_note_rejected(world):
    _, counsellor, student = world
    with pytest.raises(IntegrityError), transaction.atomic():
        Note.objects.create(student=student, text="", author_name=counsellor.name, author=counsellor)


# --- 2/3. PROTECT: history rows block deletes -------------------------------


@pytest.mark.parametrize("history", ["note", "audit", "session", "message"])
def test_student_with_history_cannot_be_deleted(world, history):
    centre, counsellor, student = world
    if history == "note":
        Note.objects.create(student=student, text="x", author_name="M", author=counsellor)
    elif history == "audit":
        AuditEvent.objects.create(student=student, centre=centre, verb=AuditEvent.Verb.CHECKED_IN)
    elif history == "session":
        session(student)
    else:
        Message.objects.create(
            student=student, template=Message.Template.TURN_CALLED, to=student.mobile, body="b"
        )
    with pytest.raises(ProtectedError):
        student.delete()


def test_centre_with_students_cannot_be_deleted(world):
    centre, _, _ = world
    with pytest.raises(ProtectedError):
        centre.delete()


def test_centre_cannot_be_deleted_even_when_empty():
    centre = make_centre()  # has CentreSettings + TokenSequence (both PROTECT)
    with pytest.raises(ProtectedError):
        centre.delete()


def test_staff_user_referenced_by_audit_cannot_be_deleted(world):
    centre, _, student = world
    lead = StaffUser.objects.create_user(
        email="lead@careers360.com", password="x", name="L", role=Role.OPS_LEAD
    )
    AuditEvent.objects.create(student=student, centre=centre, verb=AuditEvent.Verb.CALLED, actor=lead)
    with pytest.raises(ProtectedError):
        lead.delete()


@pytest.mark.parametrize("link", ["note_author", "consent_by", "on_behalf_of", "staff_user"])
def test_counsellor_referenced_by_history_cannot_be_deleted(world, link):
    centre, _, student = world
    other = make_counsellor(name="Rahul Verma", mobile="9811022002")  # has no students of its own
    if link == "note_author":
        Note.objects.create(student=student, text="x", author_name=other.name, author=other)
    elif link == "consent_by":
        Student.objects.filter(pk=student.pk).update(consent_by=other)
    elif link == "on_behalf_of":
        AuditEvent.objects.create(
            student=student, centre=centre, verb=AuditEvent.Verb.NOTED, on_behalf_of=other
        )
    else:
        StaffUser.objects.create_user(
            email="rahul@careers360.com", password="x", name="R", role=Role.COUNSELLOR, counsellor=other
        )
    with pytest.raises(ProtectedError):
        other.delete()


def test_reception_centre_is_protected():
    centre = make_centre()
    StaffUser.objects.create_user(
        email="r@careers360.com", password="x", name="R", role=Role.RECEPTION, centre=centre
    )
    with pytest.raises(ProtectedError):
        centre.delete()


# --- 6. CheckConstraints -----------------------------------------------------


def test_cq49_session_record_cannot_end_before_it_starts(world):
    _, _, student = world
    now = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        session(student, started_at=now, ended_at=now - dt.timedelta(seconds=1))


def test_cq49_zero_length_session_is_allowed(world):
    _, _, student = world
    now = timezone.now()
    assert session(student, started_at=now, ended_at=now).pk


@pytest.mark.parametrize("field", ["recall_limit", "target_session_min", "wait_sla_min"])
def test_cq46_centre_settings_must_be_at_least_1(field):
    centre = make_centre()
    with pytest.raises(IntegrityError), transaction.atomic():
        CentreSettings.objects.filter(centre=centre).update(**{field: 0})


def test_cq21_counsellor_expected_session_must_be_at_least_1():
    with pytest.raises(IntegrityError), transaction.atomic():
        Counsellor.objects.create(name="Z", mobile="9811022009", streams=["PCM"], expected_session_min=0)


# --- 5. SessionRecord snapshot -------------------------------------------------


def test_cq21_session_record_snapshots_queue_at(world):
    _, _, student = world
    record = session(student)
    assert record.queue_at == student.queue_at


# --- 7. binary collation / uniqueness ------------------------------------------


def test_cq26_access_key_is_case_sensitive(world):
    centre, counsellor, student = world
    Student.objects.filter(pk=student.pk).update(access_key="AbCdEf.key")
    other = make_student(centre, counsellor, token="PCM-02", mobile="9000010002")
    Student.objects.filter(pk=other.pk).update(access_key="abcdef.key")  # would clash under a _ci collation
    assert Student.objects.filter(access_key="AbCdEf.key").get() == student
    assert Student.objects.filter(access_key="abcdef.key").get() == other


def test_cq18_verification_nonce_nullable_and_unique():
    centre = make_centre()
    expires = timezone.now() + dt.timedelta(minutes=10)
    OtpCode.objects.create(mobile="9000010001", centre=centre, code_hash="h", expires_at=expires)
    OtpCode.objects.create(mobile="9000010002", centre=centre, code_hash="h", expires_at=expires)  # two NULLs
    OtpCode.objects.create(
        mobile="9000010003", centre=centre, code_hash="h", expires_at=expires, verification_nonce="Nonce"
    )
    OtpCode.objects.create(
        mobile="9000010004", centre=centre, code_hash="h", expires_at=expires, verification_nonce="nonce"
    )  # case-distinct under utf8mb4_bin
    with pytest.raises(IntegrityError), transaction.atomic():
        OtpCode.objects.create(
            mobile="9000010005", centre=centre, code_hash="h", expires_at=expires, verification_nonce="Nonce"
        )


# --- 9. Message.to -------------------------------------------------------------


def test_cq58_message_to_holds_16_chars(world):
    _, _, student = world
    assert Message._meta.get_field("to").max_length == 16
    m = Message.objects.create(
        student=student, template=Message.Template.TURN_CALLED, to="+919811022001123", body="b"
    )  # 16 chars; strict mode would reject this at max_length 10
    m.refresh_from_db()
    assert m.to == "+919811022001123"


# --- 10. indexes -----------------------------------------------------------------


def test_cq59_student_list_indexes():
    index_fields = [tuple(i.fields) for i in Student._meta.indexes]
    assert ("centre", "checkin_at") in index_fields
    assert ("checkin_at",) in index_fields


# --- 11. slug race -------------------------------------------------------------


def test_cq6_slug_collision_on_insert_retries_once():
    first = make_centre()
    real = Centre._unique_slug
    calls = []

    def racing(self):
        calls.append(1)
        return first.slug if len(calls) == 1 else real(self)  # 1st pick loses the race

    with mock.patch.object(Centre, "_unique_slug", racing):
        second = make_centre()
    assert second.slug != first.slug and len(calls) == 2


def test_cq6_non_slug_integrity_errors_are_not_retried():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_centre(opens_at=dt.time(18, 0), closes_at=dt.time(10, 0))


# --- 2/8. admin guards -----------------------------------------------------------


@pytest.mark.parametrize("model", [Student, Note, AuditEvent, SessionRecord, Message])
def test_history_models_cannot_be_deleted_in_admin(model):
    request = RequestFactory().get("/admin/")
    request.user = StaffUser(is_superuser=True, is_staff=True, is_active=True)
    assert admin.site._registry[model].has_delete_permission(request) is False


def test_admin_inlines_cannot_delete():
    student_admin = admin.site._registry[Student]
    assert student_admin.inlines and all(inline.can_delete is False for inline in student_admin.inlines)


def test_student_admin_queue_state_is_read_only():
    readonly = set(admin.site._registry[Student].readonly_fields)
    assert {
        "centre",
        "counsellor",
        "status",
        "queue_at",
        "priority",
        "called_at",
        "started_at",
        "ended_at",
        "recalls",
        "consent",
        "consent_by",
        "rating",
        "access_key",
        "token",
    } <= readonly
