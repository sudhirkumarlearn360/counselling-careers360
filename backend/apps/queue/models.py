from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.choices import Clarity, Klass, Outcome, Stream
from apps.queue.keys import make_access_key


class StudentStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    CALLED = "called", "Called"
    IN_SESSION = "in_session", "In session"
    DONE = "done", "Done"
    NO_SHOW = "no_show", "No-show"
    RELEASED = "released", "Released"
    NOT_COUNSELLED = "not_counselled", "Not counselled"


OPEN_STATUSES = (StudentStatus.WAITING, StudentStatus.CALLED, StudentStatus.IN_SESSION)
ACTIVE_STATUSES = (StudentStatus.CALLED, StudentStatus.IN_SESSION)


class Source(models.TextChoices):
    SELF = "self", "Self check-in"
    DESK = "desk", "Front desk"


class Consent(models.TextChoices):
    GIVEN = "given", "Given"
    PENDING = "pending", "Pending"


class TokenSequence(models.Model):
    """One per centre, created with the Centre, shared across streams. Never goes back (CQ-19)."""

    centre = models.OneToOneField("centres.Centre", on_delete=models.PROTECT, related_name="token_sequence")
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.centre}: {self.last_number}"


class Student(models.Model):
    """One row per token. Status changes only through apps.queue.services."""

    token = models.CharField(max_length=16)
    centre = models.ForeignKey("centres.Centre", on_delete=models.PROTECT, related_name="students")
    counsellor = models.ForeignKey(
        "counsellors.Counsellor", on_delete=models.PROTECT, related_name="students"
    )
    source = models.CharField(max_length=4, choices=Source.choices, default=Source.SELF)
    status = models.CharField(max_length=16, choices=StudentStatus.choices, default=StudentStatus.WAITING)

    # Details (CQ-15)
    name = models.CharField(max_length=120)
    school = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=10)  # normalised, 10 digits
    parent_mobile = models.CharField(max_length=10, blank=True)
    email = models.EmailField(blank=True)
    stream = models.CharField(max_length=4, choices=Stream.choices)
    klass = models.CharField(max_length=24, choices=Klass.choices, blank=True)

    # Goals (CQ-16)
    course = models.CharField(max_length=200, blank=True)
    exams = models.JSONField(default=list, blank=True)
    clarity = models.CharField(max_length=32, choices=Clarity.choices, blank=True)
    help = models.JSONField(default=list, blank=True)

    # Consent (CQ-17/24/42). consent_by null = the student themself.
    consent = models.CharField(max_length=8, choices=Consent.choices, default=Consent.PENDING)
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_by = models.ForeignKey(
        "counsellors.Counsellor", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    # Queue timing (current/latest visit)
    checkin_at = models.DateTimeField(default=timezone.now)
    queue_at = models.DateTimeField(default=timezone.now)  # ordering key; reset on rejoin/miss
    priority = models.IntegerField(default=0)  # pull-forward, per desk
    called_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    recalls = models.PositiveSmallIntegerField(default=0)

    # Session results (CQ-28/44/48)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=12, choices=Outcome.choices, null=True, blank=True)
    follow_up_on = models.DateField(null=True, blank=True)
    colleges_discussed = models.TextField(blank=True)
    home_city = models.CharField(max_length=100, blank=True)
    target_exam = models.CharField(max_length=100, blank=True)
    budget = models.CharField(max_length=60, blank=True)
    accompanied_by = models.CharField(max_length=100, blank=True)

    # Signed with SECRET_KEY: rotating the key invalidates live token links (see SCHEMA.md).
    access_key = models.CharField(
        max_length=100, unique=True, default=make_access_key, editable=False, db_collation="utf8mb4_bin"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checkin_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "token"], name="student_unique_token_per_centre"),
            models.CheckConstraint(
                check=models.Q(rating__isnull=True) | models.Q(rating__gte=1, rating__lte=5),
                name="student_rating_1_to_5",
            ),
        ]
        indexes = [
            models.Index(fields=["centre", "status"]),
            models.Index(fields=["centre", "mobile"]),
            models.Index(fields=["counsellor", "status", "queue_at"]),
            models.Index(fields=["centre", "checkin_at"]),  # CQ-59 list filtered by centre
            models.Index(fields=["checkin_at"]),  # CQ-59 all-centres list, newest first
        ]

    def __str__(self):
        return f"{self.token} {self.name}"


class SessionRecord(models.Model):
    """One row per complete_session, so a requeued student keeps earlier sessions (CQ-21/38/60/61)."""

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="session_records")
    counsellor = models.ForeignKey(
        "counsellors.Counsellor", on_delete=models.PROTECT, related_name="session_records"
    )
    centre = models.ForeignKey("centres.Centre", on_delete=models.PROTECT, related_name="session_records")
    # Snapshots taken at completion; later edits to the Student do not change them.
    queue_at = models.DateTimeField()  # the visit's queue start, for wait = called_at - queue_at
    called_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    outcome = models.CharField(max_length=12, choices=Outcome.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ended_at", "id"]
        indexes = [models.Index(fields=["centre", "counsellor", "ended_at"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(ended_at__gte=models.F("started_at")), name="sessionrecord_ends_after_start"
            ),
        ]

    def __str__(self):
        return f"{self.student} with {self.counsellor}"


class Note(models.Model):
    """Counsellor notes. No delete (CQ-45)."""

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="notes")
    text = models.TextField()
    author_name = models.CharField(max_length=120)
    author = models.ForeignKey(
        "counsellors.Counsellor", null=True, blank=True, on_delete=models.PROTECT, related_name="notes"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(check=~models.Q(text=""), name="note_text_not_empty")]

    def __str__(self):
        return f"Note on {self.student} by {self.author_name}"


class AuditEvent(models.Model):
    class Verb(models.TextChoices):
        CHECKED_IN = "checked_in"
        CALLED = "called"
        STARTED = "started"
        COMPLETED = "completed"
        MISSED = "missed"
        NO_SHOW = "no_show"
        RELEASED = "released"
        REQUEUED = "requeued"
        MOVED = "moved"
        PULLED_FORWARD = "pulled_forward"
        CONSENT_GIVEN = "consent_given"
        EDITED = "edited"
        NOTED = "noted"
        RATED = "rated"
        MESSAGE_FAILED = "message_failed"
        CENTRE_LIVE = "centre_live"
        CENTRE_CLOSED = "centre_closed"
        EXPORTED = "exported"

    student = models.ForeignKey(
        Student, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events"
    )  # null = centre-level event
    centre = models.ForeignKey("centres.Centre", on_delete=models.PROTECT, related_name="audit_events")
    verb = models.CharField(max_length=20, choices=Verb.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )  # null = the student
    on_behalf_of = models.ForeignKey(
        "counsellors.Counsellor", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )  # set when an ops lead works a desk (CQ-5)
    at = models.DateTimeField(default=timezone.now)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["centre", "at"]), models.Index(fields=["student", "at"])]

    def __str__(self):
        return f"{self.verb} {self.student_id or self.centre_id} at {self.at:%H:%M}"
