"""Consent (CQ-17, CQ-24, CQ-42): the student's own confirmation, or verbal consent taken by a counsellor."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.queue.exceptions import InvalidTransition
from apps.queue.models import OPEN_STATUSES, AuditEvent, Consent
from apps.queue.services.audit import record
from apps.queue.services.locks import lock_sequence, lock_student


@transaction.atomic
def record_consent(student, by=None, actor=None, on_behalf_of=None):
    """Mark consent given. `by` is the counsellor who took it verbally; None = the student themself.

    Idempotent: a student whose consent is already given is returned unchanged (no second audit row).
    """
    lock_sequence(student.centre_id)
    s = lock_student(student.pk)
    if s.status not in OPEN_STATUSES:
        raise InvalidTransition(f"Token {s.token} is no longer in the queue.")
    if s.consent == Consent.GIVEN:
        return s
    s.consent = Consent.GIVEN
    s.consent_at = timezone.now()
    s.consent_by = by
    s.save(update_fields=["consent", "consent_at", "consent_by", "updated_at"])
    data = {"by_counsellor_id": by.id} if by is not None else {}
    record(s, AuditEvent.Verb.CONSENT_GIVEN, actor, on_behalf_of, **data)
    return s
