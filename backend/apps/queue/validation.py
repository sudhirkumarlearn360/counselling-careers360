"""Check-in and student-edit validation. Exact messages from counselqueue-ui-spec; every failing
field is reported together (CQ-15, CQ-29), and entered values are never dropped by the API."""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from apps.common.choices import Clarity, Exam, Help, Klass, Stream
from apps.common.validators import normalise_mobile, valid_email, valid_mobile
from apps.queue.models import Source

MSG_NAME = "Enter your name (at least 3 letters)."
MSG_SCHOOL = "Enter your school."
MSG_MOBILE = "A 10-digit mobile number is needed for the turn alert."
MSG_PARENT = "Parent's number should be 10 digits."
MSG_EMAIL = "That email doesn't look right."
MSG_STREAM = "Pick the stream you're in."
MSG_KLASS = "Pick your class."
MSG_COURSE = "Tell us the course or career you're aiming for — 'not sure yet' is fine."
MSG_EXAMS = "Pick exams from the list."
MSG_CLARITY = "Pick how clear you are about your choice."
MSG_HELP = "Pick at least one thing you'd like help with."
MSG_HELP_LIST = "Pick help options from the list."
MSG_CONSENT = "Tick the consent line so a counsellor can advise you"


def _text(raw, key) -> str:
    value = raw.get(key)
    return value.strip() if isinstance(value, str) else ""


def _list(raw, key):
    value = raw.get(key)
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def validate_checkin(raw: dict, source: str) -> dict:
    """Self check-in is strict; the desk (CQ-29) needs only name, mobile, stream and one help option."""
    strict = source == Source.SELF
    errors, out = {}, {}

    out["name"] = _text(raw, "name")
    if len(out["name"]) < 3:
        errors["name"] = MSG_NAME
    out["school"] = _text(raw, "school")
    if strict and not out["school"]:
        errors["school"] = MSG_SCHOOL

    out["mobile"] = normalise_mobile(_text(raw, "mobile"))
    if not valid_mobile(out["mobile"]):
        errors["mobile"] = MSG_MOBILE
    parent = normalise_mobile(_text(raw, "parent_mobile"))
    out["parent_mobile"] = parent
    if parent and not valid_mobile(parent):
        errors["parent_mobile"] = MSG_PARENT
    out["email"] = _text(raw, "email")
    if out["email"] and not valid_email(out["email"]):
        errors["email"] = MSG_EMAIL

    out["stream"] = _text(raw, "stream")
    if out["stream"] not in Stream.values:
        errors["stream"] = MSG_STREAM
    out["klass"] = _text(raw, "klass")
    if out["klass"] and out["klass"] not in Klass.values:
        errors["klass"] = MSG_KLASS

    out["course"] = _text(raw, "course")
    if strict and not out["course"]:
        errors["course"] = MSG_COURSE
    exams = _list(raw, "exams")
    if any(e not in Exam.values for e in exams):
        errors["exams"] = MSG_EXAMS
    if Exam.NONE.value in exams:  # "None / not sure" is exclusive
        exams = [Exam.NONE.value]
    out["exams"] = exams
    out["clarity"] = _text(raw, "clarity")
    if out["clarity"] and out["clarity"] not in Clarity.values:
        errors["clarity"] = MSG_CLARITY
    help_ = _list(raw, "help")
    out["help"] = help_
    if not help_:
        errors["help"] = MSG_HELP
    elif any(h not in Help.values for h in help_):
        errors["help"] = MSG_HELP_LIST

    if strict and raw.get("consent") is not True:
        errors["consent"] = MSG_CONSENT
    if errors:
        raise ValidationError(errors)
    return out


# --- Counsellor edits during a session (CQ-44, CQ-48) ------------------------------------------

REQUIRED_LABELS = {"name": "Name", "school": "School", "mobile": "Mobile", "stream": "Stream"}
EDITABLE_TEXT = (
    "name",
    "school",
    "course",
    "home_city",
    "target_exam",
    "budget",
    "colleges_discussed",
    "accompanied_by",
)


def validate_student_edit(raw: dict, today) -> dict:
    """Only the keys present are validated and returned (PATCH). Clearing a required field names it."""
    from apps.common.choices import Outcome

    errors, out = {}, {}
    for key in EDITABLE_TEXT:
        if key in raw:
            out[key] = _text(raw, key)
    for key, label in REQUIRED_LABELS.items():
        if key in raw and not _text(raw, key):
            errors[key] = f"{label} is required."
    if "name" in out and out["name"] and len(out["name"]) < 3:
        errors["name"] = MSG_NAME
    if "mobile" in raw and _text(raw, "mobile"):
        out["mobile"] = normalise_mobile(_text(raw, "mobile"))
        if not valid_mobile(out["mobile"]):
            errors["mobile"] = MSG_MOBILE
    if "parent_mobile" in raw:
        out["parent_mobile"] = normalise_mobile(_text(raw, "parent_mobile"))
        if out["parent_mobile"] and not valid_mobile(out["parent_mobile"]):
            errors["parent_mobile"] = MSG_PARENT
    if "email" in raw:
        out["email"] = _text(raw, "email")
        if out["email"] and not valid_email(out["email"]):
            errors["email"] = MSG_EMAIL
    if "stream" in raw and _text(raw, "stream") and _text(raw, "stream") not in Stream.values:
        errors["stream"] = MSG_STREAM
    elif "stream" in raw:
        out["stream"] = _text(raw, "stream")
    for key, choices, msg in (("klass", Klass.values, MSG_KLASS), ("clarity", Clarity.values, MSG_CLARITY)):
        if key in raw:
            out[key] = _text(raw, key)
            if out[key] and out[key] not in choices:
                errors[key] = msg
    if "outcome" in raw:
        value = raw.get("outcome") or None
        if value is not None and value not in Outcome.values:
            errors["outcome"] = "Pick one of the outcomes."
        out["outcome"] = value
    if "follow_up_on" in raw:
        value = raw.get("follow_up_on") or None
        if value is not None:
            import datetime as dt

            try:
                value = dt.date.fromisoformat(str(value))
            except ValueError:
                errors["follow_up_on"] = "Enter the follow-up date as YYYY-MM-DD."
            else:
                if value < today:
                    errors["follow_up_on"] = "Pick a follow-up date from today onwards."
        out["follow_up_on"] = value
    if errors:
        raise ValidationError(errors)
    return out
