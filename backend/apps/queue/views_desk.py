"""`desk` area (counsellor, or ops_lead with ?as_counsellor=<id>): queue, calling, the live session."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework import status as http
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.accounts.desk_context import AsCounsellorMixin
from apps.accounts.models import Role
from apps.accounts.permissions import RoleIn
from apps.common.exceptions import DomainError
from apps.common.views import ApiView
from apps.counsellors.services import current_live_posting
from apps.messaging.services import ResendRefused, resend_message, send_template
from apps.queue import payloads
from apps.queue.models import AuditEvent, Note, Student
from apps.queue.services import (
    call_next,
    call_token,
    complete_session,
    mark_missed,
    pull_forward,
    record_consent,
    start_session,
)
from apps.queue.services.audit import record
from apps.queue.validation import validate_student_edit

DeskPermission = RoleIn(Role.COUNSELLOR, Role.OPS_LEAD)
MSG_EMPTY_NOTE = "Write something before adding a note."


class NoLiveCentre(DomainError):
    code = "no_live_centre"
    message = "You're not posted to a live centre today."


class DeskView(AsCounsellorMixin, ApiView):
    permission_classes = [DeskPermission]

    def live_centre(self):
        posting = current_live_posting(self.desk_counsellor)
        if posting is None:
            raise NoLiveCentre()
        return posting.centre

    def acting(self) -> dict:
        return {"actor": self.request.user, "on_behalf_of": self.on_behalf_of}

    def student(self, student_id) -> Student:
        s = (
            Student.objects.select_related("centre", "centre__settings", "counsellor", "consent_by")
            .prefetch_related("notes")
            .filter(pk=student_id, counsellor_id=self.desk_counsellor.pk)
            .first()
        )
        if s is None:
            raise NotFound()
        return s

    def desk(self, extra=None):
        payload = payloads.desk_payload(self.desk_counsellor, self.live_centre())
        return Response({"data": {**payload, **(extra or {})}})


class DeskQueueView(DeskView):
    def get(self, request, **kwargs):
        if current_live_posting(self.desk_counsellor) is None:  # not an error: the screen shows the message
            return Response(
                {"data": {"centre": None, "message": NoLiveCentre.message, "queue": [], "current": None}}
            )
        return self.desk()


class DeskCallNextView(DeskView):
    def post(self, request, **kwargs):
        result = call_next(self.desk_counsellor, self.live_centre(), **self.acting())
        return self.desk({"called": result.student.token, "warnings": result.warnings})


class DeskCallTokenView(DeskView):
    def post(self, request, **kwargs):
        token = request.data.get("token") if hasattr(request.data, "get") else None
        if not isinstance(token, str) or not token.strip():
            raise ValidationError({"token": "Type the token the student read out."})
        result = call_token(self.desk_counsellor, token, self.live_centre(), **self.acting())
        return self.desk({"called": result.student.token, "warnings": result.warnings})


class DeskStudentView(DeskView):
    def get(self, request, student_id, **kwargs):
        return Response({"data": payloads.student_detail(self.student(student_id))})

    def patch(self, request, student_id, **kwargs):
        s = self.student(student_id)
        changes = validate_student_edit(request.data, timezone.localdate())
        with transaction.atomic():
            s = Student.objects.select_for_update().get(pk=s.pk)
            for key, value in changes.items():
                setattr(s, key, value)
            s.save(update_fields=[*changes, "updated_at"])
            record(s, AuditEvent.Verb.EDITED, **self.acting(), fields=sorted(changes))
        return Response({"data": payloads.student_detail(self.student(student_id)), "message": "Saved."})


class DeskStartView(DeskView):
    def post(self, request, student_id, **kwargs):
        start_session(self.student(student_id), **self.acting())
        return self.desk()


class DeskCompleteView(DeskView):
    def post(self, request, student_id, **kwargs):
        next_token = complete_session(self.student(student_id), **self.acting())
        message = f"Done. Next up: {next_token}." if next_token else "Done. Your queue is clear."
        return self.desk({"next_token_after": next_token, "message": message})


class DeskMissedView(DeskView):
    def post(self, request, student_id, **kwargs):
        mark_missed(self.student(student_id), **self.acting())
        return self.desk()


class DeskPullForwardView(DeskView):
    def post(self, request, student_id, **kwargs):
        pull_forward(self.student(student_id), **self.acting())
        return self.desk()


class DeskConsentView(DeskView):
    """Verbal consent: attributed to the desk's counsellor with a timestamp (CQ-42)."""

    def post(self, request, student_id, **kwargs):
        record_consent(self.student(student_id), by=self.desk_counsellor, **self.acting())
        return self.desk()


class DeskConsentRequestView(DeskView):
    def post(self, request, student_id, **kwargs):
        send_template(self.student(student_id), "consent_request")
        return Response({"data": {"sent": True}})


class DeskNotesView(DeskView):
    def post(self, request, student_id, **kwargs):
        s = self.student(student_id)
        text = request.data.get("text") if hasattr(request.data, "get") else None
        text = text.strip() if isinstance(text, str) else ""
        if not text:
            raise ValidationError({"text": MSG_EMPTY_NOTE})
        with transaction.atomic():
            # Authored as the desk's counsellor even when an ops lead types it (CQ-5).
            Note.objects.create(
                student=s, text=text, author=self.desk_counsellor, author_name=self.desk_counsellor.name
            )
            record(s, AuditEvent.Verb.NOTED, **self.acting())
        return Response(
            {"data": payloads.student_detail(self.student(student_id))}, status=http.HTTP_201_CREATED
        )


class DeskMessageResendView(DeskView):
    def post(self, request, student_id, message_id, **kwargs):
        try:
            resend_message(self.student(student_id), message_id)
        except ResendRefused:
            raise NotFound() from None
        return Response({"data": payloads.student_detail(self.student(student_id))})


class DeskMyStudentsView(DeskView):
    def get(self, request, **kwargs):
        items = payloads.my_students(self.desk_counsellor, request.query_params.get("centre") or None)
        return Response({"data": items, "count": len(items), "total": len(items)})


class DeskMyCentresView(DeskView):
    def get(self, request, **kwargs):
        items = payloads.my_centres(self.desk_counsellor)
        return Response({"data": items, "count": len(items), "total": len(items)})
