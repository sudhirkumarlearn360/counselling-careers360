"""The single send path for WhatsApp messages (counselqueue-messaging).

`send_template` never changes a student's status or queue position (CQ-58): it only writes a
`Message` row (and a `message_failed` audit row when delivery fails). A provider exception is caught
and recorded as a failed Message, so a transition that sends a message always succeeds.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils.module_loading import import_string

from apps.counsellors.models import Posting
from apps.messaging.models import Message
from apps.messaging.templates import render
from apps.queue.models import AuditEvent

logger = logging.getLogger("apps.messaging")

DISABLED = "disabled"


def student_link(student) -> str:
    """The student's live token page (CQ-26)."""
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/t/{student.access_key}"


def get_provider():
    return import_string(settings.MESSAGING_PROVIDER)()


def _context(student) -> dict:
    centre = student.centre
    desk = (
        Posting.objects.filter(centre_id=student.centre_id, counsellor_id=student.counsellor_id)
        .values_list("desk_label", flat=True)
        .first()
    )
    return {
        "city": centre.city,
        "token": student.token,
        "counsellor": student.counsellor.name,
        "desk": desk or "",
        "link": student_link(student),
        "recalls": student.recalls,
        "close_time": centre.closes_at.strftime("%H:%M"),
        "consent_pending": student.consent == "pending",
    }


def _record_failure(student, message: Message) -> None:
    AuditEvent.objects.create(
        student=student,
        centre_id=student.centre_id,
        verb=AuditEvent.Verb.MESSAGE_FAILED,
        data={"message_id": message.id, "template": message.template, "reason": message.failure_reason},
    )


def send_template(student, key: str, **variables) -> Message:
    """Render `key` for `student`, record a Message, deliver it through the configured provider.

    Variables default from the student (city, token, counsellor, desk, link, recalls, close_time,
    consent_pending); keyword arguments override them. Honours `CentreSettings.whatsapp_enabled`.
    """
    context = _context(student)
    context.update(variables)
    message = Message.objects.create(
        student=student,
        template=key,
        to=student.mobile,
        body=render(key, **context),
        status=Message.Status.QUEUED,
    )
    if not student.centre.settings.whatsapp_enabled:
        message.status, message.failure_reason = Message.Status.FAILED, DISABLED
        message.save(update_fields=["status", "failure_reason", "updated_at"])
        return message
    try:
        result = get_provider().send(message.to, message.body)
    except Exception as exc:  # any provider error becomes a failed Message, never a failed transition
        logger.warning("WhatsApp send %s failed for message %s: %s", key, message.id, exc)
        message.status = Message.Status.FAILED
        message.failure_reason = f"error: {exc}"[:100]
    else:
        message.status, message.provider_id = result.status, result.provider_id or ""
        if result.status == Message.Status.FAILED:
            message.failure_reason = "provider"
    message.save(update_fields=["status", "provider_id", "failure_reason", "updated_at"])
    if message.status == Message.Status.FAILED:
        _record_failure(student, message)
    return message


class ResendRefused(Exception):
    """The message doesn't belong to this student, or has no student (an OTP)."""


def resend_message(student, message_id: int) -> Message:
    """Send the same template again (CQ-58). Never changes the student's status or queue position."""
    original = Message.objects.filter(pk=message_id, student_id=student.pk).first()
    if original is None:
        raise ResendRefused()
    return send_template(student, original.template)
