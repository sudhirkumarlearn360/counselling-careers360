# CounselQueue Full Build: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax. Each task has a **Model** line (CLAUDE.md → Model routing), which is the model its implementer is dispatched with.

**Goal:** Build the complete CounselQueue product: Django 4.2 REST APIs for every CQ-1…CQ-61 story, and a React 18.2 frontend (student check-in, token page, staff console for 3 roles, hall board).

**Architecture:** `backend/` is Django 4.2 + DRF + MySQL. Business rules live in services, and only queue services change student status. `frontend/` is React 18.2 + Vite + TS + React Router 6 + TanStack Query polling. The API contract is the API map in `django-backend-conventions`. The frontend builds against it, using MSW mocks until the real endpoint exists.

**Tech Stack:** Django>=4.2,<4.3 · DRF · SimpleJWT · mysqlclient · pytest-django · React ^18.2.0 · Vite 5 · TanStack Query 5 · RHF + Zod · Vitest + RTL + MSW.

**Spec:** `prd_doc.md`. The detailed, binding rules are in the project skills (`.claude/skills/*`): domain, queue-engine, messaging, ui-spec, and the backend/frontend conventions. **Ruling:** this plan does not inline code. The skills are the spec-level code guidance, and each implementer writes tests from the ACs first (TDD). Inlining 61 stories of code would duplicate the skills and drift from them.

## Global Constraints
- Django `>=4.2,<4.3`; React `"^18.2.0"` (never 19); **Python 3.9.6** (`backend/.venv`, deps installed; use `.venv/bin/…`; py39 syntax only); **Node 18.20.3** (`frontend/.nvmrc`; run npm with `export PATH="$HOME/.nvm/versions/node/v18.20.3/bin:$PATH"`); MySQL 9 local (`backend/.env` → `DATABASE_URL`, already created; the test DB is `test_counselqueue`).
- Exact copy from `counselqueue-ui-spec` / `counselqueue-messaging`. Status changes only via `apps/queue/services`.
- Every AC gets a test: `test_cq<id>_*` (backend) or `it("CQ-<id> …")` (frontend).
- Commit per story group. **Backend agents `git add backend/` only; frontend agents `git add frontend/` only** (they run in parallel in one working tree). If a commit hits `index.lock`, retry after 2s.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus
1. Two check-ins racing at one centre → distinct tokens; same mobile → one token + DuplicateToken (B3 test, real MySQL, `TransactionTestCase`).
2. Role scoping across every endpoint → role × endpoint matrix test (B1 creates it, and each later B task adds its endpoints).
3. An ops lead on a counsellor's desk → the note is authored as the counsellor, and the audit has actor = lead, on_behalf_of = counsellor (B5 test).
4. Student token page polling after a status change → the UI state flips without reload (F2 test with fake timers + MSW).
5. Mobile typed with spaces or +91 → normalised the same in the Zod schema and the serializer (B4 + F2 tests share fixtures: `"+91 98110 22001"` → `9811022001`).

---

### Task B0: Backend foundation + all models
**Model:** opus · **Agent:** django-backend-dev
**Files:** `backend/{manage.py,requirements.txt,pytest.ini,.env.example,config/**,apps/*/models.py,apps/*/migrations/**,apps/common/**,apps/*/admin.py}`, `backend/tests/test_models.py`, `apps/queue/management/commands/seed_demo.py`
**Produces:** every model from counselqueue-domain (Centre, CentreSettings, Counsellor, Posting, StaffUser, Student, SessionRecord, TokenSequence, Note, AuditEvent, Message, OtpCode); `apps.common.validators.normalise_mobile/valid_mobile/valid_email`; a DRF exception handler returning `{code,message,data}`; `seed_demo` (the prototype's Gwalior live / Indore / Jaipur data + users: admin@, reception@, meera@… with password `desk123`, local only).
- [ ] Write failing tests: model constraints (unique centre+desk_label, unique counsellor+centre posting), TokenSequence auto-created with Centre, normalise_mobile table (`"+91 98110 22001"`→`9811022001`, `"098110 22001"`→`9811022001`, `"12345"` invalid), and seed_demo is idempotent.
- [ ] Implement the settings split (base/local/test), MySQL utf8mb4, TZ Asia/Kolkata, CORS, JWT, apps.
- [ ] `pytest -q`, `ruff check .`, `python manage.py makemigrations --check`, `python manage.py migrate && python manage.py seed_demo` all pass. Commit.

### Task B1: E1 Access & roles (CQ-1…5)
**Model:** sonnet · **Agent:** django-backend-dev · **Depends:** B0
**Produces:** `POST /api/auth/login/`, `/logout/`, `/refresh/`, `GET /api/auth/me/` (with `default_view`, `nav`, current posting); permissions `RoleIn`; `as_counsellor` desk-context mixin; `GET /api/live/`; `tests/test_role_matrix.py` (a parametrised role × endpoint table that later tasks extend).
- [ ] Failing tests for every CQ-1…5 AC (generic error, email normalised, failed counter + helpdesk flag on the 3rd, reset on success, logout blacklists refresh, the counsellor can't use as_counsellor). Implement. pytest/ruff green. Commit.

### Task B2: E2 Centre & counsellor setup (CQ-6…11)
**Model:** sonnet · **Agent:** django-backend-dev · **Depends:** B1
**Produces:** centres CRUD, go-live (uncovered-stream warning with a `confirm` flag), close (waiting count preview + confirm → `queue.services.close_centre`), coverage; counsellors CRUD; postings CRUD with roster-conflict warnings; `postings/{id}/duty/`.
- [ ] Failing tests per AC, then implement. Green. Commit.

### Task B3: Queue engine services (CQ-19, 20, 21, 25, 33, 35, 36, 39, 40, 41, 42, 46, 47, 49, 8-close)
**Model:** opus · **Agent:** django-backend-dev · **Depends:** B2
**Produces:** every function in counselqueue-queue-engine (`assign_counsellor`, `next_token`, `check_in`, `eta_for`, `call_next`, `call_token`, `start_session`, `complete_session`, `mark_missed`, `release`, `requeue`, `move`, `pull_forward`, `record_consent`, `close_centre`, `set_duty`, `is_late`) + metrics selectors; `apps/messaging/services.send_template` + StubProvider + templates (used by the services).
- [ ] Failing service-level tests per AC, including the concurrency races (TransactionTestCase, threads) and "messaging never changes status". Implement. Green. Commit.

### Task B4: Public student API + OTP (CQ-12…28, 54, 57)
**Model:** opus · **Agent:** django-backend-dev · **Depends:** B3
**Produces:** `public/centres/{slug}/`, `public/otp/send|verify/`, `public/centres/{slug}/checkins/`, `public/tokens/{access_key}/` (+ release, consent, rating), `public/board/{slug}/`; throttles; the OTP binding rules; payloads with no other students' PII.
- [ ] Failing API tests per AC (the not-live/closed messages, all field errors together, OTP wrong/expired/resend/max attempts, verification bound to the mobile, duplicate returns the live token only after verification, rating once). Implement. Green. Commit.

### Task B5: Front desk + counsellor desk APIs (CQ-29…50, 55, 56, 58)
**Model:** sonnet · **Agent:** django-backend-dev · **Depends:** B3
**Produces:** `centres/{id}/hall/` (tabs counts, late, search incl. last-4, all statuses for search), `centres/{id}/checkins/` (desk), `students/{id}/` detail + audit + messages, the move/requeue/start/complete/missed/pull-forward/consent/notes/PATCH/resend endpoints, `desk/queue|call-next|call-token/`, my students, my centres.
- [ ] Failing API tests per AC + role-matrix rows + the ops-on-desk attribution test. Implement. Green. Commit.

### Task B6: Records, export, insights, board polish (CQ-51…53, 59…61)
**Model:** sonnet · **Agent:** django-backend-dev · **Depends:** B5
**Produces:** `students/` filters + count/total, `students/export.csv` (ops only, filtered, filename, formula-injection escaped, audit row), `insights/`, board payload states (break "back shortly", off duty closed, "queue clear", last 6 called).
- [ ] Failing tests per AC. Implement. Green. Commit.

### Task F0: Frontend foundation
**Model:** sonnet · **Agent:** react-frontend-dev · **Depends:** none (runs parallel with B0–B2)
**Produces:** a Vite React 18.2 TS app in `frontend/` with the exact pins from react-frontend-conventions; tokens.css (both palettes + dark mode); api/client.ts (JWT, `{code,message}` errors, `VITE_API_URL` default `http://localhost:8000/api`); the router with all routes as lazy stubs; RequireRole + lib/nav.ts; lib/mobile.ts (`normaliseMobile` with the same fixtures as B0); lib/format.ts; MSW setup; the Vitest config.
- [ ] Failing tests (normaliseMobile fixtures, nav matrix per role, RequireRole redirects to the default view). Implement. `npm test`, `npm run typecheck`, `npm run lint`, `npm run build` green. Commit.

### Task F1: Sign-in, shell, sign-out, desk banner (CQ-1…5)
**Model:** sonnet · **Agent:** react-frontend-dev · **Depends:** F0 (API: B1)
- [ ] Tests per UI AC (blank error, generic error keeps the email and clears the password, the toggle defaults to hidden, helpdesk on the 3rd, landing per role, sign-out replace-nav + cache cleared, desk banner copy). Implement. Green. Commit.

### Task F2: Student flow + token page (CQ-12…28)
**Model:** sonnet · **Agent:** react-frontend-dev · **Depends:** F0 (API: B4)
- [ ] Tests per AC (landing states, hall stats "—", 4-step progress, all errors together, None-exclusive exams, back keeps values, consent block, OTP wrong/resend countdown/change number, duplicate shows the live token, token states incl. next/called/in session/done+rating/no-show/released, release confirm, access_key recovery, polling flips state). Mobile-first 320px. Implement. Green. Commit.

### Task F3: Front desk + counsellor desk screens (CQ-29…50)
**Model:** sonnet · **Agent:** react-frontend-dev · **Depends:** F1 (API: B5)
- [ ] Tests per AC (hall tabs/late/search/move/requeue, add student + duplicate link, my queue header/duty/call/call-token/pull-forward, live session intake/edit/notes/timer/consent gate/outcome/complete, my students/centres). Implement. Green. Commit.

### Task F4: Ops screens + hall board (CQ-5…11, 51…53, 59…61)
**Model:** sonnet · **Agent:** react-frontend-dev · **Depends:** F1 (API: B2, B6)
- [ ] Tests per AC (live centres + open desk, centre form/go-live warning/close confirm, counsellors + postings + conflicts, all students filters/count/export, insights "—" and n, board panels/states/recent 6/standing line). Implement. Green. Commit.

### Task V: Verification + integration
**Model:** opus · **Agent:** prd-story-verifier per epic, then a final whole-branch review
- [ ] After each B/F pair, run prd-story-verifier for that epic's CQ ids. Any FAIL or MISSING goes back to the implementer (SDD fix loop).
- [ ] Integration smoke: `backend: migrate, seed_demo, runserver 8000`; `frontend: npm run dev`. Script the flow with curl against the real API: sign in as reception → desk check-in → sign in as meera → call → start (after consent) → complete → board shows it → export as admin. Everything must succeed.
- [ ] Final review (opus) on the whole branch, then one fix pass.
