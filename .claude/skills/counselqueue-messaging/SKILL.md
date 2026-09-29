---
name: counselqueue-messaging
description: CounselQueue WhatsApp and OTP — provider interface, stub backend, every message template verbatim with trigger and variables, OTP rules, delivery-failure flagging and resend. Load when sending any student message or touching messaging code or tests.
---

# Messaging

All sends go through `apps.messaging.services.send_template(student, key, **vars)`. It renders the body, creates a `Message` row, calls the provider from `settings.MESSAGING_PROVIDER` (default `apps.messaging.providers.stub.StubProvider`) and stores the result. **Messaging never changes a student's status or queue position (CQ-58).** If `CentreSettings.whatsapp_enabled` is False, it records `status=failed` with reason `disabled`.

## Provider interface
```python
class MessagingProvider(Protocol):
    def send(self, to: str, body: str) -> SendResult: ...  # SendResult(provider_id, status in queued|sent|delivered|failed)
```
`StubProvider` logs to the console and returns `sent`, or `failed` if `to in settings.MESSAGING_STUB_FAIL_TO`. The delivery-status webhook (future real provider) goes to `POST /api/1/webhooks/messaging/status`, which updates `Message.status`.

## Templates (key → trigger → body)
Variables: `{city} {token} {counsellor} {desk} {link} {code} {minutes} {recalls} {close_time}`. `{link}` = the student's live token URL `/t/{access_key}` (CQ-26).

| Key | Trigger | Body |
|---|---|---|
| `otp_code` | student submits details (CQ-18) | Your Careers360 check-in code is {code}. It expires in {minutes} minutes. |
| `token_confirm_self` | self check-in token issued (CQ-54) | Careers360 {city}: you're in the queue. Token {token}, counsellor {counsellor} at {desk}. We'll message you when it's your turn. Track live: {link} |
| `token_confirm_desk` | desk check-in token issued (CQ-54, CQ-24) | Careers360 {city}: our front desk has checked you in. Token {token}, counsellor {counsellor} at {desk}. Reply YES to confirm it's you and allow us to use these details for counselling. We'll message you when it's your turn. Track live: {link} |
| `consent_request` | resend from session screen (CQ-42) | Careers360: please confirm it's you and allow us to use your details for counselling — reply YES or open {link} |
| `turn_called` | counsellor calls (CQ-23, CQ-55) | It's your turn. Please go to {desk} — {counsellor}. Your place is held for two calls. *(+ if consent pending:)* Reply YES to confirm you're here and consent to your details being used for counselling. |
| `missed_first` | first miss (CQ-46, CQ-56) | We called {token} and missed you. You're back in the queue — next call is the last one. |
| `missed_final` | no-show (CQ-46, CQ-56) | We called {token} {recalls} times. Visit the front desk to get back in the queue. |
| `desk_changed` | move / cross-desk call (CQ-35, CQ-40, CQ-56) | You've been moved to {counsellor}, {desk}. Token {token} stays the same. |
| `released` | student releases (CQ-25, CQ-56) | Token {token} is released. You can check in again before {close_time}. |
| `session_done` | complete (CQ-49, CQ-57) | Thanks for meeting {counsellor}. Your shortlist and next steps are on the way. Rate this session 1–5: {link} |

Inbound "YES" (future provider webhook) → `record_consent(student, by=None)`. In this release the `{link}` token page has a "Confirm it's me" button that does the same.

## OTP (CQ-18)
4-digit code, stored hashed with `expires_at` = now + `settings.OTP_TTL_MIN` (10). Resend is allowed after `settings.OTP_RESEND_SEC` (30). `settings.OTP_MAX_ATTEMPTS` (5) wrong tries invalidate the code. A wrong code shows "That code doesn't match — check your WhatsApp". In DEBUG/stub mode, the code `settings.OTP_STUB_CODE` (e.g. "1234") is accepted, matching the prototype shortcut. The verification result is a short-lived, single-use, signed `verification_id` bound to the normalised mobile and centre (`{mobile, centre_id, nonce}`). The check-in POST must present it, and its mobile must equal the submitted mobile, otherwise it is rejected. A duplicate response (CQ-20) returns the existing token's live status (and `access_key`) only after this check passes. Throttle `public/otp/send` (per mobile: 1 per `OTP_RESEND_SEC`, 5 per hour; per IP: 20 per hour) and `public/centres/{slug}/checkins/` (per IP) with DRF throttles.

## Delivery failure (CQ-58)
A `Message` with status `failed` for key `turn_called` sets a flag the hall queue and desk show: "WhatsApp didn't reach them — {template label}. Call out their token." Resend = `POST /api/1/hall/students/<student_id>/messages/<message_id>/resend` (reception) or `POST /api/1/desk/students/<student_id>/messages/<message_id>/resend` (counsellor). It is never a status change.
