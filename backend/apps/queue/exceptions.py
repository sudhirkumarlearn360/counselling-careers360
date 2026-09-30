"""Queue-engine domain errors. Messages are the exact counselqueue-ui-spec strings where one exists.

The DRF exception handler (apps.common.exceptions) maps each to ``{"code", "message", "data"}``.
"""

from __future__ import annotations

from rest_framework import status

from apps.common.exceptions import DomainError


class QueueError(DomainError):
    code = "queue_error"


# --- Check-in (CQ-12, CQ-19, CQ-20) ---------------------------------------------------------------


class CentreNotLive(QueueError):
    """Check-in at a planned or closed centre (not the ops-side close error in apps.centres)."""

    code = "centre_not_live"


class DuplicateToken(QueueError):
    code = "duplicate_token"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, existing):
        self.existing = existing
        super().__init__(
            f"A token is already open for this number — {existing.token}.",
            data={"token": existing.token, "student_id": existing.id, "status": existing.status},
        )


class NoCounsellorOnDuty(QueueError):
    code = "no_counsellor_on_duty"
    message = "No counsellor is on desk yet — please see the front desk."


class NoCounsellorForStream(QueueError):
    code = "no_counsellor_for_stream"
    message = "No counsellor for your stream is on desk yet — please see the front desk."


# --- Desk actions (CQ-39..49) ---------------------------------------------------------------------


class CounsellorNotOnDesk(QueueError):
    code = "counsellor_not_on_desk"


class QueueEmpty(QueueError):
    code = "queue_empty"
    message = "Your queue is clear — new check-ins land here as students scan in."


class DeskBusy(QueueError):
    code = "desk_busy"
    status_code = status.HTTP_409_CONFLICT


class TokenNotFound(QueueError):
    code = "token_not_found"


class TokenNotCallable(QueueError):
    """The token exists but is done, released, no-show, not counselled or with another desk."""

    code = "token_not_callable"


class ConsentPending(QueueError):
    code = "consent_pending"
    message = "Consent is pending — record verbal consent or resend the request."


class InvalidTransition(QueueError):
    """The student's status does not allow this action (the UI hides the control in these cases)."""

    code = "invalid_transition"


class NotPostedHere(QueueError):
    code = "not_posted_here"


class QueueClosed(QueueError):
    """A closed centre has no queue to rejoin (requeue after close)."""

    code = "centre_closed"
    message = "This centre has closed and can't be changed."
