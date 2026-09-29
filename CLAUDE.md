# CounselQueue

Queue and counselling-day system for Careers360 counselling drives: student QR self check-in → stream-matched token → WhatsApp turn alerts → counsellor desk → hall board → records and insights.

## Source of truth
- `prd_doc.md`: 61 stories CQ-1…CQ-61 (index: `.claude/skills/counselqueue-domain/references/stories.md`). **PRD wins over prototypes.**
- Prototypes (visual + behaviour reference): `CounselQueue — staff console.html`, `Careers360 counselling — student check-in.html`.
- Open questions and our defaults: `.claude/skills/counselqueue-domain/references/open-questions.md`.

## Stack
- `backend/`: Python 3.9.6 (`backend/.venv`), Django 4.2 LTS, DRF, MySQL 8, SimpleJWT, pytest-django.
- `frontend/`: React 18.2 (`"react": "^18.2.0"`), Vite 5, Node 18.20.3 (`frontend/.nvmrc`), TypeScript, React Router 6, TanStack Query (polling), RHF + Zod, Vitest.
- WhatsApp/OTP via a stub provider. No WebSockets.

## Kit
Skills (`.claude/skills/`): counselqueue-domain · counselqueue-queue-engine · counselqueue-messaging · counselqueue-ui-spec · django-backend-conventions · react-frontend-conventions.
Agents (`.claude/agents/`): django-backend-dev · react-frontend-dev · prd-story-verifier.
Validate the kit: `python3 scripts/check_kit.py`.

## Working agreement
- Each epic gets its own plan (superpowers:writing-plans) in `docs/superpowers/plans/`, executed with superpowers:subagent-driven-development.
- Every acceptance criterion gets a test (`test_cq<id>_*` / `it("CQ-<id> …")`). Run prd-story-verifier before calling an epic done.
- Copy is verbatim from counselqueue-ui-spec. Status changes only through queue services.

## Model routing
Use the cheapest model that can do the job well, and **always pass `model` explicitly when dispatching a subagent** (superpowers Model Selection).

| Level | Setting | Effect |
|---|---|---|
| Session | `.claude/settings.json` → `"model": "opusplan"` | Opus in plan mode (brainstorming, writing-plans, design); Sonnet when executing |
| Subagent fallback | `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` | Any dispatch without an explicit or agent model runs on Sonnet, not the session model |
| Agent | `model:` in `.claude/agents/*.md` | django-backend-dev, react-frontend-dev → sonnet · prd-story-verifier → opus |
| Dispatch | `model` param on the Agent call | Overrides everything above; use it per the table below |

Precedence: Agent-call `model` > agent `model:` > `CLAUDE_CODE_SUBAGENT_MODEL` > session model.

| Task | Model |
|---|---|
| Brainstorming, writing plans, architecture, open-question calls | opus (session in plan mode) |
| Plan task marked `Model: haiku`: 1–2 files, complete spec (copy constants, a serializer, a simple component) | haiku |
| Default implementation task: multi-file, a service + its tests, a screen + its hooks | sonnet |
| Queue-engine / locking / consent / OTP-security tasks, fix-loop rounds 4–5 | opus |
| Explore / codebase search | haiku |
| Per-task review (SDD task reviewer) | sonnet; opus when the task touches locking, state transitions or auth |
| Final whole-branch review, prd-story-verifier | opus |

**Plans carry the choice:** every task in a `docs/superpowers/plans/*` plan has a `**Model:** haiku|sonnet|opus` line under its title, picked with this table. The subagent-driven-development controller dispatches that task's implementer with that model.

## Build roadmap (one plan each, in order)
1. Foundations: scaffold backend + frontend, settings, MySQL, auth, seed_demo, CI commands.
2. E1 Access & roles: CQ-1…5.
3. E2 Centre & counsellor setup: CQ-6…11.
4. E3 Student self check-in + assignment + OTP stub: CQ-12…20 (+ messaging core CQ-54).
5. E6 Counsellor desk: CQ-37…50.
6. E5 Front desk: CQ-29…36.
7. E4 Student queue experience: CQ-21…28.
8. E7 Hall board: CQ-51…53. E8 Messaging remainder: CQ-55…58.
9. E9 Records & insights: CQ-59…61.
