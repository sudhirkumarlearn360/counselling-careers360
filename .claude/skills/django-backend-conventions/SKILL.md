---
name: django-backend-conventions
description: How the CounselQueue backend is built — Django 4.2 LTS + DRF + MySQL project layout, services layer, locking, auth and role permissions, public student API, polling endpoints, CSV export, settings, and pytest-django testing per acceptance criterion. Load before writing or reviewing any code under backend/.
---

# Backend conventions (`backend/`)

## Stack (pin in `requirements.txt`)
`Django>=4.2,<4.3`, `djangorestframework`, `djangorestframework-simplejwt`, `mysqlclient`, `django-environ`, `django-cors-headers`; dev: `pytest`, `pytest-django`, `factory-boy`, `freezegun`, `ruff`.

**Python 3.9.6** (pinned, the system `/usr/bin/python3`). The virtualenv is `backend/.venv` (already created with the deps installed). Always run `.venv/bin/python`, `.venv/bin/pytest` and `.venv/bin/ruff` from `backend/`. Resolved pins: Django 4.2.30, djangorestframework 3.16.1, djangorestframework-simplejwt 5.5.1, mysqlclient 2.2.7, django-environ 0.14, django-cors-headers 4.9, pytest 8.4, pytest-django 4.11, factory_boy 3.3, freezegun 1.5, ruff 0.16 (`target-version = "py39"`).
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
- MySQL: `OPTIONS={"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"}`. JSON fields for exams/help/streams (MySQL 8 JSON). Index `(centre, status)`, `(centre, mobile)`, `(counsellor, status, queue_at)`.
- Config via `.env` (`DATABASE_URL`, `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `MESSAGING_PROVIDER`, `OTP_*`). Never hard-code credentials.

## Auth & permissions
- Staff: SimpleJWT. `POST /api/auth/login/` takes `{email, password}`, lowercases and strips the email, returns `{access, refresh, user:{id,name,role,centre,counsellor,default_view}}`. Failures return a generic 400 with the ui-spec string plus `failed_attempts`. The counter is per email, reset on success (CQ-2). `POST /api/auth/logout/` blacklists the refresh token (CQ-4). `GET /api/auth/me/`.
- Object scoping lives in querysets: a counsellor sees only their own students (CQ-3/50), reception sees only their centre, and ops sees all. Desk actions by ops take `?as_counsellor=<id>` (CQ-5), which sets `on_behalf_of`. Counsellors are rejected if they pass it.
- Export: `IsOpsLead` only (CQ-60).

## API map (all under `/api/`)
| Method & path | Role | Stories |
|---|---|---|
| `GET public/centres/{slug}/` | public | 12, 13, 14 |
| `POST public/otp/send/`, `POST public/otp/verify/` | public | 18 |
| `POST public/centres/{slug}/checkins/` | public | 15–20 |
| `GET public/tokens/{access_key}/` · `POST …/release/` · `POST …/consent/` · `POST …/rating/` | public | 21–28, 24 |
| `GET public/board/{slug}/` | public | 51–53 |
| `GET/POST centres/`, `PATCH centres/{id}/`, `POST centres/{id}/go-live/`, `POST centres/{id}/close/` | ops | 6–8, 10 |
| `GET/POST counsellors/`, `PATCH counsellors/{id}/` | ops | 9 |
| `GET/POST counsellors/{id}/postings/`, `PATCH postings/{id}/` (response carries roster-conflict warnings) | ops | 9, 11 |
| `POST postings/{id}/duty/` | counsellor (own posting), ops | 37 |
| `GET centres/{id}/hall/?q=&counsellor=` | reception, ops | 31–34, 58 |
| `POST centres/{id}/checkins/` | reception | 29, 30 |
| `GET desk/queue/` · `POST desk/call-next/` · `POST desk/call-token/` | counsellor (ops as_counsellor) | 38–41 |
| `GET students/{id}/` (record + audit trail + messages) | reception (own centre), counsellor (own), ops | 30, 36, 58 |
| `POST students/{id}/{start,complete,missed,pull-forward,consent}/` | counsellor (own desk), ops (as_counsellor) | 41, 42, 46, 49 |
| `POST students/{id}/move/`, `POST students/{id}/requeue/` | reception (own centre), ops | 35, 36 |
| `PATCH students/{id}/` · `POST students/{id}/notes/` | counsellor (own), ops (as_counsellor) | 44, 45, 48 |
| `POST students/{id}/messages/{mid}/resend/` | reception (own centre), counsellor (own), ops | 58 |
| `POST messaging/status/` (provider webhook, signed) | provider | 58 |
| `GET students/?filters` · `GET students/export.csv` | ops (counsellor: own) | 50, 59, 60 |
| `GET insights/?centre=` | ops | 61 |
| `GET live/` | ops | 5 |

Polling endpoints (`public/tokens`, `public/board`, `hall`, `desk/queue`, `public/centres`) must be single-query-per-panel (`select_related`/`prefetch_related`), with no N+1, and return in under 100 ms on seed data.

## Testing
- pytest-django + factory-boy; `freezegun` for waits and timers. One test per AC, named `test_cq<id>_<behaviour>`. Services are tested directly, views with `APIClient` for permissions and response shape.
- Required cross-cutting tests: role matrix (each role × each endpoint → 200/403), concurrency (two check-ins → distinct tokens), messaging never changes status, stub failure path.
- Commands: `cd backend && pytest -q`, `ruff check .`, `python manage.py makemigrations --check`.
- Seed: `python manage.py seed_demo` recreates the prototype's Gwalior/Indore/Jaipur data and users (passwords only from env in non-local environments).
