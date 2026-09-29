---
name: counselqueue-ui-spec
description: CounselQueue user-facing copy and validation — every exact error, empty-state and banner string, field validation rules shared by backend serializers and frontend Zod schemas, plus per-screen specs and design tokens. Load when building or testing any screen, form, serializer validation or error message.
---

# UI spec

Screens: [screens](references/screens.md). Colours and fonts: [design-tokens](references/design-tokens.md). Use strings **verbatim**. `{x}` = interpolated.

## Validation (backend serializer and frontend Zod must match)
- `normalise_mobile(raw)`: remove spaces and `-`, strip a leading `+91` or `0`. The result must be exactly 10 digits. Apply this before validation, duplicate checks and storage.
- Student name: required, ≥ 3 characters after trimming. School: required. Mobile: required, 10 digits. Parent mobile: optional; if given, 10 digits. Email: optional; if given, a valid format. Stream: one of 6. Class: one of CLASSES.
- Course/career: required (the hint says "Not sure yet" is a fine answer). Exams: optional, multi; "None / not sure" clears the others and is cleared by picking any other. Clarity: one. Help: ≥ 1.
- Report **all** failing fields together on submit, and keep the entered values (CQ-15/29).
- Desk check-in requires name, mobile and ≥1 help (CQ-29). Other rules are the same.
- Counsellor edit (CQ-44): same 10-digit rules. Clearing a required field shows "{Field} is required."
- Follow-up date must be ≥ today (IST).

## Exact strings
**Sign-in (CQ-1/2)**
- Blank: "Enter your work email and password"
- Wrong: "That email and password don't match an account."
- 3rd failure notice: "Three failed attempts — contact the IT helpdesk: 1800 572 9877 · it-support@careers360.com" (no reset link).

**Setup (CQ-6/9/10/11)**
- "City and venue are both needed."
- "Closing time must be later than opening time."
- Duplicate centre: "A centre in {city} on {date} already exists — you can still save."
- "A name and at least one stream are needed."
- Desk clash: "{desk} is already taken by {counsellor} at this centre."
- Uncovered on go-live: "No counsellor covers {streams}. Go live anyway?"
- Roster conflict: "{counsellor} is already posted to {city} on {date}."
- Close: "{n} students are still waiting. They'll be marked not counselled."

**Student check-in (CQ-12…20)**
- "This centre isn't open for check-in" + " — it runs on {date}."
- Closed: "Check-in closed at {close_time}. Please see the front desk."
- "A 10-digit mobile number is needed for the turn alert."
- Other field errors: "Enter your name (at least 3 letters)." · "Enter your school." · "Parent's number should be 10 digits." · "That email doesn't look right." · "Tell us the course or career you're aiming for — 'not sure yet' is fine." · "Pick at least one thing you'd like help with."
- Stream hint: "Your stream decides which counsellor you're sent to."
- Consent line: "I agree that Careers360 counsellors may use these details to advise me and contact me about admissions. I can withdraw this at any time."
- "Tick the consent line so a counsellor can advise you"
- OTP: "That code doesn't match — check your WhatsApp"
- Duplicate: "A token is already open for this number — {token}."
- No one on duty: "No counsellor is on desk yet — please see the front desk."
- No one for the stream: "No counsellor for your stream is on desk yet — please see the front desk."
- Avg wait before any call: "—"
- What to bring: "Marksheets, entrance scorecard, photo ID, and a parent or guardian — all optional."

**Token screen (CQ-21…28)**
- Position (only when `eta.ahead ≥ 1`; when `eta.is_next` show the Next line instead): "{n} ahead of you at {desk}" · "About {m} min" · "Expected around {HH:MM}" (always "about"/approximate).
- Next: "You're next — stay near {desk}."
- Called: "It's your turn — go to {desk}, {counsellor}. Your place is held for two calls."
- In session: "Session in progress with {counsellor} at {desk}."
- Done: "Session complete. Your shortlist and next steps are on their way over WhatsApp."
- No-show: "We called you twice. Visit the front desk and they'll put you back in the queue."
- Consent pending: "Consent pending — tap to confirm it's you."
- Release confirm: "Give up your turn? You'll need a new token to rejoin."
- Lost token hint: "Lost this page? The front desk can find your token from your mobile number."

**Front desk (CQ-29…36)**
- Hall empty: "No one in the hall yet — tokens appear here as students scan in."
- Search empty: "No match for "{q}". Try the last four digits of their mobile."
- Result count: "{n} results"
- Move stream warning: "{counsellor} doesn't cover {stream}. Move anyway?"
- Desk confirmation: "Token {token} issued to {counsellor}, {desk}."

**Counsellor (CQ-37…50)**
- Queue empty: "Your queue is clear — new check-ins land here as students scan in."
- Call blocked: "Finish {token} before calling the next student."
- Unknown token: "No token {token} at this centre today."
- Completed token: "Token {token} was already counselled at {HH:MM}."
- Released token: "Token {token} was released — requeue it to call."
- Start blocked: "Consent is pending — record verbal consent or resend the request."
- Unanswered: "Not answered"
- Complete confirmation: "Done. Next up: {token}." / "Done. Your queue is clear."
- Empty note: "Write something before adding a note."

**Ops lead (CQ-5, 59…61)**
- Desk banner: "Viewing {counsellor}'s desk — anything you do here is recorded against that counsellor." + "Back to live centres"
- Records empty: "No students match these filters."
- Count: "{n} of {total} students"
- No data metric: "—"; averages: "{value} (from {n})".

**Hall board (CQ-51…53)**
- Empty desk: "—" (dimmed) · break: "back shortly" · off duty: "Closed" · on desk, empty queue: "queue clear"
- Recently called empty: "Nothing called yet."
- Standing line: "Scan the code at the entrance to check in — keep your phone on for your turn alert."
