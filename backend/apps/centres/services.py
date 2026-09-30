"""Centre writes (CQ-6/7/8/10). Closing delegates to `apps.queue.services.close_centre`."""

from __future__ import annotations

from django.db import transaction

from apps.accounts.models import Role, StaffUser, normalise_email
from apps.centres.exceptions import CentreClosed, CentreInvalid, CentreNotLive, CentreNotPlanned
from apps.centres.models import Centre, CentreStatus
from apps.common.choices import Stream
from apps.common.exceptions import NeedsConfirmation
from apps.common.validators import valid_email
from apps.common.warnings import warning
from apps.queue.models import AuditEvent, Student, StudentStatus
from apps.queue.services import close_centre

FIELDS = ("city", "venue", "date", "opens_at", "closes_at", "expected_students", "front_desk_phone")
REQUIRED_MSG = "City and venue are both needed."
TIME_MSG = "Closing time must be later than opening time."
MISSING_MSG = "Date, opening time, closing time and expected students are all needed."
STREAM_LABELS = dict(Stream.choices)


def _validate(values: dict) -> None:
    if not (values.get("city") or "").strip() or not (values.get("venue") or "").strip():
        raise CentreInvalid(REQUIRED_MSG, data={"fields": {"city": [REQUIRED_MSG], "venue": [REQUIRED_MSG]}})
    for f in ("date", "opens_at", "closes_at", "expected_students"):
        if values.get(f) is None:
            raise CentreInvalid(MISSING_MSG, data={"fields": {f: [MISSING_MSG]}})
    if values["closes_at"] <= values["opens_at"]:
        raise CentreInvalid(TIME_MSG, data={"fields": {"closes_at": [TIME_MSG]}})


EMAIL_MSG = "Enter the front desk's email address."
EMAIL_TAKEN_MSG = "That email already has an account."
PASSWORD_MSG = "The password must be at least 8 characters."
MIN_PASSWORD = 8


def _validate_login(email, password, required: bool, exclude_user=None) -> None:
    """The centre's front-desk login (Add a Centre). Both are needed to create; on edit each is optional."""
    email, password = (email or "").strip(), password or ""
    errors = {}
    if required or email:
        if not valid_email(email):
            errors["email"] = [EMAIL_MSG]
        elif (
            StaffUser.objects.filter(email=normalise_email(email))
            .exclude(pk=getattr(exclude_user, "pk", None))
            .exists()
        ):
            errors["email"] = [EMAIL_TAKEN_MSG]
    if (required or password) and len(password) < MIN_PASSWORD:
        errors["password"] = [PASSWORD_MSG]
    if errors:
        raise CentreInvalid(next(iter(errors.values()))[0], data={"fields": errors})


def front_desk_user(centre: Centre):
    return StaffUser.objects.filter(role=Role.RECEPTION, centre=centre).order_by("id").first()


def duplicate_warnings(city: str, date, exclude_pk=None) -> list:
    dupes = Centre.objects.filter(city__iexact=city, date=date)
    if exclude_pk:
        dupes = dupes.exclude(pk=exclude_pk)
    if not dupes.exists():
        return []
    return [
        warning(
            "duplicate_centre",
            f"A centre in {city} on {date.isoformat()} already exists — you can still save.",
        )
    ]


@transaction.atomic
def create_centre(values: dict, actor=None):
    values = {
        **values,
        "city": (values.get("city") or "").strip(),
        "venue": (values.get("venue") or "").strip(),
    }
    _validate(values)
    _validate_login(values.get("email"), values.get("password"), required=True)
    warnings = duplicate_warnings(values["city"], values["date"])
    centre = Centre.objects.create(
        **{k: v for k, v in values.items() if k in FIELDS}, status=CentreStatus.PLANNED
    )
    StaffUser.objects.create_user(
        values["email"],
        values["password"],
        name=f"{centre.city} front desk",
        role=Role.RECEPTION,
        centre=centre,
    )
    return centre, warnings


@transaction.atomic
def update_centre(centre: Centre, values: dict, actor=None):
    """Edits fields only: tokens, queue order, postings and the slug are never touched (CQ-7)."""
    locked = Centre.objects.select_for_update().get(pk=centre.pk)
    if locked.status == CentreStatus.CLOSED:
        raise CentreClosed()
    merged = {f: getattr(locked, f) for f in FIELDS}
    merged.update({k: v for k, v in values.items() if k in FIELDS})
    merged["city"], merged["venue"] = (merged["city"] or "").strip(), (merged["venue"] or "").strip()
    _validate(merged)
    desk = front_desk_user(locked)
    _validate_login(values.get("email"), values.get("password"), required=False, exclude_user=desk)
    warnings = []
    if (merged["city"].lower(), merged["date"]) != (locked.city.lower(), locked.date):
        warnings = duplicate_warnings(merged["city"], merged["date"], exclude_pk=locked.pk)
    changed = [f for f in FIELDS if getattr(locked, f) != merged[f]]
    for f in changed:
        setattr(locked, f, merged[f])
    if changed:
        locked.save(update_fields=[*changed, "updated_at"])
        AuditEvent.objects.create(
            centre=locked, verb=AuditEvent.Verb.EDITED, actor=actor, data={"fields": changed}
        )
    if values.get("email") or values.get("password"):  # change the front-desk login
        if desk is None:
            desk = StaffUser(name=f"{locked.city} front desk", role=Role.RECEPTION, centre=locked)
        if values.get("email"):
            desk.email = normalise_email(values["email"])
        if values.get("password"):
            desk.set_password(values["password"])
        desk.save()
        AuditEvent.objects.create(
            centre=locked, verb=AuditEvent.Verb.EDITED, actor=actor, data={"fields": ["front_desk_login"]}
        )
    return locked, warnings


def uncovered_streams(centre: Centre) -> list:
    covered = set()
    for p in centre.postings.select_related("counsellor"):
        covered.update(p.counsellor.streams or [])
    return [s for s in Stream.values if s not in covered]


def uncovered_message(streams: list) -> str:
    return f"No counsellor covers {', '.join(STREAM_LABELS[s] for s in streams)}. Go live anyway?"


@transaction.atomic
def go_live(centre: Centre, actor, confirm: bool = False) -> Centre:
    locked = Centre.objects.select_for_update().get(pk=centre.pk)
    if locked.status != CentreStatus.PLANNED:
        raise CentreNotPlanned()
    missing = uncovered_streams(locked)
    if missing and not confirm:
        raise NeedsConfirmation(uncovered_message(missing), data={"uncovered_streams": missing})
    locked.status = CentreStatus.LIVE
    locked.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        centre=locked, verb=AuditEvent.Verb.CENTRE_LIVE, actor=actor, data={"uncovered_streams": missing}
    )
    return locked


def waiting_count(centre: Centre) -> int:
    return Student.objects.filter(centre=centre, status=StudentStatus.WAITING).count()


def close_preview(centre: Centre) -> dict:
    n = waiting_count(centre)
    return {
        "waiting_count": n,
        "message": f"{n} students are still waiting. They'll be marked not counselled.",
    }


def close(centre: Centre, actor, confirm: bool) -> dict:
    if centre.status != CentreStatus.LIVE:
        raise CentreNotLive()
    if not confirm:
        preview = close_preview(centre)
        raise NeedsConfirmation(preview["message"], data={"waiting_count": preview["waiting_count"]})
    n = close_centre(centre, actor)
    return {"status": CentreStatus.CLOSED, "not_counselled": n}
