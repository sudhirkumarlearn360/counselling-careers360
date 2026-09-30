"""Provider delivery-status webhook (CQ-58): signed with MESSAGING_WEBHOOK_SECRET (HMAC-SHA256)."""

from __future__ import annotations

import hashlib
import hmac

from django.conf import settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.views import ApiView
from apps.messaging.models import Message
from apps.queue.models import AuditEvent


class MessagingStatusView(ApiView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, **kwargs):
        secret = getattr(settings, "MESSAGING_WEBHOOK_SECRET", "")
        signature = request.headers.get("X-Signature", "")
        expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest() if secret else ""
        if not secret or not hmac.compare_digest(signature, expected):
            raise PermissionDenied("Bad signature.", code="bad_signature")
        provider_id = str(request.data.get("provider_id") or "")
        new_status = request.data.get("status")
        if new_status not in Message.Status.values:
            raise ValidationError({"status": "Unknown status."})
        message = Message.objects.filter(provider_id=provider_id).exclude(provider_id="").first()
        if message is None:
            raise NotFound()
        was_failed = message.status == Message.Status.FAILED
        message.status = new_status
        message.save(update_fields=["status", "updated_at"])
        if new_status == Message.Status.FAILED and not was_failed and message.student_id:
            AuditEvent.objects.create(
                student_id=message.student_id,
                centre_id=message.student.centre_id,
                verb=AuditEvent.Verb.MESSAGE_FAILED,
                data={"message_id": message.id, "template": message.template, "reason": "provider"},
            )
        return Response({"data": {"id": message.id, "status": message.status}})
