# CounselQueue schema (ER summary)

Source of truth: the models in `apps/*/models.py` and their migrations. Business rules: `.claude/skills/counselqueue-domain`.
MySQL 8+/9, `utf8mb4` (table default collation `utf8mb4_unicode_ci`), `sql_mode=STRICT_TRANS_TABLES`, and times stored in UTC (`USE_TZ=True`, `TIME_ZONE=Asia/Kolkata`).

**Every schema change must add a migration and a line in the [Change log](#change-log) at the end of this file.**

## Relationships

```
Centre 1──1 CentreSettings            Centre 1──1 TokenSequence       (both created in Centre.save)
Centre 1──* Posting *──1 Counsellor   (the roster; unique (centre, desk_label) and (counsellor, centre))
Centre 1──* Student *──1 Counsellor   (one Student row per token)
Student 1──* SessionRecord *──1 Counsellor, *──1 Centre   (history: one row per completed session)
Student 1──* Note *──0..1 Counsellor (author)
Student 0..1──* AuditEvent *──1 Centre; AuditEvent *──0..1 StaffUser (actor), *──0..1 Counsellor (on_behalf_of)
Student 0..1──* Message                Centre 1──* OtpCode
StaffUser *──0..1 Centre (reception)   StaffUser 0..1──0..1 Counsellor (counsellor role)
LoginAttempt (keyed by normalised email, no FK)
```

## Rules the schema relies on

- **Nothing is deleted in this release.** Every FK uses `on_delete=PROTECT`, so deleting a Centre, Student, Counsellor or StaffUser that has history raises `ProtectedError`. A Centre can never be deleted, because its CentreSettings and TokenSequence protect it. Staff users are retired with `is_active=False`, never deleted. The admin hides delete for Student, Note, AuditEvent, SessionRecord, Message and TokenSequence, and inlines have `can_delete=False`. Only `seed_demo --reset` deletes, and it deletes children first in this order: Message → Note → SessionRecord → AuditEvent → Student → OtpCode.
- **Null means something on attribution FKs:**
  - `AuditEvent.actor` null means **the student** acted (self check-in, release, rating, "Confirm it's me").
  - `AuditEvent.on_behalf_of` is set when an ops lead works a desk (CQ-5).
  - `Student.consent_by` null means the student consented themselves; otherwise it is the counsellor who recorded verbal consent.
  - `Note.author` is the counsellor the note is written as. When an ops lead writes it on a desk, the author is that desk's counsellor.
  - `AuditEvent.student` null means a centre-level event (`centre_live`, `centre_closed`, `exported`).
  - `Message.student` null is only for `otp_code`, which is sent before any Student exists.
- **`SessionRecord` is the history table.** `Student.called_at`, `started_at`, `ended_at` and `queue_at` describe only the current or latest visit, and a requeue clears them. One `SessionRecord` is written on each `complete_session`. Session length, averages, "counselled today" and exports read `SessionRecord` (CQ-21/38/60/61).
- **`SessionRecord` fields are snapshots taken at completion.** `outcome` is the outcome at that moment, and `queue_at` is the visit's queue start, so wait = `called_at − queue_at` survives a later requeue. Later edits to the Student do not rewrite history.
- **Rating is one value on the Student.** `Student.rating` (1–5, set once, CQ-28) belongs to the student's **latest** session. The per-counsellor rating roll-up attributes it to the counsellor of that student's latest `SessionRecord` (by `ended_at`). Decision: we did not add `SessionRecord.rating`, because a rating is given once per token and a requeued student is re-rated only in the rare case that the rating is still unset.
- **One open token per (centre, mobile) has no DB constraint.** "Open" = waiting, called or in_session, and a partial unique index on status is not portable to MySQL. The check-in service enforces the rule under the per-centre `TokenSequence` row lock (`select_for_update`), which serialises check-ins at a centre before the duplicate check runs (CQ-20, queue-engine "Concurrency"). The `(centre, mobile)` index keeps that check fast.
- **Token numbers never go back.** `TokenSequence.last_number` only increases, including through `seed_demo --reset`. `(centre, token)` is unique on Student.
- **`school`, `course` and `help` are `blank=True` at model level**, because a desk check-in needs only name, mobile and at least one help item, and seeded or legacy rows may be sparse. Tasks 5 and 6 serializers must enforce the required rules: self check-in requires school, course and at least one help item (CQ-15/16), and desk check-in requires name, mobile and at least one help item (CQ-29). `mobile` is stored normalised (10 digits) by `normalise_mobile`.
- **`access_key` is a random value signed with `SECRET_KEY`** (`apps/queue/keys.py`, salt `counselqueue.student-access`). Rotating `SECRET_KEY` invalidates every live student token link: `/t/{access_key}` pages stop verifying if signatures are checked. Students must then recover the link via the front desk (CQ-26).
- **Collation `utf8mb4_bin`** is used on `Student.access_key`, `OtpCode.code_hash` and `OtpCode.verification_nonce`. These secrets must compare case-sensitively; under `_ci`, `Ab` and `ab` would collide or match. `OtpCode.verification_nonce` is `NULL` until verified, and `UNIQUE` (MySQL allows many NULLs), which makes `verification_id` single-use.
- **Queue fields have a single writer.** `Student.status`, `counsellor`, `queue_at` and `priority` are changed only by `apps/queue/services`. They and the other queue-state fields are read-only in admin.
- **Centre slugs** are auto-generated `city-YYYY-MM-DD[-n]`. If a concurrent insert takes the chosen slug, `Centre.save()` retries once with a fresh slug.

## Models

### Centre (`centres_centre`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `city` | CharField(100) | no |  |
| `venue` | CharField(200) | no |  |
| `date` | DateField | no |  |
| `opens_at` | TimeField | no |  |
| `closes_at` | TimeField | no |  |
| `expected_students` | PositiveIntegerField | no | default 0 |
| `status` | CharField(10) | no | choices: planned / live / closed; default 'planned' |
| `slug` | SlugField(80) | no | unique |
| `front_desk_phone` | CharField(30) | no | blank allowed |
| `created_at` | DateTimeField | no |  |
| `updated_at` | DateTimeField | no |  |

**Constraints:** `centre_closes_after_opens` CHECK (closes_at > opens_at)

**Indexes:** (date, status); (city, date)

### CentreSettings (`centres_centresettings`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `centre` | OneToOne → Centre | no | on_delete=PROTECT; unique |
| `target_session_min` | PositiveSmallIntegerField | no | default 15 |
| `wait_sla_min` | PositiveSmallIntegerField | no | default 30 |
| `recall_limit` | PositiveSmallIntegerField | no | default 2 |
| `whatsapp_enabled` | BooleanField | no | default True |

**Constraints:** `centresettings_recall_limit_gte_1` CHECK (recall_limit >= 1); `centresettings_target_session_gte_1` CHECK (target_session_min >= 1); `centresettings_wait_sla_gte_1` CHECK (wait_sla_min >= 1)

### Counsellor (`counsellors_counsellor`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `name` | CharField(120) | no |  |
| `mobile` | CharField(10) | no |  |
| `streams` | JSONField | no | default list() |
| `expected_session_min` | PositiveSmallIntegerField | no | default 15 |
| `created_at` | DateTimeField | no |  |
| `updated_at` | DateTimeField | no |  |

**Constraints:** `counsellor_expected_session_gte_1` CHECK (expected_session_min >= 1)

### Posting (`counsellors_posting`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `counsellor` | FK → Counsellor | no | on_delete=PROTECT |
| `centre` | FK → Centre | no | on_delete=PROTECT |
| `desk_label` | CharField(40) | no |  |
| `duty` | CharField(10) | no | choices: on_desk / on_break / off_duty; default 'off_duty' |
| `created_at` | DateTimeField | no |  |
| `updated_at` | DateTimeField | no |  |

**Constraints:** `posting_unique_desk_per_centre` UNIQUE (centre, desk_label); `posting_unique_counsellor_per_centre` UNIQUE (counsellor, centre)

**Indexes:** (centre, duty)

### StaffUser (`accounts_staffuser`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `password` | CharField(128) | no |  |
| `last_login` | DateTimeField | yes |  |
| `is_superuser` | BooleanField | no | default False |
| `email` | CharField(254) | no | unique |
| `name` | CharField(120) | no |  |
| `role` | CharField(12) | no | choices: ops_lead / reception / counsellor |
| `centre` | FK → Centre | yes | on_delete=PROTECT |
| `counsellor` | OneToOne → Counsellor | yes | on_delete=PROTECT; unique |
| `title` | CharField(120) | no | blank allowed |
| `is_active` | BooleanField | no | default True |
| `is_staff` | BooleanField | no | default False |
| `date_joined` | DateTimeField | no | default now() |

**Constraints:** `staffuser_counsellor_has_counsellor` CHECK (role = 'counsellor' ⇒ counsellor_id IS NOT NULL); `staffuser_reception_has_centre` CHECK (role = 'reception' ⇒ centre_id IS NOT NULL)

### LoginAttempt (`accounts_loginattempt`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `email` | CharField(254) | no | unique |
| `failed_count` | PositiveIntegerField | no | default 0 |
| `last_failed_at` | DateTimeField | yes |  |

### TokenSequence (`queue_tokensequence`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `centre` | OneToOne → Centre | no | on_delete=PROTECT; unique |
| `last_number` | PositiveIntegerField | no | default 0 |

### Student (`queue_student`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `token` | CharField(16) | no |  |
| `centre` | FK → Centre | no | on_delete=PROTECT |
| `counsellor` | FK → Counsellor | no | on_delete=PROTECT |
| `source` | CharField(4) | no | choices: self / desk; default 'self' |
| `status` | CharField(16) | no | choices: waiting / called / in_session / done / no_show / released / not_counselled; default 'waiting' |
| `name` | CharField(120) | no |  |
| `school` | CharField(200) | no | blank allowed |
| `mobile` | CharField(10) | no |  |
| `parent_mobile` | CharField(10) | no | blank allowed |
| `email` | CharField(254) | no | blank allowed |
| `stream` | CharField(4) | no | choices: PCM / PCB / PCMB / COM / HUM / OTH |
| `klass` | CharField(24) | no | choices: Class 11 / Class 12 / Dropper / repeat year / Graduate / Parent enquiring; blank allowed |
| `course` | CharField(200) | no | blank allowed |
| `exams` | JSONField | no | default list(); blank allowed |
| `clarity` | CharField(32) | no | choices: Very clear / Have shortlisted options / Need help shortlisting / Completely confused; blank allowed |
| `help` | JSONField | no | default list(); blank allowed |
| `consent` | CharField(8) | no | choices: given / pending; default 'pending' |
| `consent_at` | DateTimeField | yes |  |
| `consent_by` | FK → Counsellor | yes | on_delete=PROTECT |
| `checkin_at` | DateTimeField | no | default now() |
| `queue_at` | DateTimeField | no | default now() |
| `priority` | IntegerField | no | default 0 |
| `called_at` | DateTimeField | yes |  |
| `started_at` | DateTimeField | yes |  |
| `ended_at` | DateTimeField | yes |  |
| `recalls` | PositiveSmallIntegerField | no | default 0 |
| `rating` | PositiveSmallIntegerField | yes |  |
| `outcome` | CharField(12) | yes | choices: ready / interested / exploring / not_fit |
| `follow_up_on` | DateField | yes |  |
| `colleges_discussed` | TextField | no | blank allowed |
| `home_city` | CharField(100) | no | blank allowed |
| `target_exam` | CharField(100) | no | blank allowed |
| `budget` | CharField(60) | no | blank allowed |
| `accompanied_by` | CharField(100) | no | blank allowed |
| `access_key` | CharField(100) | no | unique; default make_access_key(); collation utf8mb4_bin |
| `created_at` | DateTimeField | no |  |
| `updated_at` | DateTimeField | no |  |

**Constraints:** `student_unique_token_per_centre` UNIQUE (centre, token); `student_rating_1_to_5` CHECK (rating IS NULL OR 1 <= rating <= 5)

**Indexes:** (centre, status); (centre, mobile); (counsellor, status, queue_at); (centre, checkin_at); (checkin_at)

### SessionRecord (`queue_sessionrecord`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `student` | FK → Student | no | on_delete=PROTECT |
| `counsellor` | FK → Counsellor | no | on_delete=PROTECT |
| `centre` | FK → Centre | no | on_delete=PROTECT |
| `queue_at` | DateTimeField | no |  |
| `called_at` | DateTimeField | yes |  |
| `started_at` | DateTimeField | no |  |
| `ended_at` | DateTimeField | no |  |
| `outcome` | CharField(12) | yes | choices: ready / interested / exploring / not_fit |
| `created_at` | DateTimeField | no |  |

**Constraints:** `sessionrecord_ends_after_start` CHECK (ended_at >= started_at)

**Indexes:** (centre, counsellor, ended_at)

### Note (`queue_note`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `student` | FK → Student | no | on_delete=PROTECT |
| `text` | TextField | no |  |
| `author_name` | CharField(120) | no |  |
| `author` | FK → Counsellor | yes | on_delete=PROTECT |
| `created_at` | DateTimeField | no | default now() |

**Constraints:** `note_text_not_empty` CHECK (text <> '')

### AuditEvent (`queue_auditevent`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `student` | FK → Student | yes | on_delete=PROTECT |
| `centre` | FK → Centre | no | on_delete=PROTECT |
| `verb` | CharField(20) | no | choices: checked_in / called / started / completed / missed / no_show / released / requeued / moved / pulled_forward / consent_given / edited / noted / rated / message_failed / centre_live / centre_closed / exported |
| `actor` | FK → StaffUser | yes | on_delete=PROTECT |
| `on_behalf_of` | FK → Counsellor | yes | on_delete=PROTECT |
| `at` | DateTimeField | no | default now() |
| `data` | JSONField | no | default dict(); blank allowed |

**Indexes:** (centre, at); (student, at)

### Message (`messaging_message`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `student` | FK → Student | yes | on_delete=PROTECT |
| `template` | CharField(24) | no | choices: otp_code / token_confirm_self / token_confirm_desk / consent_request / turn_called / missed_first / missed_final / desk_changed / released / session_done |
| `to` | CharField(16) | no |  |
| `body` | TextField | no |  |
| `status` | CharField(10) | no | choices: queued / sent / delivered / failed; default Message.Status.QUEUED |
| `provider_id` | CharField(100) | no | blank allowed |
| `failure_reason` | CharField(100) | no | blank allowed |
| `created_at` | DateTimeField | no | default now() |
| `updated_at` | DateTimeField | no |  |

**Indexes:** (student, template, status); (provider_id)

### OtpCode (`messaging_otpcode`)

| Field | Type | Null | Notes |
|---|---|---|---|
| `id` | BigAutoField | no | PK |
| `mobile` | CharField(10) | no |  |
| `centre` | FK → Centre | no | on_delete=PROTECT |
| `code_hash` | CharField(128) | no | collation utf8mb4_bin |
| `expires_at` | DateTimeField | no |  |
| `attempts` | PositiveSmallIntegerField | no | default 0 |
| `invalidated_at` | DateTimeField | yes |  |
| `verified_at` | DateTimeField | yes |  |
| `verification_nonce` | CharField(64) | yes | unique; collation utf8mb4_bin |
| `verification_used_at` | DateTimeField | yes |  |
| `created_at` | DateTimeField | no | default now() |

**Indexes:** (centre, mobile, created_at)

## Change log

| Migration(s) | Change |
|---|---|
| `*/0001_initial` | Initial schema: all models above (Task 1 / B0). |
| `*/0002_schema_protect_constraints` | Every FK set to PROTECT. Added CHECKs: session end ≥ start, CentreSettings minimums ≥ 1, counsellor expected_session_min ≥ 1. Added `SessionRecord.queue_at` (backfilled from `Student.queue_at`). `utf8mb4_bin` on access_key, code_hash and verification_nonce. `verification_nonce` made NULL + UNIQUE (`''` backfilled to NULL). `Message.to` max_length 16. Student indexes `(centre, checkin_at)` and `(checkin_at)` (Task 1 fix round 2). |
