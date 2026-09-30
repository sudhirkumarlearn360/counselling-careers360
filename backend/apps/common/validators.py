"""Input normalisation shared by every serializer (mirrors the frontend Zod rules)."""

import re
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

_TEN_DIGITS = re.compile(r"^\d{10}$")


def normalise_mobile(raw: Optional[str]) -> str:
    """Reduce any way of writing an Indian mobile number to its 10 digits. Does not validate.

    Handled: spaces, dashes, dots, brackets and other separators; `+91`, `91`, `0091`, `091`, a leading `0`,
    and combinations such as `+91 098110 22001`. A 10-digit number is never trimmed, even when it starts with
    91 or 0's neighbours (e.g. 9198765432), because prefixes are only removed from longer numbers.
    The frontend (frontend/src/lib/mobile.ts) implements the same rules against the same fixtures.
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00"):  # international dialling prefix: 0091 98110 22001
        digits = digits[2:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 13 and digits[:3] in ("910", "091"):  # +91 0 98110 22001, 091 98110 22001
        digits = digits[3:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


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
