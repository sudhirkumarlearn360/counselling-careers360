"""CQ-8 close in the queue engine: waiting -> not_counselled; active students stay actionable."""

from unittest import mock

import pytest
from django.utils import timezone

from apps.centres.models import CentreStatus
from apps.queue.models import AuditEvent, StudentStatus
from apps.queue.services import close_centre, complete_session, mark_missed, start_session
from tests.queue.helpers import live_centre, ops_lead, post, raw_student

pytestmark = pytest.mark.django_db


@pytest.fixture
def desk():
    centre = live_centre()
    return centre, post(centre, "Meera Iyer", ["PCM"], "Desk 1").counsellor


def test_cq8_close_marks_waiting_not_counselled_and_leaves_active_actionable(desk):
    centre, c = desk
    lead = ops_lead()
    w1 = raw_student(centre, c, "PCM-01")
    w2 = raw_student(centre, c, "PCM-02")
    called = raw_student(centre, c, "PCM-03", status=StudentStatus.CALLED)
    busy = raw_student(centre, c, "PCM-04", status=StudentStatus.IN_SESSION, started_at=timezone.now())
    assert close_centre(centre, lead) == 2
    centre.refresh_from_db()
    assert centre.status == CentreStatus.CLOSED
    for s in (w1, w2):
        s.refresh_from_db()
        assert s.status == StudentStatus.NOT_COUNSELLED
    assert start_session(called).status == StudentStatus.IN_SESSION
    assert complete_session(busy) is None
    busy.refresh_from_db()
    assert busy.status == StudentStatus.DONE
    assert AuditEvent.objects.filter(verb="centre_closed", student__isnull=False).count() == 2


def test_cq8_a_miss_after_close_ends_as_not_counselled(desk):
    centre, c = desk
    s = raw_student(centre, c, "PCM-01", status=StudentStatus.CALLED)
    close_centre(centre)
    s = mark_missed(s)
    assert s.status == StudentStatus.NOT_COUNSELLED and s.recalls == 1
    assert not s.messages.filter(template="missed_first").exists()
    assert AuditEvent.objects.get(student=s, verb="missed").data["to"] == "not_counselled"


def test_cq8_close_audit_rows_are_batched(desk):
    centre, c = desk
    raw_student(centre, c, "PCM-01")
    with mock.patch.object(AuditEvent.objects, "bulk_create", wraps=AuditEvent.objects.bulk_create) as spy:
        close_centre(centre)
    assert spy.call_args.kwargs["batch_size"] == 500
