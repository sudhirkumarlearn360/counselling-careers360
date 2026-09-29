"""`public` area: student-facing and hall-screen endpoints. No login, no cookies, JSON only."""

from __future__ import annotations

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.throttles import SettingsScopedRateThrottle
from apps.centres.models import Centre, CentreStatus
from apps.common.exceptions import DomainError
from apps.common.validators import normalise_mobile, valid_mobile
from apps.common.views import ApiView
from apps.messaging import otp
from apps.queue import payloads
from apps.queue.exceptions import CentreNotLive, DuplicateToken
from apps.queue.keys import is_signed_access_key
from apps.queue.models import AuditEvent, Source, Student, StudentStatus
from apps.queue.services import check_in, record_consent, release
from apps.queue.services.audit import record
from apps.queue.validation import MSG_MOBILE, validate_checkin


class PublicView(ApiView):
    """No authentication: a stale staff token in the browser must never turn a student call into a 401."""

    authentication_classes = []
    permission_classes = [AllowAny]


def _centre(slug) -> Centre:
    centre = Centre.objects.select_related("settings").filter(slug=slug).first()
    if centre is None:
        raise NotFound()
    return centre


def _student(access_key) -> Student:
    if not is_signed_access_key(access_key):
        raise NotFound()
    s = (
        Student.objects.select_related("centre", "centre__settings", "counsellor")
        .filter(access_key=access_key)
        .first()
    )
    if s is None:
        raise NotFound()
    return s


def _mobile(request) -> str:
    raw = request.data.get("mobile") if hasattr(request.data, "get") else None
    mobile = normalise_mobile(raw if isinstance(raw, str) else "")
    if not valid_mobile(mobile):
        raise ValidationError({"mobile": MSG_MOBILE})
    return mobile


class CentreDetailView(PublicView):
    def get(self, request, centre_slug, **kwargs):
        return Response({"data": payloads.public_centre_payload(_centre(centre_slug))})


class OtpSendView(PublicView):
    throttle_classes = [SettingsScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request, centre_slug, **kwargs):
        centre = _centre(centre_slug)
        if centre.status != CentreStatus.LIVE:
            raise CentreNotLive(payloads.open_message(centre)[1], data={"status": centre.status})
        return Response({"data": otp.send_otp(centre, _mobile(request))})


class OtpVerifyView(PublicView):
    throttle_classes = [SettingsScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request, centre_slug, **kwargs):
        centre = _centre(centre_slug)
        vid = otp.verify_otp(centre, _mobile(request), str(request.data.get("code") or ""))
        return Response({"data": {"verification_id": vid}})


class CheckInView(PublicView):
    throttle_classes = [SettingsScopedRateThrottle]
    throttle_scope = "checkin"

    def post(self, request, centre_slug, **kwargs):
        centre = _centre(centre_slug)
        data = validate_checkin(request.data, Source.SELF)
        try:
            with transaction.atomic():
                otp.consume_verification(
                    centre, data["mobile"], str(request.data.get("verification_id") or "")
                )
                student = check_in(centre, data, Source.SELF)
        except DuplicateToken as dup:
            # The number was verified above, so it is safe to point the student at their open token.
            dup.data = {**dup.data, "access_key": dup.existing.access_key}
            raise
        student = Student.objects.select_related("centre", "centre__settings", "counsellor").get(
            pk=student.pk
        )
        return Response(
            {"data": {"access_key": student.access_key, "token": payloads.token_payload(student)}},
            status=status.HTTP_201_CREATED,
        )


class TokenDetailView(PublicView):
    def get(self, request, access_key, **kwargs):
        return Response({"data": payloads.token_payload(_student(access_key))})


class TokenReleaseView(PublicView):
    def post(self, request, access_key, **kwargs):
        release(_student(access_key))
        return Response({"data": payloads.token_payload(_student(access_key))})


class TokenConsentView(PublicView):
    def post(self, request, access_key, **kwargs):
        record_consent(_student(access_key), by=None)
        return Response({"data": payloads.token_payload(_student(access_key))})


class AlreadyRated(DomainError):
    code = "already_rated"
    status_code = status.HTTP_409_CONFLICT
    message = "You've already rated this session."


class TokenRatingView(PublicView):
    def post(self, request, access_key, **kwargs):
        rating = request.data.get("rating") if hasattr(request.data, "get") else None
        if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
            raise ValidationError({"rating": "Pick a rating from 1 to 5."})
        with transaction.atomic():
            s = Student.objects.select_for_update().get(pk=_student(access_key).pk)
            if s.status != StudentStatus.DONE:
                raise ValidationError({"rating": "You can rate once your session is complete."})
            if s.rating is not None:
                raise AlreadyRated()
            s.rating = rating
            s.save(update_fields=["rating", "updated_at"])
            record(s, AuditEvent.Verb.RATED, None, rating=rating)
        return Response({"data": payloads.token_payload(_student(access_key))})


class BoardView(PublicView):
    def get(self, request, centre_slug, **kwargs):
        return Response({"data": payloads.board_payload(_centre(centre_slug))})
