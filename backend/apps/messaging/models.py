from django.db import models
from django.utils import timezone


class Message(models.Model):
    class Template(models.TextChoices):
        OTP_CODE = "otp_code", "OTP code"
        TOKEN_CONFIRM_SELF = "token_confirm_self", "Token confirmation"
        TOKEN_CONFIRM_DESK = "token_confirm_desk", "Token confirmation (front desk)"
        CONSENT_REQUEST = "consent_request", "Consent request"
        TURN_CALLED = "turn_called", "Turn alert"
        MISSED_FIRST = "missed_first", "First missed call"
        MISSED_FINAL = "missed_final", "Final missed call"
        DESK_CHANGED = "desk_changed", "Desk change"
        RELEASED = "released", "Token released"
        SESSION_DONE = "session_done", "Session complete"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    # null only for otp_code, which is sent before a student row exists.
    student = models.ForeignKey(
        "queue.Student", null=True, blank=True, on_delete=models.CASCADE, related_name="messages"
    )
    template = models.CharField(max_length=24, choices=Template.choices)
    to = models.CharField(max_length=10)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    provider_id = models.CharField(max_length=100, blank=True)
    failure_reason = models.CharField(max_length=100, blank=True)  # e.g. "disabled"
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["student", "template", "status"]),
            models.Index(fields=["provider_id"]),
        ]

    def __str__(self):
        return f"{self.template} to {self.to} ({self.status})"


class OtpCode(models.Model):
    """4-digit check-in code, stored hashed (CQ-18)."""

    mobile = models.CharField(max_length=10)  # normalised
    centre = models.ForeignKey("centres.Centre", on_delete=models.CASCADE, related_name="otp_codes")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    invalidated_at = models.DateTimeField(null=True, blank=True)  # max attempts reached or superseded
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_nonce = models.CharField(max_length=64, blank=True)  # bound into the signed verification_id
    verification_used_at = models.DateTimeField(null=True, blank=True)  # verification_id is single-use
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["centre", "mobile", "created_at"]),
            models.Index(fields=["verification_nonce"]),
        ]

    def __str__(self):
        return f"OTP {self.mobile} @ {self.centre_id}"
