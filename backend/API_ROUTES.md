# CounselQueue API routes (contract)

Copied from `.claude/skills/django-backend-conventions/SKILL.md` ("API routes"). This is the contract for Tasks 2–7.
`tests/test_routes.py` holds the same names and paths; a name is marked pending there until its endpoint exists.

Rules (summary):
- Explicit `path("api/<int:version>/<area>/<resource>[/<id>][/<action>]", View.as_view(), name="cq.<area>.<...>")`. No routers or ViewSets, **no trailing slash** (`APPEND_SLASH = False`).
- Only `version == 1` is served. Views subclass `apps.common.views.ApiView`, which returns 404 for any other version.
- One URL module per area (area = who calls it): `auth` → `apps/accounts/urls.py`, `public` → `apps/public/urls.py`, `ops` → `apps/ops/urls.py`, `hall` → `apps/hall/urls.py`, `desk` → `apps/desk/urls.py`, `webhooks` → `apps/messaging/urls.py`. All are included from `config/urls.py`.
- GET reads, POST creates or runs an action, PATCH edits. No PUT or DELETE.
- Responses: `{"data": ...}`; lists `{"data": [...], "count": n, "total": n}`; errors `{"code", "message", "data"}` with 400 / 401 / 403 / 404 / 409 / 429.
- Warnings: successful writes may add `"warnings": [{"code", "message"}]` beside `data` (objects, not strings).
- 409 `needs_confirmation`: allowed but must be confirmed. `data.waiting_count` (close) or `data.uncovered_streams` (go-live); repeat the request with `{"confirm": true}`.
- Wrong-state actions (go-live when not planned, close when not live, edit a closed centre) are 400 with a `code` (`not_planned`, `not_live`, `centre_closed`).

| Method | Path (prefix `/api/1/`) | Name | Who | Stories |
|---|---|---|---|---|
| POST | `auth/login` | cq.auth.login | anyone | 1, 2 |
| POST | `auth/logout` | cq.auth.logout | anyone (refresh token in body) | 4 |
| POST | `auth/refresh` | cq.auth.refresh | staff | 1 |
| GET | `auth/me` | cq.auth.me | staff | 1, 3 |
| GET | `public/centres/<centre_slug>` | cq.public.centre-detail | student | 12, 13, 14 |
| POST | `public/centres/<centre_slug>/otp/send` | cq.public.otp-send | student | 18 |
| POST | `public/centres/<centre_slug>/otp/verify` | cq.public.otp-verify | student | 18 |
| POST | `public/centres/<centre_slug>/check-in` | cq.public.check-in | student | 15–20, 54 |
| GET | `public/tokens/<access_key>` | cq.public.token-detail | student | 19, 21–28 |
| POST | `public/tokens/<access_key>/release` | cq.public.token-release | student | 25 |
| POST | `public/tokens/<access_key>/consent` | cq.public.token-consent | student | 24 |
| POST | `public/tokens/<access_key>/rating` | cq.public.token-rating | student | 28 |
| GET | `public/board/<centre_slug>` | cq.public.board | anyone (hall screen) | 51–53 |
| GET | `ops/live` | cq.ops.live | ops_lead | 5 |
| GET, POST | `ops/centres` | cq.ops.centres | ops_lead | 6 |
| GET, PATCH | `ops/centres/<centre_id>` | cq.ops.centre-detail | ops_lead | 7, 10 |
| POST | `ops/centres/<centre_id>/go-live` | cq.ops.centre-go-live | ops_lead | 8, 10 |
| GET, POST | `ops/centres/<centre_id>/close` | cq.ops.centre-close | ops_lead | 8 (GET = preview of waiting count) |
| GET, POST | `ops/counsellors` | cq.ops.counsellors | ops_lead | 9, 11 |
| GET, PATCH | `ops/counsellors/<counsellor_id>` | cq.ops.counsellor-detail | ops_lead | 9 |
| GET, POST | `ops/counsellors/<counsellor_id>/postings` | cq.ops.counsellor-postings | ops_lead | 9, 11 |
| PATCH | `ops/postings/<posting_id>` | cq.ops.posting-detail | ops_lead | 9, 11 |
| GET | `ops/students` | cq.ops.students | ops_lead | 59 |
| GET | `ops/students/export` | cq.ops.students-export | ops_lead | 60 (CSV) |
| GET | `ops/insights` | cq.ops.insights | ops_lead | 61 |
| GET | `hall/centres/<centre_id>/queue` | cq.hall.queue | reception, ops_lead | 31–34, 58 |
| POST | `hall/centres/<centre_id>/check-in` | cq.hall.check-in | reception, ops_lead | 29, 30 |
| GET | `hall/students/<student_id>` | cq.hall.student-detail | reception, ops_lead | 30, 36, 58 (record + audit + messages) |
| POST | `hall/students/<student_id>/move` | cq.hall.student-move | reception, ops_lead | 35 |
| POST | `hall/students/<student_id>/requeue` | cq.hall.student-requeue | reception, ops_lead | 36 |
| POST | `hall/students/<student_id>/messages/<message_id>/resend` | cq.hall.message-resend | reception, ops_lead | 58 |
| GET | `desk/queue` | cq.desk.queue | counsellor, ops_lead† | 38 |
| POST | `desk/duty` | cq.desk.duty | counsellor, ops_lead† | 37 |
| POST | `desk/call-next` | cq.desk.call-next | counsellor, ops_lead† | 39 |
| POST | `desk/call-token` | cq.desk.call-token | counsellor, ops_lead† | 40 |
| GET, PATCH | `desk/students/<student_id>` | cq.desk.student-detail | counsellor, ops_lead† | 43, 44, 48 |
| POST | `desk/students/<student_id>/start` | cq.desk.student-start | counsellor, ops_lead† | 42, 47 |
| POST | `desk/students/<student_id>/complete` | cq.desk.student-complete | counsellor, ops_lead† | 49 |
| POST | `desk/students/<student_id>/missed` | cq.desk.student-missed | counsellor, ops_lead† | 46 |
| POST | `desk/students/<student_id>/pull-forward` | cq.desk.student-pull-forward | counsellor, ops_lead† | 41 |
| POST | `desk/students/<student_id>/consent` | cq.desk.student-consent | counsellor, ops_lead† | 42 (verbal) |
| POST | `desk/students/<student_id>/consent-request` | cq.desk.student-consent-request | counsellor, ops_lead† | 42 (resend WhatsApp) |
| POST | `desk/students/<student_id>/notes` | cq.desk.student-notes | counsellor, ops_lead† | 45 |
| POST | `desk/students/<student_id>/messages/<message_id>/resend` | cq.desk.message-resend | counsellor, ops_lead† | 58 |
| GET | `desk/my-students` | cq.desk.my-students | counsellor, ops_lead† | 50 |
| GET | `desk/my-centres` | cq.desk.my-centres | counsellor | 50 |
| POST | `webhooks/messaging/status` | cq.webhooks.messaging-status | provider (signed) | 58 |

† An ops_lead passes `?as_counsellor=<counsellor_id>` (CQ-5). This sets `on_behalf_of` and is rejected (403) for counsellors.

## Request / response reference (what the frontend sends and reads)

All bodies are JSON. Success: `{"data": ...}` (+ `"warnings": [{code,message}]`, `"message"`, and for lists
`"count"` and `"total"`). Error: `{"code","message","data"}` with the exact UI string in `message`. Validation
errors (`code: "invalid"`) carry `data.fields = {field: message}` for **every** failing field.

### public (no login)
| Route | Body → data |
|---|---|
| `GET public/centres/<slug>` | → `centre{id,city,venue,date,opens_at,closes_at,status,front_desk_phone}`, `open`, `message`, `stats{waiting,counsellors_on_site,avg_wait_min\|null,avg_wait_label}`, `steps[]`, `bring[]`, `bring_note` |
| `POST …/otp/send` | `{mobile}` → `{resend_after_sec, expires_in_min}`; 429 `otp_resend_wait` `{retry_after}` |
| `POST …/otp/verify` | `{mobile, code}` → `{verification_id}`; 400 `otp_mismatch` (`data.attempts_left`) / `otp_expired` |
| `POST …/check-in` | `{name,school,mobile,parent_mobile,email,stream,klass,course,exams[],clarity,help[],consent:true,verification_id}` → 201 `{access_key, token{…}}`; 409 `duplicate_token` (`data.access_key`, `data.token`); 400 `verification_required` |
| `GET public/tokens/<key>` | → `token,status,state{kind: waiting\|next\|called\|in_session\|done\|no_show\|released\|not_counselled, ahead?,minutes?,expected_at?,approximate?},stream_name,name,mobile,counsellor,desk,venue,city,date,closes_at,front_desk_phone,checked_in_at,consent,rating,can_release,can_rate` |
| `POST …/release` `…/consent` | → token payload |
| `POST …/rating` | `{rating:1-5}` → token payload; 409 `already_rated` |
| `GET public/board/<slug>` | → `centre, now, total_waiting, panels[{desk,counsellor,duty,serving\|null,next\|null,waiting,line}], recently_called[], recently_called_empty, standing_line` |

### hall (reception own centre; ops any)
`GET hall/centres/<id>/queue?q=&counsellor=` → `header{waiting,late,wait_promise_min}`, `tabs[{key,label,counsellor_id,count,late,duty?}]`,
`rows[{id,token,name,mobile,stream,status,source,counsellor{id,name,desk},checked_in_at,waited_min,late,consent_pending,recalls,alert_failed,alert_failed_message}]`, `query`, `count`.
`POST hall/centres/<id>/check-in` `{name,mobile,stream,help[],…optional…,counsellor_id?,confirm?}` → 201 `data`=student, `message` "Token … issued to …".
`GET hall/students/<id>` → student + `audit[]` + `messages[]`. `POST …/move` `{counsellor_id,confirm?}`; `POST …/requeue`; `POST …/messages/<id>/resend`.

### desk (counsellor; ops with `?as_counsellor=<id>`)
`GET desk/queue` → `centre|null, message?, desk, duty, counsellor, figures{in_queue,waiting_hall,counselled_today,avg_session_min|null,target_session_min,late,wait_promise_min}, next_token, current{student + timer}, queue[{id,token,name,stream,klass,waited_min,source,consent_pending,late,next}]`.
Actions return the refreshed desk payload (+ `called`, `warnings`, `message`, `next_token_after`): `POST desk/call-next`, `desk/call-token {token}`, `desk/students/<id>/{start,complete,missed,pull-forward,consent}`.
`GET|PATCH desk/students/<id>` (PATCH: name,school,mobile,parent_mobile,email,stream,klass,course,clarity,home_city,target_exam,budget,colleges_discussed,accompanied_by,outcome,follow_up_on).
`POST …/notes {text}`, `…/consent-request`, `…/messages/<id>/resend`. `GET desk/my-students`, `desk/my-centres`. `POST desk/duty {duty}`.

### ops
`GET ops/students?q=&counsellor=&centre=&stream=&status=&limit=&offset=` → rows + `count` (matched) + `total`. `GET ops/students/export` (same filters) → `text/csv`. `GET ops/insights?centre=`.
