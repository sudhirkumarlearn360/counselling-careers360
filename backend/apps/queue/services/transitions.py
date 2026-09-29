"""Status transitions. Minimal `close_centre` (CQ-8); the queue-services task adds the rest."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.centres.exceptions import CentreNotLive
from apps.centres.models import Centre, CentreStatus
from apps.queue.models import AuditEvent, Student, StudentStatus


@transaction.atomic
def close_centre(centre: Centre, actor) -> int:
    """Waiting students become `not_counselled` (never no_show), the centre is closed. Returns the count.

    Called or in-session students are left alone so a session in progress is never cut off.
    """
    locked = Centre.objects.select_for_update().get(pk=centre.pk)
    if locked.status != CentreStatus.LIVE:
        raise CentreNotLive()
    waiting = Student.objects.select_for_update().filter(centre=locked, status=StudentStatus.WAITING)
    ids = list(waiting.order_by("id").values_list("id", "token"))
    if ids:
        Student.objects.filter(pk__in=[i for i, _ in ids]).update(
            status=StudentStatus.NOT_COUNSELLED, updated_at=timezone.now()
        )
    locked.status = CentreStatus.CLOSED
    locked.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        centre=locked,
        verb=AuditEvent.Verb.CENTRE_CLOSED,
        actor=actor,
        data={"not_counselled": len(ids), "tokens": [t for _, t in ids]},
    )
    centre.status = CentreStatus.CLOSED
    return len(ids)
