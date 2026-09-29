"""Sign-in (CQ-1/2). One generic failure for wrong email or wrong password, counted per email."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, OperationalError, transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import LoginAttempt, StaffUser, normalise_email
from apps.common.exceptions import DomainError

BLANK_MESSAGE = "Enter your work email and password"
WRONG_MESSAGE = "That email and password don't match an account."
HELPDESK_MESSAGE = (
    "Three failed attempts — contact the IT helpdesk: 1800 572 9877 · it-support@careers360.com"
)

# Checked when the email is unknown so a miss costs the same hashing work as a wrong password.
_DUMMY_HASH = make_password("counselqueue-no-such-user")


class CredentialsRequired(DomainError):
    code = "credentials_required"
    message = BLANK_MESSAGE


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    message = WRONG_MESSAGE


def failure_data(failed_count: int) -> dict:
    show = failed_count >= settings.LOGIN_HELPDESK_AFTER_FAILURES
    return {
        "failed_attempts": failed_count,
        "show_helpdesk": show,
        "helpdesk_notice": HELPDESK_MESSAGE if show else None,
    }


MAX_EMAIL_LENGTH = 254  # LoginAttempt.email max_length; longer input can never match an account
RECORD_ATTEMPTS = 2  # one retry when two failures for the same email race on get_or_create


def _record_failure(email: str) -> int:
    for attempt in range(RECORD_ATTEMPTS):
        try:
            return _bump_failure(email)
        except (OperationalError, IntegrityError):
            if attempt == RECORD_ATTEMPTS - 1:
                raise


def _bump_failure(email: str) -> int:
    with transaction.atomic():
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(email=email)
        attempt.failed_count += 1
        attempt.last_failed_at = timezone.now()
        attempt.save(update_fields=["failed_count", "last_failed_at"])
        return attempt.failed_count


def sign_in(raw_email, raw_password) -> tuple:
    """Return (user, RefreshToken) or raise CredentialsRequired / InvalidCredentials."""
    email = normalise_email(raw_email) if isinstance(raw_email, str) else ""
    password = raw_password if isinstance(raw_password, str) else ""
    if not email or not password.strip():
        raise CredentialsRequired()

    if len(email) > MAX_EMAIL_LENGTH:
        # Same hashing work and same response, but nothing is stored (bounds LoginAttempt growth).
        check_password(password, _DUMMY_HASH)
        raise InvalidCredentials(data=failure_data(0))

    user = StaffUser.objects.filter(email=email).first()
    password_ok = check_password(password, user.password if user else _DUMMY_HASH)
    if not (user and password_ok and user.is_active):
        raise InvalidCredentials(data=failure_data(_record_failure(email)))

    LoginAttempt.objects.filter(email=email).update(failed_count=0)
    update_last_login(None, user)
    return user, RefreshToken.for_user(user)
