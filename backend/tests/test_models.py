"""B0: schema constraints every later task relies on."""

import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreSettings, CentreStatus
from apps.common import choices
from apps.counsellors.models import Counsellor, Duty, Posting
from apps.messaging.models import Message, OtpCode
from apps.queue.models import AuditEvent, Note, SessionRecord, Student, StudentStatus, TokenSequence

pytestmark = pytest.mark.django_db


def make_centre(city="Gwalior", day=None, **kw):
    return Centre.objects.create(
        city=city,
        venue=kw.pop("venue", "Hotel Landmark"),
        date=day or timezone.localdate(),
        opens_at=kw.pop("opens_at", dt.time(10, 0)),
        closes_at=kw.pop("closes_at", dt.time(18, 0)),
        **kw,
    )


def make_counsellor(name="Meera Iyer", mobile="9811022001", streams=("PCM",)):
    return Counsellor.objects.create(name=name, mobile=mobile, streams=list(streams))


def make_student(centre, counsellor, token="PCM-01", mobile="9000010001", **kw):
    now = timezone.now()
    return Student.objects.create(
        token=token,
        centre=centre,
        counsellor=counsellor,
        name="Priya Nair",
        school="Carmel Convent",
        mobile=mobile,
        stream="PCM",
        course="B.Tech",
        help=["College selection"],
        checkin_at=now,
        queue_at=now,
        **kw,
    )


# --- Centre ---------------------------------------------------------------


def test_cq6_new_centre_is_planned_with_slug_and_default_settings():
    centre = make_centre()
    assert centre.status == CentreStatus.PLANNED
    assert centre.slug
    s = CentreSettings.objects.get(centre=centre)
    assert (s.target_session_min, s.wait_sla_min, s.recall_limit, s.whatsapp_enabled) == (15, 30, 2, True)


def test_cq6_centre_slugs_are_unique_for_same_city_and_date():
    a = make_centre()
    b = make_centre()
    assert a.slug != b.slug


def test_cq6_closing_time_must_be_after_opening():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_centre(opens_at=dt.time(18, 0), closes_at=dt.time(10, 0))


def test_cq19_token_sequence_created_with_centre():
    centre = make_centre()
    seq = TokenSequence.objects.get(centre=centre)
    assert seq.last_number == 0


# --- Counsellor / Posting -------------------------------------------------


def test_cq9_new_posting_starts_off_duty():
    posting = Posting.objects.create(counsellor=make_counsellor(), centre=make_centre(), desk_label="Desk 1")
    assert posting.duty == Duty.OFF_DUTY


def test_cq9_desk_label_unique_per_centre():
    centre = make_centre()
    Posting.objects.create(counsellor=make_counsellor(), centre=centre, desk_label="Desk 1")
    other = make_counsellor(name="Rahul Verma", mobile="9811022002")
    with pytest.raises(IntegrityError), transaction.atomic():
        Posting.objects.create(counsellor=other, centre=centre, desk_label="Desk 1")


def test_cq9_same_desk_label_allowed_at_another_centre():
    c = make_counsellor()
    Posting.objects.create(counsellor=c, centre=make_centre(), desk_label="Desk 1")
    Posting.objects.create(counsellor=c, centre=make_centre(city="Indore"), desk_label="Desk 1")
    assert Posting.objects.filter(counsellor=c).count() == 2


def test_cq11_counsellor_posted_once_per_centre():
    centre = make_centre()
    c = make_counsellor()
    Posting.objects.create(counsellor=c, centre=centre, desk_label="Desk 1")
    with pytest.raises(IntegrityError), transaction.atomic():
        Posting.objects.create(counsellor=c, centre=centre, desk_label="Desk 2")


# --- StaffUser ------------------------------------------------------------


def test_cq1_staff_email_stored_lowercased_and_trimmed():
    user = StaffUser.objects.create_user(
        email="  Admin@Careers360.COM ", password="x", name="N", role=Role.OPS_LEAD
    )
    assert user.email == "admin@careers360.com"
    assert user.check_password("x")


def test_cq1_staff_email_unique_regardless_of_case():
    StaffUser.objects.create_user(email="a@careers360.com", password="x", name="A", role=Role.OPS_LEAD)
    with pytest.raises(IntegrityError), transaction.atomic():
        StaffUser.objects.create_user(email="A@Careers360.com", password="x", name="B", role=Role.OPS_LEAD)


def test_cq3_counsellor_user_must_link_a_counsellor():
    with pytest.raises(IntegrityError), transaction.atomic():
        StaffUser.objects.create_user(email="c@careers360.com", password="x", name="C", role=Role.COUNSELLOR)


def test_cq3_reception_user_must_have_a_centre():
    with pytest.raises(IntegrityError), transaction.atomic():
        StaffUser.objects.create_user(email="r@careers360.com", password="x", name="R", role=Role.RECEPTION)


# --- Student and friends --------------------------------------------------


def test_cq19_token_unique_per_centre():
    centre, c = make_centre(), make_counsellor()
    make_student(centre, c)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_student(centre, c, mobile="9000010002")


def test_cq26_student_gets_unique_access_key():
    centre, c = make_centre(), make_counsellor()
    a = make_student(centre, c)
    b = make_student(centre, c, token="PCM-02", mobile="9000010002")
    assert a.access_key and b.access_key and a.access_key != b.access_key
    assert a.status == StudentStatus.WAITING
    assert a.priority == 0 and a.recalls == 0


def test_cq28_rating_must_be_between_1_and_5():
    centre, c = make_centre(), make_counsellor()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_student(centre, c, rating=6)


def test_cq21_session_record_and_note_and_audit_rows():
    centre, c = make_centre(), make_counsellor()
    s = make_student(centre, c)
    now = timezone.now()
    SessionRecord.objects.create(
        student=s,
        counsellor=c,
        centre=centre,
        called_at=now,
        started_at=now,
        ended_at=now,
        outcome=choices.Outcome.READY,
    )
    Note.objects.create(student=s, text="Strong scores", author_name=c.name, author=c)
    AuditEvent.objects.create(student=None, centre=centre, verb=AuditEvent.Verb.CENTRE_LIVE)
    AuditEvent.objects.create(student=s, centre=centre, verb=AuditEvent.Verb.CHECKED_IN, data={"src": "self"})
    assert s.session_records.count() == 1
    assert s.notes.count() == 1
    assert AuditEvent.objects.filter(centre=centre).count() == 2


def test_cq18_message_and_otp_rows():
    centre, c = make_centre(), make_counsellor()
    s = make_student(centre, c)
    m = Message.objects.create(student=s, template=Message.Template.TURN_CALLED, to=s.mobile, body="hi")
    assert m.status == Message.Status.QUEUED
    otp = OtpCode.objects.create(
        mobile="9000010001",
        centre=centre,
        code_hash="x",
        expires_at=timezone.now() + dt.timedelta(minutes=10),
    )
    assert otp.attempts == 0


# --- Enums ------------------------------------------------------------------


def test_domain_enums_have_exact_values():
    assert [(v, str(label)) for v, label in choices.Stream.choices] == [
        ("PCM", "Science – PCM"),
        ("PCB", "Science – PCB"),
        ("PCMB", "Science – PCMB"),
        ("COM", "Commerce"),
        ("HUM", "Humanities / Arts"),
        ("OTH", "Other"),
    ]
    assert choices.Exam.values == ["JEE", "NEET", "CUET", "CLAT", "Other", "None / not sure"]
    assert choices.Clarity.values == [
        "Very clear",
        "Have shortlisted options",
        "Need help shortlisting",
        "Completely confused",
    ]
    assert choices.Help.values == [
        "College selection",
        "Course selection",
        "College & course comparison",
        "Admission / counselling",
        "Cut-offs & college chances",
        "Entrance exams",
        "Other",
    ]
    assert choices.Klass.values == [
        "Class 11",
        "Class 12",
        "Dropper / repeat year",
        "Graduate",
        "Parent enquiring",
    ]
    assert [(v, str(label)) for v, label in choices.Outcome.choices] == [
        ("ready", "Ready to apply"),
        ("interested", "Interested, needs time"),
        ("exploring", "Just exploring"),
        ("not_fit", "Not a fit"),
    ]
    assert StudentStatus.values == [
        "waiting",
        "called",
        "in_session",
        "done",
        "no_show",
        "released",
        "not_counselled",
    ]
    assert Duty.values == ["on_desk", "on_break", "off_duty"]
    assert Role.values == ["ops_lead", "reception", "counsellor"]
    assert CentreStatus.values == ["planned", "live", "closed"]
    assert Message.Status.values == ["queued", "sent", "delivered", "failed"]
    assert AuditEvent.Verb.values == [
        "checked_in",
        "called",
        "started",
        "completed",
        "missed",
        "no_show",
        "released",
        "requeued",
        "moved",
        "pulled_forward",
        "consent_given",
        "edited",
        "noted",
        "rated",
        "message_failed",
        "centre_live",
        "centre_closed",
        "exported",
    ]
