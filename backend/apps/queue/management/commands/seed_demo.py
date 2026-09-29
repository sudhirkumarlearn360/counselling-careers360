"""Recreate the prototype's demo data (the `seed()` function in "CounselQueue — staff console.html").

Idempotent: centres, counsellors, postings and users are upserted by natural key; students are
created only if their (centre, token) is missing, so a rerun never duplicates or clobbers live state.
`--reset` deletes the demo centres' students first and seeds them fresh (times relative to now).

Students are written directly through the ORM because this runs before any queue service exists.
Passwords: `admin123` / `desk123` only when DEBUG; otherwise SEED_ADMIN_PASSWORD / SEED_STAFF_PASSWORD
from the environment, or an unusable password when those are unset.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, StaffUser
from apps.centres.models import Centre, CentreStatus
from apps.counsellors.models import Counsellor, Duty, Posting
from apps.queue.models import (
    AuditEvent,
    Consent,
    Note,
    SessionRecord,
    Source,
    Student,
    StudentStatus,
    TokenSequence,
)

MIN = dt.timedelta(minutes=1)
FRONT_DESK_PHONE = "1800 572 9877"

CENTRES = [
    # slug, city, venue, days from today, opens, closes, expected, status
    (
        "gwalior-demo",
        "Gwalior",
        "Hotel Landmark, City Centre",
        0,
        dt.time(10, 0),
        dt.time(18, 0),
        120,
        CentreStatus.LIVE,
    ),
    (
        "indore-demo",
        "Indore",
        "Brilliant Convention Centre",
        2,
        dt.time(10, 0),
        dt.time(17, 0),
        150,
        CentreStatus.PLANNED,
    ),
    (
        "jaipur-demo",
        "Jaipur",
        "Hotel Clarks Amer",
        5,
        dt.time(9, 30),
        dt.time(18, 0),
        200,
        CentreStatus.PLANNED,
    ),
]

COUNSELLORS = [
    # email, name, mobile, desk, streams, centre slug, duty, expected_session_min
    (
        "meera@careers360.com",
        "Meera Iyer",
        "9811022001",
        "Desk 1",
        ["PCM", "PCMB"],
        "gwalior-demo",
        Duty.ON_DESK,
        14,
    ),
    (
        "rahul@careers360.com",
        "Rahul Verma",
        "9811022002",
        "Desk 2",
        ["PCB", "PCMB"],
        "gwalior-demo",
        Duty.ON_DESK,
        17,
    ),
    (
        "aditi@careers360.com",
        "Aditi Sharma",
        "9811022003",
        "Desk 3",
        ["COM", "HUM", "OTH"],
        "gwalior-demo",
        Duty.ON_BREAK,
        12,
    ),
    (
        "farid@careers360.com",
        "Farid Khan",
        "9811022004",
        "Desk 1",
        ["PCM", "COM"],
        "indore-demo",
        Duty.OFF_DUTY,
        15,
    ),
    (
        "nisha@careers360.com",
        "Nisha Rao",
        "9811022005",
        "Desk 2",
        ["PCB", "OTH"],
        "indore-demo",
        Duty.OFF_DUTY,
        16,
    ),
]

# Minutes are relative to "now" at seed time (the prototype's `t - N*MIN`).
STUDENTS: list[dict[str, Any]] = [
    dict(
        token="PCB-01",
        name="Ankit Patel",
        school="Delhi Public School, Gwalior",
        mobile="9000010001",
        parent_mobile="9000020001",
        email="ankit.p@example.com",
        stream="PCB",
        klass="Class 12",
        counsellor="Rahul Verma",
        status=StudentStatus.DONE,
        consent=Consent.GIVEN,
        checkin=72,
        called=64,
        started=63,
        ended=45,
        course="MBBS",
        exams=["NEET"],
        clarity="Have shortlisted options",
        help=["College selection", "Cut-offs & college chances"],
        home_city="Gwalior",
        target_exam="NEET 2027",
        budget="8-12 L",
        outcome="ready",  # prototype "hot"
        colleges_discussed="AIIMS Bhopal, MGM Indore",
        follow_up_days=3,
        rating=5,
        notes=[(50, "Strong bio scores. Wants govt college first, private as backup.")],
    ),
    dict(
        token="PCM-02",
        name="Priya Nair",
        school="Carmel Convent, Gwalior",
        mobile="9000010002",
        parent_mobile="9000020002",
        email="priya.nair@example.com",
        stream="PCM",
        klass="Class 12",
        counsellor="Meera Iyer",
        status=StudentStatus.IN_SESSION,
        consent=Consent.GIVEN,
        checkin=38,
        called=12,
        started=11,
        course="B.Tech Computer Science",
        exams=["JEE", "CUET"],
        clarity="Need help shortlisting",
        help=["College selection", "College & course comparison"],
        home_city="Gwalior",
        target_exam="JEE Main",
        budget="4-8 L",
    ),
    dict(
        token="PCM-03",
        name="Sahil Yadav",
        school="Kendriya Vidyalaya No.1",
        mobile="9000010003",
        parent_mobile="9000020003",
        email="sahil.y@example.com",
        stream="PCM",
        klass="Dropper / repeat year",
        counsellor="Meera Iyer",
        status=StudentStatus.WAITING,
        consent=Consent.GIVEN,
        checkin=31,
        course="B.Tech Mechanical",
        exams=["JEE"],
        clarity="Completely confused",
        help=["Course selection", "Entrance exams"],
    ),
    dict(
        token="PCB-04",
        name="Fatima Sheikh",
        school="St. Paul's School",
        mobile="9000010004",
        parent_mobile="9000020004",
        email="fatima.s@example.com",
        stream="PCB",
        klass="Class 11",
        counsellor="Rahul Verma",
        status=StudentStatus.WAITING,
        consent=Consent.PENDING,
        checkin=27,
        source=Source.DESK,
        course="BDS or BSc Nursing",
        exams=["NEET"],
        clarity="Completely confused",
        help=["Course selection", "Admission / counselling"],
    ),
    dict(
        token="COM-05",
        name="Devansh Gupta",
        school="Scindia Kanya Vidyalaya",
        mobile="9000010005",
        parent_mobile="9000020005",
        email="devansh@example.com",
        stream="COM",
        klass="Graduate",
        counsellor="Aditi Sharma",
        status=StudentStatus.WAITING,
        consent=Consent.GIVEN,
        checkin=24,
        course="BBA then MBA",
        exams=["CUET"],
        clarity="Very clear",
        help=["College selection"],
    ),
    dict(
        token="PCM-06",
        name="Ritika Bose",
        school="Delhi Public School, Gwalior",
        mobile="9000010006",
        parent_mobile="9000020006",
        email="ritika.b@example.com",
        stream="PCM",
        klass="Class 12",
        counsellor="Meera Iyer",
        status=StudentStatus.WAITING,
        consent=Consent.GIVEN,
        checkin=19,
        course="B.Tech Electronics",
        exams=["JEE", "CUET"],
        clarity="Have shortlisted options",
        help=["Cut-offs & college chances"],
    ),
    # Prototype has recalls:1 with no_show; with recall_limit 2 a no-show has used both calls (CQ-46).
    dict(
        token="PCB-07",
        name="Karan Singh",
        school="Gyan Ganga Vidyalaya",
        mobile="9000010007",
        parent_mobile="9000020007",
        email="karan.s@example.com",
        stream="PCB",
        klass="Class 12",
        counsellor="Rahul Verma",
        status=StudentStatus.NO_SHOW,
        consent=Consent.GIVEN,
        checkin=45,
        called=20,
        recalls=2,
        course="MBBS",
        exams=["NEET"],
        clarity="Need help shortlisting",
        help=["Admission / counselling"],
    ),
    dict(
        token="HUM-08",
        name="Sneha Kulkarni",
        school="Little Angels HS School",
        mobile="9000010008",
        parent_mobile="9000020008",
        email="sneha.k@example.com",
        stream="HUM",
        klass="Class 12",
        counsellor="Aditi Sharma",
        status=StudentStatus.WAITING,
        consent=Consent.GIVEN,
        checkin=9,
        course="BA LLB",
        exams=["CLAT", "CUET"],
        clarity="Have shortlisted options",
        help=["College selection", "Entrance exams"],
    ),
    # Desk check-in, manually placed with Meera by reception (as in the prototype); no goals captured.
    dict(
        token="HUM-09",
        name="Mohit Raj",
        school="Bal Bharti, Gwalior",
        mobile="9000010009",
        parent_mobile="9000020009",
        email="mohit.raj@example.com",
        stream="HUM",
        klass="Class 12",
        counsellor="Meera Iyer",
        status=StudentStatus.WAITING,
        consent=Consent.PENDING,
        checkin=4,
        source=Source.DESK,
    ),
]
GWALIOR_LAST_TOKEN = 9

STUDENT_FIELDS = (
    "name",
    "school",
    "mobile",
    "parent_mobile",
    "email",
    "stream",
    "klass",
    "course",
    "exams",
    "clarity",
    "help",
    "home_city",
    "target_exam",
    "budget",
    "colleges_discussed",
    "outcome",
    "rating",
    "recalls",
)


class Command(BaseCommand):
    help = "Seed the prototype's Gwalior (live) / Indore / Jaipur demo data and staff users. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo centres' students and reseed them relative to now.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        centres = self._centres(today)
        counsellors = self._counsellors(centres)
        users = self._users(centres, counsellors)
        gwalior = centres["gwalior-demo"]
        if options["reset"]:
            Student.objects.filter(centre__in=centres.values()).delete()
            AuditEvent.objects.filter(centre__in=centres.values()).delete()
        created = self._students(gwalior, counsellors, users["reception@careers360.com"], today)
        seq = TokenSequence.objects.select_for_update().get(centre=gwalior)
        if seq.last_number < GWALIOR_LAST_TOKEN:  # never move a sequence backwards
            seq.last_number = GWALIOR_LAST_TOKEN
            seq.save(update_fields=["last_number"])
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo: {len(centres)} centres, {len(counsellors)} counsellors, {len(users)} users, "
                f"{created} new students."
            )
        )

    # --- centres ----------------------------------------------------------
    def _centres(self, today: dt.date) -> dict[str, Centre]:
        out = {}
        for slug, city, venue, days, opens, closes, expected, status in CENTRES:
            centre, _ = Centre.objects.update_or_create(
                slug=slug,
                defaults=dict(
                    city=city,
                    venue=venue,
                    date=today + dt.timedelta(days=days),
                    opens_at=opens,
                    closes_at=closes,
                    expected_students=expected,
                    status=status,
                    front_desk_phone=FRONT_DESK_PHONE,
                ),
            )
            if (
                status == CentreStatus.LIVE
                and not AuditEvent.objects.filter(
                    centre=centre, student=None, verb=AuditEvent.Verb.CENTRE_LIVE
                ).exists()
            ):
                AuditEvent.objects.create(
                    centre=centre, verb=AuditEvent.Verb.CENTRE_LIVE, data={"seed": True}
                )
            out[slug] = centre
        return out

    # --- counsellors + postings ---------------------------------------------
    def _counsellors(self, centres: dict[str, Centre]) -> dict[str, Counsellor]:
        out = {}
        for _email, name, mobile, desk, streams, slug, duty, expected in COUNSELLORS:
            counsellor, _ = Counsellor.objects.update_or_create(
                mobile=mobile, defaults=dict(name=name, streams=streams, expected_session_min=expected)
            )
            Posting.objects.update_or_create(
                counsellor=counsellor, centre=centres[slug], defaults=dict(desk_label=desk, duty=duty)
            )
            out[name] = counsellor
        return out

    # --- staff users --------------------------------------------------------
    def _password(self, admin: bool) -> str | None:
        if settings.DEBUG:
            return "admin123" if admin else "desk123"
        return (settings.SEED_ADMIN_PASSWORD if admin else settings.SEED_STAFF_PASSWORD) or None

    def _user(self, email: str, admin: bool = False, **fields) -> StaffUser:
        user, _ = StaffUser.objects.update_or_create(email=email, defaults=fields)
        password = self._password(admin)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(update_fields=["password"])
        return user

    def _users(self, centres: dict[str, Centre], counsellors: dict[str, Counsellor]) -> dict[str, StaffUser]:
        gwalior = centres["gwalior-demo"]
        users = {
            "admin@careers360.com": self._user(
                "admin@careers360.com",
                admin=True,
                name="Nikhil Bhatia",
                role=Role.OPS_LEAD,
                title="Head of counselling operations",
                is_staff=True,
                is_superuser=True,
            ),
            "reception@careers360.com": self._user(
                "reception@careers360.com",
                name="Pooja Menon",
                role=Role.RECEPTION,
                centre=gwalior,
                title="Front desk, Gwalior",
            ),
        }
        for email, name, _mobile, desk, _streams, slug, _duty, _exp in COUNSELLORS:
            users[email] = self._user(
                email,
                name=name,
                role=Role.COUNSELLOR,
                counsellor=counsellors[name],
                title=f"{desk}, {centres[slug].city}",
            )
        return users

    # --- students -------------------------------------------------------------
    def _students(
        self, centre: Centre, counsellors: dict[str, Counsellor], reception: StaffUser, today: dt.date
    ) -> int:
        now = timezone.now()
        created = 0
        for spec in STUDENTS:
            if Student.objects.filter(centre=centre, token=spec["token"]).exists():
                continue
            self._create_student(centre, counsellors, reception, today, now, spec)
            created += 1
        return created

    def _create_student(self, centre, counsellors, reception, today, now, spec):
        def ago(key):
            return now - spec[key] * MIN if spec.get(key) is not None else None

        counsellor = counsellors[spec["counsellor"]]
        source = spec.get("source", Source.SELF)
        checkin_at = ago("checkin")
        fields = {k: spec[k] for k in STUDENT_FIELDS if k in spec}
        student = Student.objects.create(
            token=spec["token"],
            centre=centre,
            counsellor=counsellor,
            source=source,
            status=spec["status"],
            consent=spec["consent"],
            consent_at=checkin_at if spec["consent"] == Consent.GIVEN else None,
            checkin_at=checkin_at,
            queue_at=checkin_at,
            called_at=ago("called"),
            started_at=ago("started"),
            ended_at=ago("ended"),
            follow_up_on=today + dt.timedelta(days=spec["follow_up_days"])
            if "follow_up_days" in spec
            else None,
            **fields,
        )

        def audit(verb, at, actor=None, **data):
            AuditEvent.objects.create(
                student=student, centre=centre, verb=verb, at=at, actor=actor, data=data
            )

        audit(
            AuditEvent.Verb.CHECKED_IN,
            checkin_at,
            actor=reception if source == Source.DESK else None,
            token=student.token,
            source=source,
        )
        if student.called_at:
            audit(AuditEvent.Verb.CALLED, student.called_at, counsellor_id=counsellor.id)
        if student.started_at:
            audit(AuditEvent.Verb.STARTED, student.started_at)
        if student.status == StudentStatus.NO_SHOW:
            audit(AuditEvent.Verb.NO_SHOW, student.called_at + 3 * MIN, recalls=student.recalls)
        if student.ended_at:
            SessionRecord.objects.create(
                student=student,
                counsellor=counsellor,
                centre=centre,
                called_at=student.called_at,
                started_at=student.started_at,
                ended_at=student.ended_at,
                outcome=student.outcome,
            )
            audit(AuditEvent.Verb.COMPLETED, student.ended_at)
        if student.rating:
            audit(AuditEvent.Verb.RATED, student.ended_at + MIN, rating=student.rating)
        for minutes_ago, text in spec.get("notes", []):
            note = Note.objects.create(
                student=student,
                text=text,
                author_name=counsellor.name,
                author=counsellor,
                created_at=now - minutes_ago * MIN,
            )
            audit(AuditEvent.Verb.NOTED, note.created_at, note_id=note.id)
