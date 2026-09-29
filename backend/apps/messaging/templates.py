"""WhatsApp template bodies, verbatim from counselqueue-messaging.

`{link}` = `{FRONTEND_BASE_URL}/t/{access_key}`.
"""

from __future__ import annotations

TEMPLATES = {
    "otp_code": "Your Careers360 check-in code is {code}. It expires in {minutes} minutes.",
    "token_confirm_self": (
        "Careers360 {city}: you're in the queue. Token {token}, counsellor {counsellor} at {desk}. "
        "We'll message you when it's your turn. Track live: {link}"
    ),
    "token_confirm_desk": (
        "Careers360 {city}: our front desk has checked you in. Token {token}, counsellor {counsellor} "
        "at {desk}. Reply YES to confirm it's you and allow us to use these details for counselling. "
        "We'll message you when it's your turn. Track live: {link}"
    ),
    "consent_request": (
        "Careers360: please confirm it's you and allow us to use your details for counselling — "
        "reply YES or open {link}"
    ),
    "turn_called": ("It's your turn. Please go to {desk} — {counsellor}. Your place is held for two calls."),
    "missed_first": (
        "We called {token} and missed you. You're back in the queue — next call is the last one."
    ),
    "missed_final": "We called {token} {recalls} times. Visit the front desk to get back in the queue.",
    "desk_changed": "You've been moved to {counsellor}, {desk}. Token {token} stays the same.",
    "released": "Token {token} is released. You can check in again before {close_time}.",
    "session_done": (
        "Thanks for meeting {counsellor}. Your shortlist and next steps are on the way. "
        "Rate this session 1–5: {link}"
    ),
}

# Appended to turn_called while the student's consent is still pending (CQ-55).
TURN_CALLED_CONSENT = (
    " Reply YES to confirm you're here and consent to your details being used for counselling."
)


def render(key: str, consent_pending: bool = False, **variables) -> str:
    """Render a template. Unknown keys raise KeyError; a missing variable raises KeyError too."""
    body = TEMPLATES[key].format(**variables)
    if key == "turn_called" and consent_pending:
        body += TURN_CALLED_CONSENT
    return body
