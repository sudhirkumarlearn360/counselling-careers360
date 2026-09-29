"""Centre writes (CQ-6/7/8/10). Closing delegates to `apps.queue.services.close_centre`."""

from __future__ import annotations

from django.db import transaction

from apps.centres.exceptions import CentreClosed, CentreInvalid, CentreNotLive, CentreNotPlanned
from apps.centres.models import Centre, CentreStatus
from apps.common.choices import Stream
from apps.common.exceptions import NeedsConfirmation
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
    warnings = duplicate_warnings(values["city"], values["date"])
    centre = Centre.objects.create(
        **{k: v for k, v in values.items() if k in FIELDS}, status=CentreStatus.PLANNED
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
