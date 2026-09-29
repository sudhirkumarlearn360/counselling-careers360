"""Counsellor assignment at check-in (CQ-19, CQ-37). Strict stream routing, no silent fallback."""

from __future__ import annotations

import re
from collections import Counter

from apps.counsellors.models import Duty, Posting
from apps.queue.exceptions import NoCounsellorForStream, NoCounsellorOnDuty
from apps.queue.models import ACTIVE_STATUSES, Student, StudentStatus
from apps.queue.services.eta import avg_session


def desk_sort_key(label: str):
    """Natural order, so "Desk 2" sorts before "Desk 10"."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", label)]


def loads(centre, counsellor_ids) -> Counter:
    """load = waiting count + 1 if the counsellor has a called or in-session student."""
    load = Counter()
    rows = Student.objects.filter(
        centre_id=centre.pk,
        counsellor_id__in=counsellor_ids,
        status__in=[StudentStatus.WAITING, *ACTIVE_STATUSES],
    ).values_list("counsellor_id", "status")
    active = set()
    for counsellor_id, status in rows:
        if status == StudentStatus.WAITING:
            load[counsellor_id] += 1
        else:
            active.add(counsellor_id)
    for counsellor_id in active:
        load[counsellor_id] += 1
    return load


def assign_counsellor(centre, stream: str) -> Posting:
    """Pick the on-desk posting at the centre whose counsellor covers `stream`.

    Order: lowest load, then lowest average session, then desk label. The on-desk postings are
    locked (by id) so a concurrent duty change cannot slip between the choice and the insert. Returns
    the Posting (its counsellor and desk label go on the token).
    """
    on_desk = list(
        Posting.objects.select_for_update(of=("self",))
        .select_related("counsellor")
        .filter(centre_id=centre.pk, duty=Duty.ON_DESK)
        .order_by("id")
    )
    if not on_desk:
        raise NoCounsellorOnDuty()
    candidates = [p for p in on_desk if p.counsellor.covers(stream)]
    if not candidates:
        raise NoCounsellorForStream()
    load = loads(centre, [p.counsellor_id for p in candidates])
    return min(
        candidates,
        key=lambda p: (
            load[p.counsellor_id],
            avg_session(p.counsellor, centre),
            desk_sort_key(p.desk_label),
            p.id,
        ),
    )
