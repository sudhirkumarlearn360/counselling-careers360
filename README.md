# counselling-careers360

**CounselQueue** — queue and counselling-day system for Careers360 counselling drives: students scan a QR at the
entrance, check in on their phone (WhatsApp-verified), get a stream-matched token, and are called by WhatsApp and
the hall board; counsellors run their desk; the front desk and operations lead see the whole hall.

- Spec: [prd_doc.md](prd_doc.md) (stories CQ-1…CQ-61) and the two HTML prototypes in the repo root.
- `backend/` — Django 4.2 + DRF + MySQL (Python 3.9.6). 47 explicit, versioned routes: [backend/API_ROUTES.md](backend/API_ROUTES.md). Schema: [backend/SCHEMA.md](backend/SCHEMA.md).
- `frontend/` — React 18.2 + Vite + TypeScript (Node 18.20.3): responsive student flow, staff console, hall board.
- `.claude/` — the Claude Code kit (skills + agents) that encodes the PRD; `python3 scripts/check_kit.py` validates it. Project map: [CLAUDE.md](CLAUDE.md).

**Scope:** Phase 1 is live in the UI; Phase 2 items are built but hidden — see [docs/PHASES.md](docs/PHASES.md).

## Run it locally

```bash
# 1. Database (MySQL 8+): create the DB and a user, then copy backend/.env.example to backend/.env and fill it in
#    (MASTER_DB_* / SLAVE_DB_*, SECRET_KEY, CORS_ALLOWED_ORIGINS=http://localhost:5173, OTP_STUB_CODE=1234 for local).

# 2. Backend  (Python 3.9.6)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo          # demo centres, counsellors, users (password desk123; admin123 for admin@)
.venv/bin/python manage.py runserver 8000

# 3. Frontend  (Node 18.20.3 — see frontend/.nvmrc)
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

Demo entry points (after `seed_demo`):

| Who | URL | Sign in |
|---|---|---|
| Student | `http://localhost:5173/c/gwalior-demo` | none (OTP `1234` in local/stub mode) |
| Front desk | `http://localhost:5173/console/login` | `reception@careers360.com` / `desk123` |
| Counsellor | same | `meera@careers360.com` / `desk123` |
| Operations lead | same | `admin@careers360.com` / `admin123` |
| Hall board | `http://localhost:5173/board/gwalior-demo` | none |

## Checks

```bash
cd backend  && .venv/bin/pytest -q && .venv/bin/ruff check .            # 596 tests
cd frontend && npm test && npm run typecheck && npm run lint && npm run build   # 68 tests
python3 scripts/smoke_e2e.py                                            # a whole counselling day over HTTP (backend running)
```

WhatsApp and OTP go through a stub provider (`MESSAGING_PROVIDER`); nothing is sent to a real number until a real
provider is implemented behind `apps.messaging.providers`.
