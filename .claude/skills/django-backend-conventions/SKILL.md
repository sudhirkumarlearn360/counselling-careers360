---
name: django-backend-conventions
description: How the CounselQueue backend is built — Django 4.2 LTS + DRF + MySQL project layout, services layer, locking, auth and role permissions, public student API, polling endpoints, CSV export, settings, and pytest-django testing per acceptance criterion. Load before writing or reviewing any code under backend/.
---

# Backend conventions (`backend/`)

## Stack (pin in `requirements.txt`)
`Django>=4.2,<4.3`, `djangorestframework`, `djangorestframework-simplejwt`, `mysqlclient==2.1.0`, `python-dotenv==1.0.0`, `django-cors-headers`; dev: `pytest`, `pytest-django`, `factory-boy`, `freezegun`, `ruff`.

**Python 3.9.6** (pinned, the system `/usr/bin/python3`). The virtualenv is `backend/.venv` (already created with the deps installed). Always run `.venv/bin/python`, `.venv/bin/pytest` and `.venv/bin/ruff` from `backend/`. Resolved pins: Django 4.2.30, djangorestframework 3.16.1, djangorestframework-simplejwt 5.5.1, mysqlclient 2.1.0 (same as cnext-backend-deb), python-dotenv 1.0.0, django-cors-headers 4.9, pytest 8.4, pytest-django 4.11, factory_boy 3.3, freezegun 1.5, ruff 0.16 (`target-version = "py39"`).
Python 3.9 rules: put `from __future__ import annotations` at the top of every module that uses `X | Y` hints or builtin generics in annotations. No `match`, no `zip(strict=)`, no parenthesised multi-item `with`, no `typing.Self`/`TypeAlias`, no `dataclass(slots=True, kw_only=True)`.

## Layout
```
backend/
  manage.py  requirements.txt  pytest.ini  .env.example
  config/settings/{base,local,test}.py  config/urls.py
  apps/
    accounts/    StaffUser (AbstractBaseUser, USERNAME_FIELD=email), login lockout counter, permissions.py (IsOpsLead, IsReception, IsCounsellor, RoleIn(...))
    centres/     Centre (creates its TokenSequence), CentreSettings, services (create/edit/go_live, coverage, duplicate warn); close delegates to `queue.services.close_centre`
    counsellors/ Counsellor, Posting (roster: counsellor×centre, desk_label, duty), services (create, post, set_duty, roster conflicts)
    queue/       Student, TokenSequence, Note, AuditEvent; services/{assignment,tokens,checkin,eta,transitions,consent}.py; selectors.py (read queries)
    messaging/   Message, OtpCode, providers/{base,stub}.py, services.py, templates.py
    insights/    selectors.py (aggregations), export.py (CSV)
    public/      student-facing views (no auth)
    common/      validators.py (normalise_mobile, valid_mobile, valid_email), exception handler
  tests/ mirror apps/, one file per story group: tests/queue/test_cq19_assignment.py …
```

## Rules
- Business logic lives only in `services/` (writes) and `selectors.py` (reads). Views and serializers stay thin: they validate input and call one service. Services raise domain exceptions (`apps.queue.exceptions`), and one DRF exception handler maps them to `400 {"code": ..., "message": <exact ui-spec string>, "data": {...}}`.
- Every write service: `@transaction.atomic`, `select_for_update()` on each row it decides on, and write an `AuditEvent(actor, on_behalf_of)`.
- Time: store UTC (`USE_TZ=True`), `TIME_ZONE="Asia/Kolkata"`. "Today", the centre date and follow-up checks use `timezone.localdate()`.
- Mobile: always `normalise_mobile()` in serializers (`apps/common/validators.py`), and mirror the frontend Zod rules from counselqueue-ui-spec.
- MySQL, configured the same way as cnext-backend-deb: `load_dotenv(".env")` in `config/settings/base.py`, then
  ```python
  DATABASES = {
      "default": {"ENGINE": "django.db.backends.mysql", "NAME": os.getenv("MASTER_DB_NAME", ""), "USER": os.getenv("MASTER_DB_USER", ""),
                  "PASSWORD": os.getenv("MASTER_DB_PASSWORD", ""), "HOST": os.getenv("MASTER_DB_HOST", ""), "PORT": "3306", "CONN_MAX_AGE": 60,
                  "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}, "TEST": {"NAME": "test_counselqueue"}},
      "slave": {... same with SLAVE_DB_* ..., "TEST": {"MIRROR": "default"}},
  }
  ```
  Writes and every locking read (`select_for_update`) go to `default`. Read-only list/report selectors (`ops/students`, `ops/insights`, export) may use `.using("slave")`. Polling reads stay on `default` for read-after-write consistency. JSON fields for exams/help/streams (MySQL 8+ JSON). Index `(centre, status)`, `(centre, mobile)`, `(counsellor, status, queue_at)`.
- Config via `.env` loaded with python-dotenv (`MASTER_DB_*`, `SLAVE_DB_*`, `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `MESSAGING_PROVIDER`, `OTP_*`). Never hard-code credentials.

## Auth & permissions
- Staff: SimpleJWT. `POST /api/1/auth/login` takes `{email, password}`, lowercases and strips the email, returns `{access, refresh, user:{id,name,role,centre,counsellor,default_view}}`. Failures return a generic 400 with the ui-spec string plus `failed_attempts`. The counter is per email, reset on success (CQ-2). `POST /api/1/auth/logout` blacklists the refresh token (CQ-4). `GET /api/1/auth/me`.
- Object scoping lives in querysets: a counsellor sees only their own students (CQ-3/50), reception sees only their centre, and ops sees all. Desk actions by ops take `?as_counsellor=<counsellor_id>` (CQ-5), which sets `on_behalf_of`. Counsellors are rejected if they pass it.
- Export: `IsOpsLead` only (CQ-60).

## API routes (clear, explicit, versioned, the cnext-backend-deb style)
- Every route is an explicit `path("api/<int:version>/<area>/<resource>[/<id>][/<action>]", View.as_view(), name="cq.<area>.<resource>-<action>")`. No routers, no ViewSets, **no trailing slash** (`APPEND_SLASH = False`). Only `version == 1` is served (a mixin returns 404 for other versions).
- **One URL module per area**: `apps/<app>/urls.py`, included from `config/urls.py`. **Area = who calls it**, so the path alone tells you the audience and the permission:
  `auth` (anyone) · `public` (students, no login) · `ops` (ops_lead) · `hall` (reception + ops_lead) · `desk` (counsellor, or an ops_lead with `?as_counsellor=<id>`) · `webhooks` (provider).
- Resources are plural nouns in kebab-case; actions are verbs in kebab-case (`go-live`, `call-next`, `pull-forward`). Path ids: `<int:centre_id>`, `<int:student_id>`, `<int:counsellor_id>`, `<int:posting_id>`, `<slug:centre_slug>`, `<str:access_key>`, `<int:message_id>`.
- Methods: GET reads; POST creates or runs an action; PATCH edits. No PUT or DELETE (nothing is deleted in this release).
- Every response is JSON `{"data": ...}`, or on error `{"code": "...", "message": "<exact ui-spec string>", "data": {...}}`, with 400 validation/domain, 401 unauthenticated, 403 wrong role, 404 not found or not in scope, 409 conflict (duplicate token, busy desk), and 429 throttled. Lists carry `{"data": [...], "count": n, "total": n}`.
- The route table below is the contract. Keep `backend/API_ROUTES.md` generated from it (method, path, name, roles, stories), and add a test that every URL name in the table resolves.

| Method | Path (prefix `/api/1/`) | Name | Who | Stories |
|---|---|---|---|---|
| POST | `auth/login` | cq.auth.login | anyone | 1, 2 |
| POST | `auth/logout` | cq.auth.logout | staff | 4 |
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

Polling endpoints (`public/centres/…`, `public/tokens/…`, `public/board/…`, `hall/centres/…/queue`, `desk/queue`) must be single-query-per-panel (`select_related`/`prefetch_related`), with no N+1, and return in under 100 ms on seed data. Public payloads never include other students' names or mobiles.

## Testing
- pytest-django + factory-boy; `freezegun` for waits and timers. One test per AC, named `test_cq<id>_<behaviour>`. Services are tested directly, views with `APIClient` for permissions and response shape.
- Required cross-cutting tests: role matrix (each role × each endpoint → 200/403), concurrency (two check-ins → distinct tokens), messaging never changes status, stub failure path.
- Commands: `cd backend && pytest -q`, `ruff check .`, `python manage.py makemigrations --check`.
- Seed: `python manage.py seed_demo` recreates the prototype's Gwalior/Indore/Jaipur data and users (passwords only from env in non-local environments).
