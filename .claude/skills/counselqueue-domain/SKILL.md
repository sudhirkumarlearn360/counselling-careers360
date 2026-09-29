---
name: counselqueue-domain
description: CounselQueue domain model — glossary, entities and fields, exact enums (streams, exams, clarity, help, classes, outcomes), student status state machine, consent, roles and navigation, audit rules. Load before designing models, APIs, screens or tests for any CQ-* story.
---

# CounselQueue domain

CounselQueue runs Careers360's travelling counselling drives. Operations sets up a **centre** (city + venue + date). Counsellors sit at **desks**. Students scan a QR at the entrance, check in on their phone, get a **token** routed to a counsellor who covers their **stream**, and wait. They are called by WhatsApp and by the **hall board**. Spec: `prd_doc.md` (story index: [stories](references/stories.md); unresolved: [open questions](references/open-questions.md)). Visual/behaviour reference: the two prototype HTML files in the project root. **The PRD wins over the prototype.**

## Glossary
- **Centre**: one city + venue + date (the prototype calls it `event`). A "centre-day".
- **Desk**: a label like "Desk 1", unique per centre (CQ-9).
- **Token**: `STREAM-NN`, e.g. `PCM-07`. It is the student's queue identity for the centre-day.
- **Wait promise**: `CentreSettings.wait_sla_min` (default 30). Past it = "late".
- **Target session**: `CentreSettings.target_session_min` (default 15).
- **Recall**: a missed call. Hitting `recall_limit` (default 2) = no-show.

## Entities (fields → Django names)
- `Centre`: city*, venue*, date, opens_at, closes_at (> opens_at), expected_students, status `planned|live|closed`, slug (for the QR URL), front_desk_phone. New centres are `planned`.
- `CentreSettings` (1:1 Centre): target_session_min=15, wait_sla_min=30, recall_limit=2, whatsapp_enabled=True.
- `Counsellor`: name*, mobile*, streams (≥1, subset of STREAMS), expected_session_min (default 15). A person; posted to centres through `Posting`.
- `Posting` (the roster, CQ-9/11/50): counsellor FK, centre FK, desk_label*, duty `on_desk|on_break|off_duty` (new = `off_duty`). Unique (centre, desk_label) and (counsellor, centre). A second posting on the same date as another is allowed with a conflict warning naming the other city (CQ-11). A counsellor's "current posting" = their posting at today's live centre. Sign-in lands them there (CQ-1). Duty, desk, board panels, tabs and assignment all read postings.
- `StaffUser` (custom user, email login, case-insensitive): name, email, role `ops_lead|reception|counsellor`, centre FK (reception), counsellor 1:1 (counsellor), title. A counsellor's centre and desk come from their current `Posting`.
- `Student` (one row per token): token, centre FK, counsellor FK, source `self|desk`, status, name*, school*, mobile* (10 digits), parent_mobile, email, stream, klass, course*, exams[], clarity, help[] (≥1), consent `given|pending`, consent_at, consent_by (null = student themself), checkin_at, queue_at (ordering key; reset on rejoin/miss), priority (pull-forward), called_at, started_at, ended_at (the current/latest visit), recalls, rating (1–5, set once), outcome, follow_up_on, colleges_discussed, home_city, target_exam, budget, accompanied_by, access_key (signed, for the student token URL).
- `SessionRecord`: student FK, counsellor FK, called_at, started_at, ended_at, outcome. One row is written on each `complete_session`, so a requeued `done` student keeps their earlier session. Session-length metrics, averages and exports read `SessionRecord` (CQ-21/38/60/61).
- `TokenSequence`: (centre, last_number). Created together with the Centre. The number never goes backwards.
- `Note`: student FK, text (non-empty), author_name, author counsellor FK, created_at. No delete.
- `AuditEvent`: student FK (nullable for centre-level events), centre FK, verb (`checked_in|called|started|completed|missed|no_show|released|requeued|moved|pulled_forward|consent_given|edited|noted|rated|message_failed|centre_live|centre_closed|duty_changed|exported`), actor (StaffUser or null = student), `on_behalf_of` (Counsellor, set when an ops lead works a desk, CQ-5), at, data JSON.
- `Message`: student FK, template, to, body, status `queued|sent|delivered|failed`, provider_id, created_at.

## Enums (exact)
- STREAMS: `PCM` "Science – PCM", `PCB` "Science – PCB", `PCMB` "Science – PCMB", `COM` "Commerce", `HUM` "Humanities / Arts", `OTH` "Other".
- EXAMS: "JEE", "NEET", "CUET", "CLAT", "Other", "None / not sure" ("None / not sure" is exclusive).
- CLARITY: "Very clear", "Have shortlisted options", "Need help shortlisting", "Completely confused".
- HELP: "College selection", "Course selection", "College & course comparison", "Admission / counselling", "Cut-offs & college chances", "Entrance exams", "Other".
- CLASSES: "Class 11", "Class 12", "Dropper / repeat year", "Graduate", "Parent enquiring".
- OUTCOMES: `ready` "Ready to apply", `interested` "Interested, needs time", `exploring` "Just exploring", `not_fit` "Not a fit"; null = "Not set" (reported distinctly, CQ-48/61).

## Student status state machine
| From | Action | To | Guard | Side effects |
|---|---|---|---|---|
| — | check in | waiting | centre live; no open token for mobile at centre (CQ-20); OTP verified (self); consent ticked (self) | token issued, `token_confirm_*` |
| waiting | call (next/by token) | called | counsellor has no called/in_session student (CQ-39) | called_at; `turn_called` |
| called | start | in_session | consent given (CQ-42) | started_at |
| in_session | complete | done | started (CQ-49) | ended_at; `session_done` |
| called | miss (recalls+1 < limit) | waiting | — | queue_at=now; `missed_first` |
| called | miss (recalls+1 ≥ limit) | no_show | — | `missed_final` |
| waiting, called | release | released | not in_session (CQ-25) | `released` |
| waiting (on close) | close centre | not_counselled | — | (not no_show, CQ-8) |
| no_show, released, done | requeue (desk) | waiting | — | same token, queue_at=now, recalls=0, audit actor (CQ-36) |
| waiting | move / call cross-desk | waiting/called | not in_session | counsellor changed, queue_at kept (CQ-35); `desk_changed` |

"Open" statuses = waiting, called, in_session.

## Consent
Self check-in: consent is given at submit (`consent_at`, by student). Desk check-in: `pending`. The consent ask is sent inside `token_confirm_desk`. `consent_request` is only for a resend from the session screen, so the student gets one message, not two. It clears by the student replying YES / tapping the link (CQ-24), or by the counsellor recording verbal consent (`consent_by` = counsellor, CQ-42; when an ops lead records it on a desk, `consent_by` = that desk's counsellor and `on_behalf_of` is set). A session cannot start while pending.

## Roles & navigation (CQ-3)
| Role | Nav (in order) | Default screen |
|---|---|---|
| reception | Hall queue, Add a student, Hall board | Hall queue |
| counsellor | My queue, Live session, My students, My centres | My queue |
| ops_lead | Live centres, Centres & dates, Counsellors, All students, Insights, Hall queue, Hall board | Live centres |

An ops lead can additionally open a counsellor's desk (My queue / Live session / My students for that counsellor) via the live view, never as a permanent nav item (CQ-5). Any other screen → redirect to the role's default. A counsellor sees only students where `counsellor = self`. Export: ops_lead only (CQ-60).

## Audit & attribution
Every transition writes an `AuditEvent`. When an ops lead acts on a desk: `actor` = the lead, `on_behalf_of` = the counsellor, and notes use `author` = that counsellor (CQ-5). Signing out changes no student state (CQ-4).
