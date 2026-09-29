"""`hall` area (reception + ops_lead): the front-desk queue, desk check-in, and student actions."""

from __future__ import annotations

from rest_framework import status as http
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import RoleIn
from apps.centres.models import Centre
from apps.common.views import ApiView
from apps.counsellors.models import Counsellor
from apps.messaging.services import ResendRefused, resend_message
from apps.queue import payloads
from apps.queue.models import Source, Student
from apps.queue.services import check_in, move, requeue
from apps.queue.services.checkin import STREAM_LABELS  # noqa: F401
from apps.queue.validation import validate_checkin

HallPermission = RoleIn(Role.RECEPTION, Role.OPS_LEAD)


def hall_centre(request, centre_id) -> Centre:
    """Reception sees only their own centre; ops sees any. Others get 404 (never reveal existence)."""
    centre = Centre.objects.select_related("settings").filter(pk=centre_id).first()
    if centre is None or (request.user.role == Role.RECEPTION and request.user.centre_id != centre.id):
        raise NotFound()
    return centre


def hall_student(request, student_id) -> Student:
    s = (
        Student.objects.select_related("centre", "centre__settings", "counsellor", "consent_by")
        .prefetch_related("notes", "messages")
        .filter(pk=student_id)
        .first()
    )
    if s is None or (request.user.role == Role.RECEPTION and request.user.centre_id != s.centre_id):
        raise NotFound()
    return s


def pick_counsellor(raw) -> Counsellor:
    """A counsellor chosen in the UI; anything unknown or malformed is a clear 400, never a 500."""
    try:
        counsellor = (
            Counsellor.objects.filter(pk=int(raw)).first() if raw not in (None, "", True, False) else None
        )
    except (TypeError, ValueError):
        counsellor = None
    if counsellor is None:
        raise ValidationError({"counsellor_id": "Pick a counsellor."})
    return counsellor


def _counsellor_id(request):
    raw = request.query_params.get("counsellor")
    if raw in (None, "", "all"):
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError({"counsellor": "Unknown counsellor."}) from None


class HallQueueView(ApiView):
    permission_classes = [HallPermission]

    def get(self, request, centre_id, **kwargs):
        centre = hall_centre(request, centre_id)
        payload = payloads.hall_payload(centre, request.query_params.get("q", ""), _counsellor_id(request))
        return Response({"data": payload, "count": payload["count"], "total": len(payload["rows"])})


class HallCheckInView(ApiView):
    permission_classes = [HallPermission]

    def post(self, request, centre_id, **kwargs):
        centre = hall_centre(request, centre_id)
        data = validate_checkin(request.data, Source.DESK)
        if request.data.get("counsellor_id") not in (None, ""):
            data["counsellor_id"] = pick_counsellor(request.data.get("counsellor_id")).id
        student = check_in(
            centre, data, Source.DESK, actor=request.user, confirm=request.data.get("confirm") is True
        )
        student = hall_student(request, student.pk)
        desk = payloads.student_detail(student)["counsellor"]["desk"]
        message = f"Token {student.token} issued to {student.counsellor.name}, {desk}."
        return Response(
            {"data": payloads.student_detail(student), "message": message}, status=http.HTTP_201_CREATED
        )


class HallStudentView(ApiView):
    permission_classes = [HallPermission]

    def get(self, request, student_id, **kwargs):
        return Response({"data": payloads.hall_student_detail(hall_student(request, student_id))})


class HallStudentMoveView(ApiView):
    permission_classes = [HallPermission]

    def post(self, request, student_id, **kwargs):
        s = hall_student(request, student_id)
        target = pick_counsellor(request.data.get("counsellor_id"))
        move(s, target, actor=request.user, confirm=request.data.get("confirm") is True)
        return Response({"data": payloads.hall_student_detail(hall_student(request, student_id))})


class HallStudentRequeueView(ApiView):
    permission_classes = [HallPermission]

    def post(self, request, student_id, **kwargs):
        requeue(hall_student(request, student_id), actor=request.user)
        return Response({"data": payloads.hall_student_detail(hall_student(request, student_id))})


class HallMessageResendView(ApiView):
    permission_classes = [HallPermission]

    def post(self, request, student_id, message_id, **kwargs):
        s = hall_student(request, student_id)
        try:
            resend_message(s, message_id)
        except ResendRefused:
            raise NotFound() from None
        return Response({"data": payloads.hall_student_detail(hall_student(request, student_id))})
