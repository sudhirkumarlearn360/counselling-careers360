"""Counsellor and roster writes (CQ-9/11/37)."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.centres.exceptions import CentreClosed
from apps.centres.models import Centre, CentreStatus
from apps.common.choices import Stream
from apps.common.validators import normalise_mobile, valid_mobile
from apps.common.warnings import warning
from apps.counsellors.exceptions import AlreadyPosted, CounsellorInvalid, DeskClash, NoLivePosting
from apps.counsellors.models import Counsellor, Duty, Posting
from apps.queue.models import AuditEvent

NAME_STREAM_MSG = "A name and at least one stream are needed."
MOBILE_MSG = "A 10-digit mobile number is needed."
DUTY_MSG = "Duty must be on_desk, on_break or off_duty."


def _validate_counsellor(name, mobile, streams, expected_session_min) -> None:
    ok_streams = (
        isinstance(streams, list)
        and len(streams) >= 1
        and all(isinstance(s, str) and s in Stream.values for s in streams)
    )
    if not (name or "").strip() or not ok_streams:
        raise CounsellorInvalid(NAME_STREAM_MSG, data={"fields": {"name": [NAME_STREAM_MSG]}})
    if not valid_mobile(mobile):
        raise CounsellorInvalid(MOBILE_MSG, data={"fields": {"mobile": [MOBILE_MSG]}})
    if expected_session_min is not None and expected_session_min < 1:
        raise CounsellorInvalid("Expected session length must be at least 1 minute.")


def _clean_streams(streams):
    if not isinstance(streams, list):
        return streams
    return [s for s in Stream.values if s in streams] if all(s in Stream.values for s in streams) else streams


@transaction.atomic
def create_counsellor(values: dict, actor=None):
    """Creates the counsellor and, when `centre_id` + `desk_label` are given, their first posting."""
    name = (values.get("name") or "").strip()
    streams = values.get("streams")
    esm = values.get("expected_session_min")
    _validate_counsellor(name, values.get("mobile"), streams, esm)
    centre_id, desk = values.get("centre_id"), (values.get("desk_label") or "").strip()
    if (centre_id or desk) and not (centre_id and desk):
        raise CounsellorInvalid("A centre and a desk label are both needed to post a counsellor.")
    counsellor = Counsellor.objects.create(
        name=name,
        mobile=normalise_mobile(values["mobile"]),
        streams=_clean_streams(streams),
        **({"expected_session_min": esm} if esm else {}),
    )
    warnings = []
    if centre_id:
        _, warnings = create_posting(counsellor, centre_id, desk, actor)
    return counsellor, warnings


@transaction.atomic
def update_counsellor(counsellor: Counsellor, values: dict, actor=None) -> Counsellor:
    locked = Counsellor.objects.select_for_update().get(pk=counsellor.pk)
    merged = {
        "name": values.get("name", locked.name),
        "mobile": values.get("mobile", locked.mobile),
        "streams": values.get("streams", locked.streams),
        "expected_session_min": values.get("expected_session_min", locked.expected_session_min),
    }
    _validate_counsellor(merged["name"], merged["mobile"], merged["streams"], merged["expected_session_min"])
    locked.name = merged["name"].strip()
    locked.mobile = normalise_mobile(merged["mobile"])
    locked.streams = _clean_streams(merged["streams"])
    locked.expected_session_min = merged["expected_session_min"]
    locked.save()
    return locked


def _lock_centre(centre_id) -> Centre:
    """Serialises roster changes per centre so the desk-clash check cannot race."""
    centre = Centre.objects.select_for_update().filter(pk=centre_id).first()
    if centre is None:
        raise CounsellorInvalid("Choose a centre for this posting.")
    if centre.status == CentreStatus.CLOSED:
        raise CentreClosed("That centre has closed — a counsellor can't be posted to it.")
    return centre


def _check_desk(centre: Centre, desk: str, exclude_pk=None) -> None:
    clash = Posting.objects.select_related("counsellor").filter(centre=centre, desk_label__iexact=desk)
    if exclude_pk:
        clash = clash.exclude(pk=exclude_pk)
    hit = clash.first()
    if hit:
        raise DeskClash(f"{hit.desk_label} is already taken by {hit.counsellor.name} at this centre.")


def _roster_warnings(counsellor: Counsellor, centre: Centre, exclude_pk=None) -> list:
    others = Posting.objects.select_related("centre").filter(counsellor=counsellor, centre__date=centre.date)
    others = others.exclude(centre=centre)
    if exclude_pk:
        others = others.exclude(pk=exclude_pk)
    return [
        warning(
            "roster_conflict",
            f"{counsellor.name} is already posted to {p.centre.city} on {p.centre.date.isoformat()}.",
        )
        for p in others.order_by("id")
    ]


@transaction.atomic
def create_posting(counsellor: Counsellor, centre_id, desk_label: str, actor=None):
    """A new posting starts off duty. Same-date postings elsewhere only warn (CQ-11)."""
    desk = (desk_label or "").strip()
    if not desk:
        raise CounsellorInvalid(
            "A desk label is needed.", data={"fields": {"desk_label": ["A desk label is needed."]}}
        )
    centre = _lock_centre(centre_id)
    if Posting.objects.filter(counsellor=counsellor, centre=centre).exists():
        raise AlreadyPosted(f"{counsellor.name} is already posted to this centre.")
    _check_desk(centre, desk)
    posting = Posting.objects.create(
        counsellor=counsellor, centre=centre, desk_label=desk, duty=Duty.OFF_DUTY
    )
    return posting, _roster_warnings(counsellor, centre)


@transaction.atomic
def update_posting(posting: Posting, values: dict, actor=None):
    """Move to another centre and/or change the desk label. Duty is changed only by `set_duty`."""
    locked = Posting.objects.select_for_update().select_related("counsellor", "centre").get(pk=posting.pk)
    centre_id = values.get("centre_id", locked.centre_id)
    desk = (values.get("desk_label", locked.desk_label) or "").strip()
    if not desk:
        raise CounsellorInvalid(
            "A desk label is needed.", data={"fields": {"desk_label": ["A desk label is needed."]}}
        )
    moved = centre_id != locked.centre_id
    centre = _lock_centre(centre_id) if moved else locked.centre
    if moved and Posting.objects.filter(counsellor=locked.counsellor, centre=centre).exists():
        raise AlreadyPosted(f"{locked.counsellor.name} is already posted to this centre.")
    _check_desk(centre, desk, exclude_pk=locked.pk)
    locked.centre, locked.desk_label = centre, desk
    locked.save(update_fields=["centre", "desk_label", "updated_at"])
    warnings = _roster_warnings(locked.counsellor, centre, exclude_pk=locked.pk) if moved else []
    return locked, warnings


def current_live_posting(counsellor: Counsellor):
    return (
        Posting.objects.filter(
            counsellor=counsellor, centre__status=CentreStatus.LIVE, centre__date=timezone.localdate()
        )
        .order_by("centre__opens_at", "id")
        .first()
    )


@transaction.atomic
def set_duty(posting: Posting, duty: str, actor=None, on_behalf_of=None) -> Posting:
    """State store for CQ-37. Never moves or re-orders existing students."""
    if duty not in Duty.values:
        raise CounsellorInvalid(DUTY_MSG)
    locked = Posting.objects.select_for_update().get(pk=posting.pk)
    before = locked.duty
    if before != duty:
        locked.duty = duty
        locked.save(update_fields=["duty", "updated_at"])
        AuditEvent.objects.create(
            centre_id=locked.centre_id,
            verb=AuditEvent.Verb.EDITED,
            actor=actor,
            on_behalf_of=on_behalf_of,
            data={"posting_id": locked.id, "duty": duty, "from": before},
        )
    return locked


def set_own_duty(counsellor: Counsellor, duty: str, actor=None, on_behalf_of=None) -> Posting:
    posting = current_live_posting(counsellor)
    if posting is None:
        raise NoLivePosting()
    return set_duty(posting, duty, actor, on_behalf_of)
