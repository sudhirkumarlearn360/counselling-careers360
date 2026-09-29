"""Row locks for the queue engine, in the one fixed order that avoids deadlocks.

    1. TokenSequence for the centre   (check-in, close, and anything that can put a student back in a queue)
    2. Postings, ordered by id         (desk-level decisions: assignment, busy desk, move, pull-forward)
    3. Students                        (the rows whose status is decided)

Every decision read after a lock is a locking read (`select_for_update`), which in InnoDB is a *current*
read: it sees the latest committed row, not the transaction's snapshot. The one plain read that decides
anything is the centre status after lock 1 (see `centre_status`).
"""

from __future__ import annotations

from apps.centres.models import Centre
from apps.counsellors.models import Posting
from apps.queue.exceptions import NotPostedHere
from apps.queue.models import Student, TokenSequence


def lock_sequence(centre_id) -> TokenSequence:
    return TokenSequence.objects.select_for_update().get(centre_id=centre_id)


def centre_status(centre_id) -> str:
    """The centre status, read after `lock_sequence`.

    `close_centre` changes the status while holding the TokenSequence lock, and the lock is the first
    statement of every caller's transaction, so this plain read opens its snapshot after any close
    has committed. Callers must not run nested inside a transaction that already read (no
    ATOMIC_REQUESTS).
    """
    return Centre.objects.filter(pk=centre_id).values_list("status", flat=True).get()


def lock_postings(centre_id, counsellor_ids) -> dict:
    """Lock the postings of these counsellors at the centre (by id). Returns {counsellor_id: Posting}."""
    rows = (
        Posting.objects.select_for_update(of=("self",))
        .select_related("counsellor")
        .filter(centre_id=centre_id, counsellor_id__in=set(counsellor_ids))
        .order_by("id")
    )
    return {p.counsellor_id: p for p in rows}


def lock_desk(centre_id, counsellor) -> Posting:
    posting = lock_postings(centre_id, [counsellor.id]).get(counsellor.id)
    if posting is None:
        raise NotPostedHere(f"{counsellor.name} isn't posted to this centre.")
    return posting


def lock_student(student_id) -> Student:
    return (
        Student.objects.select_for_update(of=("self",))
        .select_related("centre", "centre__settings", "counsellor")
        .get(pk=student_id)
    )
