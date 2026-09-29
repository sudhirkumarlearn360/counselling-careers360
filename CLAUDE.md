# CounselQueue

Queue and counselling-day system for Careers360 counselling drives: student QR self check-in → stream-matched token → WhatsApp turn alerts → counsellor desk → hall board → records and insights.

## Source of truth
- `prd_doc.md`: 61 stories CQ-1…CQ-61 (index: `.claude/skills/counselqueue-domain/references/stories.md`). **PRD wins over prototypes.**
- Prototypes (visual + behaviour reference): `CounselQueue — staff console.html`, `Careers360 counselling — student check-in.html`.
- Open questions and our defaults: `.claude/skills/counselqueue-domain/references/open-questions.md`.

## Stack
- `backend/`: Django 4.2 LTS, DRF, MySQL 8, SimpleJWT, pytest-django.
- `frontend/`: React 19, Vite, TypeScript, React Router, TanStack Query (polling), RHF + Zod, Vitest.
- WhatsApp/OTP via a stub provider. No WebSockets.

## Kit
Skills (`.claude/skills/`): counselqueue-domain · counselqueue-queue-engine · counselqueue-messaging · counselqueue-ui-spec · django-backend-conventions · react-frontend-conventions.
Agents (`.claude/agents/`): django-backend-dev · react-frontend-dev · prd-story-verifier.
Validate the kit: `python3 scripts/check_kit.py`.

## Working agreement
- Each epic gets its own plan (superpowers:writing-plans) in `docs/superpowers/plans/`, executed with superpowers:subagent-driven-development.
- Every acceptance criterion gets a test (`test_cq<id>_*` / `it("CQ-<id> …")`). Run prd-story-verifier before calling an epic done.
- Copy is verbatim from counselqueue-ui-spec. Status changes only through queue services.

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
