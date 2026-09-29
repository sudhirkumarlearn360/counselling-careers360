"""Input normalisation shared by every serializer (mirrors the frontend Zod rules)."""

import re
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

_TEN_DIGITS = re.compile(r"^\d{10}$")


def normalise_mobile(raw: Optional[str]) -> str:
    """Remove spaces and '-', then strip one leading '+91' or '0'. Does not validate."""
    value = (raw or "").strip().replace(" ", "").replace("-", "")
    if value.startswith("+91"):
        value = value[3:]
    elif value.startswith("0"):
        value = value[1:]
    return value


def valid_mobile(raw: Optional[str]) -> bool:
    """True when the normalised value is exactly 10 digits."""
    return bool(_TEN_DIGITS.match(normalise_mobile(raw)))


def valid_email(raw: Optional[str]) -> bool:
    if not raw:
        return False
    try:
        validate_email(raw.strip())
    except ValidationError:
        return False
    return True
