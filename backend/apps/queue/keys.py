import secrets

from django.core import signing

_SIGNER = signing.Signer(salt="counselqueue.student-access", sep=".")


def make_access_key() -> str:
    """Random, signed key for the student's live token URL `/t/{access_key}` (CQ-26)."""
    return _SIGNER.sign(secrets.token_urlsafe(18))


def is_signed_access_key(value: str) -> bool:
    try:
        _SIGNER.unsign(value)
    except signing.BadSignature:
        return False
    return True
