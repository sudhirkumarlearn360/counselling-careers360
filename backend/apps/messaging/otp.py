"""Mobile verification before a token is issued (CQ-18).

A 4-digit code goes to the student's WhatsApp. Verifying it returns a signed, single-use
`verification_id` bound to the normalised mobile and the centre; the check-in POST must present it.
Codes are stored hashed. Limits (settings): OTP_TTL_MIN, OTP_RESEND_SEC, OTP_MAX_ATTEMPTS.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.common.exceptions import DomainError
from apps.messaging.models import Message, OtpCode
from apps.messaging.services import get_provider
from apps.messaging.templates import render

logger = logging.getLogger("apps.messaging")

SALT = "counselqueue.otp-verification"
MAX_SENDS_PER_HOUR = 5
VERIFICATION_MAX_AGE_SEC = 30 * 60

MISMATCH = "That code doesn't match — check your WhatsApp"
EXPIRED = "That code has expired — request a new one."
NOT_VERIFIED = "Verify your number first."


class OtpError(DomainError):
    code = "otp_error"


class OtpMismatch(OtpError):
    code = "otp_mismatch"
    message = MISMATCH


class OtpExpired(OtpError):
    code = "otp_expired"
    message = EXPIRED


class OtpTooSoon(OtpError):
    code = "otp_resend_wait"
    status_code = 429


class OtpLimit(OtpError):
    code = "otp_limit"
    status_code = 429
    message = "Too many codes requested — try again in an hour."


class NotVerified(OtpError):
    code = "verification_required"
    message = NOT_VERIFIED


def _hash(centre_id: int, mobile: str, code: str) -> str:
    return salted_hmac(SALT, f"{centre_id}:{mobile}:{code}").hexdigest()


def _deliver(centre, mobile: str, code: str) -> Message:
    message = Message.objects.create(
        student=None,
        template=Message.Template.OTP_CODE,
        to=mobile,
        body=render("otp_code", code=code, minutes=settings.OTP_TTL_MIN),
        status=Message.Status.QUEUED,
    )
    if not centre.settings.whatsapp_enabled:
        message.status, message.failure_reason = Message.Status.FAILED, "disabled"
    else:
        try:
            result = get_provider().send(mobile, message.body)
            message.status, message.provider_id = result.status, result.provider_id or ""
            if result.status == Message.Status.FAILED:
                message.failure_reason = "provider"
        except Exception as exc:  # noqa: BLE001 - a provider error is recorded, never raised to the student
            logger.warning("OTP send failed for centre %s: %s", centre.pk, exc)
            message.status, message.failure_reason = Message.Status.FAILED, f"error: {exc}"[:100]
    message.save(update_fields=["status", "provider_id", "failure_reason", "updated_at"])
    return message


def send_otp(centre, mobile: str) -> dict:
    """Send a fresh code. Earlier unverified codes for this mobile are superseded."""
    now = timezone.now()
    with transaction.atomic():
        recent = list(
            OtpCode.objects.select_for_update()
            .filter(centre=centre, mobile=mobile, created_at__gte=now - timedelta(hours=1))
            .order_by("-created_at")
        )
        if recent:
            wait = settings.OTP_RESEND_SEC - (now - recent[0].created_at).total_seconds()
            if wait > 0:
                raise OtpTooSoon(
                    f"Wait {int(wait) + 1} seconds before asking for another code.",
                    data={"retry_after": int(wait) + 1},
                )
        if len(recent) >= MAX_SENDS_PER_HOUR:
            raise OtpLimit()
        OtpCode.objects.filter(
            centre=centre, mobile=mobile, invalidated_at__isnull=True, verified_at__isnull=True
        ).update(invalidated_at=now)
        code = settings.OTP_STUB_CODE or f"{secrets.randbelow(10000):04d}"
        OtpCode.objects.create(
            mobile=mobile,
            centre=centre,
            code_hash=_hash(centre.pk, mobile, code),
            expires_at=now + timedelta(minutes=settings.OTP_TTL_MIN),
        )
        _deliver(centre, mobile, code)
    return {"resend_after_sec": settings.OTP_RESEND_SEC, "expires_in_min": settings.OTP_TTL_MIN}


def verify_otp(centre, mobile: str, code: str) -> str:
    """Return a signed verification_id, or raise OtpMismatch / OtpExpired."""
    code = (code or "").strip()
    now = timezone.now()
    outcome = None  # decided inside the transaction, raised after it commits (attempts must persist)
    verification_id = None
    with transaction.atomic():
        otp = (
            OtpCode.objects.select_for_update()
            .filter(centre=centre, mobile=mobile, invalidated_at__isnull=True, verified_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if otp is None or otp.expires_at <= now:
            outcome = OtpExpired()
        elif constant_time_compare(_hash(centre.pk, mobile, code), otp.code_hash):
            nonce = secrets.token_urlsafe(24)
            otp.verified_at, otp.verification_nonce = now, nonce
            otp.save(update_fields=["verified_at", "verification_nonce"])
            verification_id = signing.dumps({"m": mobile, "c": centre.pk, "n": nonce}, salt=SALT)
        else:
            otp.attempts += 1
            fields = ["attempts"]
            if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp.invalidated_at = now
                fields.append("invalidated_at")
            otp.save(update_fields=fields)
            outcome = OtpMismatch(data={"attempts_left": max(0, settings.OTP_MAX_ATTEMPTS - otp.attempts)})
    if outcome is not None:
        raise outcome
    return verification_id


def consume_verification(centre, mobile: str, verification_id: str) -> None:
    """Check the id is genuine, for this mobile and centre, and unused; then mark it used.

    Call inside the check-in transaction: a check-in that fails rolls the use back, so the student
    can fix the form and resubmit with the same verification.
    """
    try:
        payload = signing.loads(verification_id or "", salt=SALT, max_age=VERIFICATION_MAX_AGE_SEC)
    except signing.BadSignature:
        raise NotVerified() from None
    if payload.get("m") != mobile or payload.get("c") != centre.pk:
        raise NotVerified()
    otp = OtpCode.objects.select_for_update().filter(verification_nonce=payload.get("n")).first()
    if otp is None or otp.verification_used_at is not None:
        raise NotVerified()
    otp.verification_used_at = timezone.now()
    otp.save(update_fields=["verification_used_at"])
