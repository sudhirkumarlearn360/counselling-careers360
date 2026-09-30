"""The one way queue services write an AuditEvent (actor null = the student; on_behalf_of = CQ-5)."""

from __future__ import annotations

from apps.queue.models import AuditEvent


def record(student, verb: str, actor=None, on_behalf_of=None, **data) -> AuditEvent:
    return AuditEvent.objects.create(
        student=student,
        centre_id=student.centre_id,
        verb=verb,
        actor=actor,
        on_behalf_of=on_behalf_of,
        data=data,
    )
