# CounselQueue Claude Code Kit: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **On approval:** copy this file to `counselling/docs/superpowers/plans/2026-09-29-counselqueue-kit.md` (Task 0) so it lives with the project.

**Goal:** Create a project-level `.claude/` kit (6 skills, 3 agents, CLAUDE.md, and a validator). It encodes the CounselQueue PRD and prototypes so that later plans can build a Django 4.2 backend and a React frontend story by story.

**Architecture:** Domain knowledge lives in skills (the single source of truth that agents load). Agents are thin role definitions: a backend builder, a frontend builder, and a read-only story verifier. A Python validator (`scripts/check_kit.py`) is the test suite for the kit. It checks frontmatter, coverage of all 61 stories, and every exact user-facing string in the PRD.

**Tech Stack:** Markdown skills and agents (Claude Code format), Python 3 stdlib validator. Target app stack recorded in the kit: Django 4.2 LTS + DRF + MySQL 8 + pytest-django, and React 19 + Vite + TypeScript + React Router + TanStack Query + Zod + Vitest. Live updates use polling. WhatsApp and OTP sit behind a stub provider.

**Spec:** `counselling/prd_doc.md` (CQ-1 to CQ-61) plus the prototypes `counselling/CounselQueue — staff console.html` and `counselling/Careers360 counselling — student check-in.html`.

## Global Constraints
- Project root: `/Users/sudhir/Documents/1Office_projects/counselling`. All paths below are relative to it.
- **The PRD wins over the prototypes** whenever they disagree. Divergences are listed in the queue-engine skill.
- Backend: Django **4.2** LTS, DRF, **MySQL** (utf8mb4), `TIME_ZONE="Asia/Kolkata"`, `USE_TZ=True`.
- Frontend: React **19**, Vite, TypeScript strict.
- Live data uses **polling only** (no WebSockets/Channels): 5s for token, board and queues; 10s for hall stats.
- WhatsApp and OTP always go through `messaging.providers` with a **stub** backend by default. No real provider in this release.
- Roles are exactly `ops_lead`, `reception`, `counsellor` (the prototype's `superadmin` = `ops_lead`).
- Streams are exactly: `PCM` Science – PCM, `PCB` Science – PCB, `PCMB` Science – PCMB, `COM` Commerce, `HUM` Humanities / Arts, `OTH` Other.
- Settings defaults: target session 15 min, wait promise 30 min, recall limit 2.
- User-facing copy is used **verbatim** from `counselqueue-ui-spec` / `counselqueue-messaging`.
- Every acceptance criterion gets a test named `test_cq<id>_<behaviour>` (backend) or `it("CQ-<id> …")` (frontend).

## Review Focus
1. **Concurrent check-ins at the same centre**: two students submit at the same second. Expected: distinct token numbers, and nobody is double-assigned past load. The queue-engine skill must mandate `select_for_update` on `TokenSequence` and on counsellor rows. The validator checks that the phrase `select_for_update` appears in the queue-engine and backend-conventions skills (Task 3, Task 6).
2. **Mobile numbers typed with spaces or +91** (the prototype seeds `"98110 22001"`). Expected: normalise to 10 digits before validation and duplicate checks. The skill must state the normalisation rule. The validator checks for `normalise_mobile` (Task 5).
3. **The operations lead acting on a counsellor's desk** (CQ-5). Expected: the note is attributed to the counsellor, but the audit keeps the real actor. The domain skill must define `AuditEvent.actor` + `on_behalf_of`. The validator checks for `on_behalf_of` (Task 2).
4. **A released token is called by number** (the prototype allows this). Expected: rejected as released, with a route to rejoin (CQ-40). The queue-engine divergence list must include it. The validator checks for `released` in the divergence section (Task 3).
5. **Clock and timezone**: centre times are local IST, and a follow-up date "not in the past" uses the IST date. The conventions skill must state "compare against `timezone.localdate()`". The validator checks for `localdate` (Task 6).

---

## File Structure

| Path | Responsibility |
|---|---|
| `scripts/check_kit.py` | Validator: the kit's test suite |
| `.gitignore` | Standard Python/Node ignores |
| `CLAUDE.md` | Project map, working agreement, kit index, build roadmap |
| `.claude/skills/counselqueue-domain/SKILL.md` | Glossary, entities, enums, state machine, roles and navigation, audit |
| `.claude/skills/counselqueue-domain/references/stories.md` | Index of all 61 stories: epic, rule summary, dependencies |
| `.claude/skills/counselqueue-domain/references/open-questions.md` | PRD open questions + defaults we assume |
| `.claude/skills/counselqueue-queue-engine/SKILL.md` | Assignment, tokens, ETA, duplicates, all transitions and guards |
| `.claude/skills/counselqueue-queue-engine/references/prototype-engine.md` | Prototype JS logic, annotated, with divergences |
| `.claude/skills/counselqueue-messaging/SKILL.md` | Provider interface, templates, triggers, OTP, delivery failure |
| `.claude/skills/counselqueue-ui-spec/SKILL.md` | Validation rules + every exact UI string |
| `.claude/skills/counselqueue-ui-spec/references/screens.md` | Screen-by-screen spec per role / student step |
| `.claude/skills/counselqueue-ui-spec/references/design-tokens.md` | CSS variables + fonts from both prototypes |
| `.claude/skills/django-backend-conventions/SKILL.md` | Backend layout, patterns, API map, testing |
| `.claude/skills/react-frontend-conventions/SKILL.md` | Frontend layout, routing, polling, forms, testing |
| `.claude/agents/django-backend-dev.md` | Backend builder agent |
| `.claude/agents/react-frontend-dev.md` | Frontend builder agent |
| `.claude/agents/prd-story-verifier.md` | Read-only acceptance-criteria verifier |

---

### Task 0: Repo init + validator (tests first)

**Files:**
- Create: `.gitignore`, `scripts/check_kit.py`, `docs/superpowers/plans/2026-09-29-counselqueue-kit.md` (copy of this plan)

**Interfaces:**
- Produces: `python3 scripts/check_kit.py [--only skills|agents|stories|strings|claude|focus]`. It exits 0 and prints `kit OK` when clean. Otherwise it prints one `FAIL: …` line per problem and exits 1. Later tasks run it to go red→green.

- [ ] **Step 1: Init git and ignores**

```bash
cd /Users/sudhir/Documents/1Office_projects/counselling
git init
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.venv/
.env
node_modules/
dist/
.DS_Store
.pytest_cache/
coverage/
EOF
mkdir -p docs/superpowers/plans scripts
cp /Users/sudhir/.claude/plans/cryptic-gathering-teacup.md docs/superpowers/plans/2026-09-29-counselqueue-kit.md
```

- [ ] **Step 2: Write the validator**

`scripts/check_kit.py`:
```python
#!/usr/bin/env python3
"""Validate the CounselQueue Claude Code kit against prd_doc.md."""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRD = (ROOT / "prd_doc.md").read_text()
SK = ROOT / ".claude" / "skills"
AG = ROOT / ".claude" / "agents"

SKILLS = [
    "counselqueue-domain", "counselqueue-queue-engine", "counselqueue-messaging",
    "counselqueue-ui-spec", "django-backend-conventions", "react-frontend-conventions",
]
AGENTS = ["django-backend-dev", "react-frontend-dev", "prd-story-verifier"]

# Exact user-facing copy from the PRD; must appear verbatim in ui-spec or messaging.
EXACT = [
    "Enter your work email and password",
    "That email and password don't match an account.",
    "City and venue are both needed.",
    "A name and at least one stream are needed.",
    "This centre isn't open for check-in",
    "A 10-digit mobile number is needed for the turn alert.",
    "Tick the consent line so a counsellor can advise you",
    "That code doesn't match — check your WhatsApp",
    "A token is already open for this number — {token}.",
    "No token {token} at this centre today.",
    "back shortly",
    "queue clear",
    "None / not sure",
]
# (file relative to SK, phrase) pairs pinned by the plan's Review Focus.
FOCUS = [
    ("counselqueue-queue-engine/SKILL.md", "select_for_update"),
    ("django-backend-conventions/SKILL.md", "select_for_update"),
    ("counselqueue-ui-spec/SKILL.md", "normalise_mobile"),
    ("counselqueue-domain/SKILL.md", "on_behalf_of"),
    ("django-backend-conventions/SKILL.md", "localdate"),
]
TEMPLATES = [
    "token_confirm_self", "token_confirm_desk", "otp_code", "turn_called",
    "missed_first", "missed_final", "desk_changed", "released",
    "session_done", "consent_request",
]


def read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def check_skills(errs):
    for s in SKILLS:
        p = SK / s / "SKILL.md"
        if not p.exists():
            errs.append(f"missing skill {s}")
            continue
        fm = frontmatter(read(p))
        if fm.get("name") != s or not fm.get("description"):
            errs.append(f"bad frontmatter in {p.relative_to(ROOT)}")
        for ref in re.findall(r"\]\((references/[^)]+)\)", read(p)):
            if not (p.parent / ref).exists():
                errs.append(f"{s} links missing {ref}")


def check_agents(errs):
    for a in AGENTS:
        p = AG / f"{a}.md"
        if not p.exists():
            errs.append(f"missing agent {a}")
            continue
        fm = frontmatter(read(p))
        if fm.get("name") != a or not fm.get("description") or not fm.get("tools"):
            errs.append(f"bad frontmatter in {p.relative_to(ROOT)}")
    if "Edit" in frontmatter(read(AG / "prd-story-verifier.md")).get("tools", ""):
        errs.append("prd-story-verifier must be read-only (no Edit)")


def check_stories(errs):
    ids = sorted(set(re.findall(r"^CQ-(\d+)", PRD, re.M)), key=int)
    text = read(SK / "counselqueue-domain" / "references" / "stories.md")
    missing = [i for i in ids if not re.search(rf"\bCQ-{i}\b", text)]
    if len(ids) != 61:
        errs.append(f"expected 61 stories in PRD, found {len(ids)}")
    if missing:
        errs.append("stories.md missing CQ-" + ", CQ-".join(missing))


def check_strings(errs):
    corpus = read(SK / "counselqueue-ui-spec" / "SKILL.md") + read(SK / "counselqueue-messaging" / "SKILL.md")
    for s in EXACT:
        if s not in corpus:
            errs.append(f"exact string missing: {s!r}")
    msg = read(SK / "counselqueue-messaging" / "SKILL.md")
    for t in TEMPLATES:
        if f"`{t}`" not in msg:
            errs.append(f"messaging template missing: {t}")


def check_focus(errs):
    for rel, phrase in FOCUS:
        if phrase not in read(SK / rel):
            errs.append(f"review-focus phrase {phrase!r} missing in {rel}")
    eng = read(SK / "counselqueue-queue-engine" / "SKILL.md")
    div = eng.split("## Prototype divergences", 1)
    if len(div) < 2 or "released" not in div[1]:
        errs.append("queue-engine divergences must cover released tokens")


def check_claude(errs):
    text = read(ROOT / "CLAUDE.md")
    if not text:
        errs.append("missing CLAUDE.md")
        return
    for name in SKILLS + AGENTS:
        if name not in text:
            errs.append(f"CLAUDE.md does not mention {name}")


CHECKS = {"skills": check_skills, "agents": check_agents, "stories": check_stories,
          "strings": check_strings, "focus": check_focus, "claude": check_claude}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=CHECKS.keys())
    args = ap.parse_args()
    errs = []
    for name, fn in CHECKS.items():
        if args.only in (None, name):
            fn(errs)
    for e in errs:
        print("FAIL:", e)
    if errs:
        sys.exit(1)
    print("kit OK")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it and confirm red**

Run: `python3 scripts/check_kit.py`
Expected: exit 1 with `FAIL: missing skill counselqueue-domain`, … `FAIL: missing CLAUDE.md`. There should be no Python traceback.

- [ ] **Step 4: Commit**

```bash
git add .gitignore scripts/check_kit.py docs/ prd_doc.md "CounselQueue — staff console.html" "Careers360 counselling — student check-in.html"
git commit -m "chore: init repo with PRD, prototypes and kit validator

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: counselqueue-domain skill + stories index + open questions

**Files:**
- Create: `.claude/skills/counselqueue-domain/SKILL.md`, `references/stories.md`, `references/open-questions.md`

**Interfaces:**
- Produces: canonical names used everywhere later. Models `Centre`, `CentreSettings`, `Counsellor`, `StaffUser`, `Student`, `TokenSequence`, `Note`, `AuditEvent`, `Message`. Status values `waiting|called|in_session|done|released|no_show|not_counselled`. Centre status `planned|live|closed`. Duty `on_desk|on_break|off_duty`. Consent `given|pending`. Source `self|desk`. Outcome `ready|interested|exploring|not_fit|null`.

- [ ] **Step 1: Confirm red**: `python3 scripts/check_kit.py --only stories` → `FAIL: stories.md missing CQ-1, …`

- [ ] **Step 2: Write `SKILL.md`**

````markdown
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
- `Counsellor`: name*, mobile*, centre FK, desk_label*, streams (≥1, subset of STREAMS), duty `on_desk|on_break|off_duty` (new = `off_duty`), expected_session_min (default 15). Unique (centre, desk_label).
- `StaffUser` (custom user, email login, case-insensitive): name, email, role `ops_lead|reception|counsellor`, centre FK (reception), counsellor 1:1 (counsellor), title.
- `Student` (one row per token): token, centre FK, counsellor FK, source `self|desk`, status, name*, school*, mobile* (10 digits), parent_mobile, email, stream, klass, course*, exams[], clarity, help[] (≥1), consent `given|pending`, consent_at, consent_by (null = student themself), checkin_at, queue_at (ordering key; reset on rejoin/miss), priority (pull-forward), called_at, started_at, ended_at, recalls, rating (1–5, set once), outcome, follow_up_on, colleges_discussed, home_city, target_exam, budget, accompanied_by, access_key (signed, for the student token URL).
- `TokenSequence`: (centre, last_number). The number never goes backwards.
- `Note`: student FK, text (non-empty), author_name, author counsellor FK, created_at. No delete.
- `AuditEvent`: student FK, verb (`checked_in|called|started|completed|missed|no_show|released|requeued|moved|pulled_forward|consent_given|edited|message_failed`), actor (StaffUser or null = student), `on_behalf_of` (Counsellor, set when an ops lead works a desk, CQ-5), at, data JSON.
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
Self check-in: consent is given at submit (`consent_at`, by student). Desk check-in: `pending`, and `consent_request` is sent. It clears by the student replying YES / tapping the link (CQ-24), or by the counsellor recording verbal consent (`consent_by` = counsellor, CQ-42). A session cannot start while pending.

## Roles & navigation (CQ-3)
| Role | Nav (in order) | Default screen |
|---|---|---|
| reception | Hall queue, Add a student, Hall board | Hall queue |
| counsellor | My queue, Live session, My students, My centres | My queue |
| ops_lead | Live centres, Centres & dates, Counsellors, All students, Insights, Hall queue, Hall board | Live centres |
An ops lead can additionally open a counsellor's desk (My queue / Live session / My students for that counsellor) via the live view, never as a permanent nav item (CQ-5). Any other screen → redirect to the role's default. A counsellor sees only students where `counsellor = self`. Export: ops_lead only (CQ-60).

## Audit & attribution
Every transition writes an `AuditEvent`. When an ops lead acts on a desk: `actor` = the lead, `on_behalf_of` = the counsellor, and notes use `author` = that counsellor (CQ-5). Signing out changes no student state (CQ-4).
````

- [ ] **Step 3: Write `references/stories.md`**

```markdown
# Story index (CQ-1 … CQ-61)
Source of truth: `prd_doc.md`. Epics: E1 Access & roles · E2 Centre & counsellor setup · E3 Student self check-in · E4 Student queue experience · E5 Front desk · E6 Counsellor desk · E7 Hall board · E8 Messaging · E9 Records & insights.

| ID | Epic | Story | Key rules | Depends |
|---|---|---|---|---|
| CQ-1 | E1 | Staff sign-in | email+password required; email case/space-insensitive; password toggle hidden by default; role→landing; no centre/desk/role pickers | — |
| CQ-2 | E1 | Failed sign-in | one generic error; keep email, clear password; 3rd consecutive failure shows IT helpdesk; reset on success; NO reset flow | CQ-1 |
| CQ-3 | E1 | Role-based nav | nav matrix; other screens redirect to default; never empty nav; counsellor sees own students | CQ-1 |
| CQ-4 | E1 | Sign out | on every screen; back button can't re-enter; no student state change | CQ-1 |
| CQ-5 | E1 | Lead opens a desk | control per counsellor card; switch centre; banner; full desk capability; notes as counsellor; not permanent nav; counsellors can't | CQ-3 |
| CQ-6 | E2 | Create centre | city, venue, date, times, expected; city+venue required; close>open; planned; duplicate city+date warns | — |
| CQ-7 | E2 | Edit centre | all fields; planned+live; no token/queue reset; board updates; assignments untouched | CQ-6 |
| CQ-8 | E2 | Go live / close | one action live; close confirms waiting count; waiting→not_counselled; no reopen | CQ-6 |
| CQ-9 | E2 | Add counsellor | name, mobile, centre, desk, ≥1 stream; starts off duty; desk label unique per centre | CQ-6 |
| CQ-10 | E2 | Stream coverage | show covered/uncovered; going live warns naming uncovered, allows continue | CQ-8, CQ-9 |
| CQ-11 | E2 | Roster conflicts | list centre/city/date/desk; same-date second assignment warns naming other city | CQ-9 |
| CQ-12 | E3 | QR landing | centre-only page; city/venue/date/times; no login; not-live and closed messages; one-hand mobile | CQ-8 |
| CQ-13 | E3 | Hall busyness | waiting count, counsellors on site, avg wait ("—" before first call); auto refresh | CQ-12 |
| CQ-14 | E3 | What to expect | 3 steps; what to bring (optional); front desk contact on landing+token | CQ-12 |
| CQ-15 | E3 | Details step | name ≥3, school req, mobile 10 digits, parent/email optional-valid; all errors together; keep values; 6 streams; stream decides counsellor | CQ-12 |
| CQ-16 | E3 | Goals step | course req ("not sure" ok); exams multi, None exclusive; clarity one; help ≥1; back keeps values; 4-step progress | CQ-15 |
| CQ-17 | E3 | Consent | one explicit unticked box; statement content; block message; consent_at recorded | CQ-16 |
| CQ-18 | E3 | OTP verify | code to WhatsApp; token only after code; change number keeps answers; wrong code message; resend after wait | CQ-15 |
| CQ-19 | E3 | Token issued | token content; assignment rule; STREAM-NN never repeats; on screen + WhatsApp | CQ-9, CQ-17, CQ-18 |
| CQ-20 | E3 | Duplicate block | open token same mobile same centre blocked, named, show its live status; closed tokens may re-check-in | CQ-19 |
| CQ-21 | E4 | Position & ETA | ahead at my desk; minutes + clock time; actual avg else expected; running session; live; approximate; never ≤0 | CQ-19 |
| CQ-22 | E4 | You're next | replaces position block; names desk; board shows next | CQ-21 |
| CQ-23 | E4 | Called | desk + counsellor; held for two calls; WhatsApp same moment; persists until start/complete/release | CQ-22, CQ-39 |
| CQ-24 | E4 | Desk-added consent | pending; WhatsApp ask; one action confirms; screen shows pending; verbal fallback; no start while pending | CQ-29, CQ-42 |
| CQ-25 | E4 | Release | waiting/called only; confirm; leaves queues/board; others move up; WhatsApp; new token on return | CQ-21 |
| CQ-26 | E4 | Recover token | same phone returns to token; WhatsApp link; desk can find by mobile | CQ-19, CQ-34 |
| CQ-27 | E4 | In session / done / no-show screens | state-specific screens; controls removed | CQ-23, CQ-40, CQ-46 |
| CQ-28 | E4 | Rating | 1–5 after done; also WhatsApp; optional; immutable; roll up per counsellor/centre | CQ-27 |
| CQ-29 | E5 | Desk check-in | same questions grouped; name+mobile+help required; same assignment; confirmation; source desk + consent pending; back to hall; form clears | CQ-9 |
| CQ-30 | E5 | Desk duplicate | CQ-20 rule; name token; open existing record; no issue | CQ-29 |
| CQ-31 | E5 | Hall list | waiting/called/in_session; token,name,counsellor,desk,stream,mobile,waited; by check-in; status; consent flag; empty state | CQ-19, CQ-29 |
| CQ-32 | E5 | Counsellor tabs | All first/default; per counsellor in desk order; live count; late badge; persists; off-duty with students shown; zero shown | CQ-31 |
| CQ-33 | E5 | Late flag | past wait promise; row+tab+header; clears on call; rejoin resets clock | CQ-32 |
| CQ-34 | E5 | Search today | name/mobile/token partial incl last 4; all statuses; above tabs, overrides; clear restores tab; count; empty suggests last 4 | CQ-32 |
| CQ-35 | E5 | Move student | waiting only; picker with queue lengths; excludes current; token same; keeps original order; WhatsApp; stream-mismatch warning | CQ-31 |
| CQ-36 | E5 | Requeue | from no_show/released/done; same token; clock restarts; recalls reset; audit who/when | CQ-34, CQ-46 |
| CQ-37 | E6 | Duty state | on desk/break/off duty; visible; only on-desk auto-assigned; no queue moves; board+desk view; break mid-session ok | CQ-9 |
| CQ-38 | E6 | My queue | header figures; order; row fields incl source; next highlighted; consent flag; empty; centre context | CQ-19, CQ-37 |
| CQ-39 | E6 | Call next | one control naming token; blocked with explanation if active; blocked if empty; called_at; notify; go to session | CQ-38 |
| CQ-40 | E6 | Call by token | case/space tolerant; unknown/completed/released messages; cross-desk reassigns + notifies; stream warning | CQ-39 |
| CQ-41 | E6 | Pull forward | not for top; becomes next; others keep order; ETAs recalc; audit | CQ-38 |
| CQ-42 | E6 | Consent gate | start disabled while pending with reason; verbal consent; resend request | CQ-24 |
| CQ-43 | E6 | Intake summary | course, school, parent, clarity, exams, help; "Not answered" for blanks; above edit form | CQ-16, CQ-29 |
| CQ-44 | E6 | Edit details | listed fields; save confirms; stream change keeps token/desk; 10-digit rule; required fields | CQ-43 |
| CQ-45 | E6 | Notes | any time; time + author; no empty; oldest first; no delete | CQ-43 |
| CQ-46 | E6 | Missed call | 1st miss → waiting, clock restarts, WhatsApp; 2nd → no_show, WhatsApp; desk free; recall count visible | CQ-39 |
| CQ-47 | E6 | Session timer | from start; elapsed + target; over-target state + my waiting count; never auto-ends; none before start | CQ-42 |
| CQ-48 | E6 | Outcome & follow-up | 4 outcomes or unset; follow-up not past; colleges text; roll up | CQ-44 |
| CQ-49 | E6 | Complete | ended_at; desk free; confirmation names next token or "queue clear"; WhatsApp; student screen; not before start | CQ-47 |
| CQ-50 | E6 | My students / centres | all mine newest first with wait/session/outcome/status; my centres live vs upcoming with route; own only | CQ-3 |
| CQ-51 | E7 | Hall board | panel per counsellor: desk, name, serving token, next, waiting; header; empty desk dash dimmed; big tokens; self refresh | CQ-39 |
| CQ-52 | E7 | Recently called | last six, newest first; none-yet message; scan instruction | CQ-51 |
| CQ-53 | E7 | Desk states on board | break "back shortly"; off duty closed; empty "queue clear"; from CQ-37 | CQ-37, CQ-51 |
| CQ-54 | E8 | Token confirmation WA | on issue; city/token/counsellor/desk + alert follows; desk variant asks consent | CQ-19, CQ-29 |
| CQ-55 | E8 | Turn WA | on call; desk + counsellor; consent ask if pending | CQ-39 |
| CQ-56 | E8 | Miss/move/release WA | first miss, second miss, desk change, release texts | CQ-46, CQ-35, CQ-25 |
| CQ-57 | E8 | Closing WA | thanks, counsellor, next steps, rating invite; on done | CQ-49, CQ-28 |
| CQ-58 | E8 | Delivery failure | failed turn alert flagged in hall + desk naming message; resend; never changes status | CQ-55 |
| CQ-59 | E9 | All students | all centres newest first; columns; filters text/counsellor/centre/stream/status combine; clear; count vs total; empty keeps filters | CQ-19 |
| CQ-60 | E9 | Export | listed columns; respects filters; filename has centre+date; ops_lead only | CQ-59 |
| CQ-61 | E9 | Insights | headline figures; stream demand; help & clarity counts; outcomes incl unset; follow-ups; rating avg with n; "—" for no data; averages state n | CQ-59 |
```

- [ ] **Step 4: Write `references/open-questions.md`**

```markdown
# Open questions (from PRD) and the defaults we build with
Each default is a setting or an isolated function so it can change after sign-off.

| Story | Question | Default we build |
|---|---|---|
| CQ-5 | Is attributing a lead's desk actions to the counsellor acceptable? | Notes are authored as the counsellor (per PRD); `AuditEvent.actor` = lead and `on_behalf_of` = counsellor, so the truth is never lost. |
| CQ-8 | Waiting students at close | Marked `not_counselled` (not `no_show`); close dialog names the count. |
| CQ-18 | OTP retry limit and resend interval | 4-digit code, expires 10 min, resend after 30 s, 5 wrong attempts invalidate the code (new code required). All in `settings.OTP_*`. |
| CQ-46 | Two calls before no-show | `CentreSettings.recall_limit = 2`. |
| CQ-58 | Delivery status from provider | Provider reports `queued/sent/delivered/failed`; stub marks `sent` immediately; a `failed` `turn_called` flags the student. Stub can be forced to fail via `MESSAGING_STUB_FAIL_TO` (list of mobiles) for tests. |
| CQ-60 | Export restriction vs data policy | ops_lead only; every export writes an audit row (who, filters, count). |
```

- [ ] **Step 5: Run** `python3 scripts/check_kit.py --only stories` → no FAIL lines, `kit OK`. Also run `--only focus` and confirm the `on_behalf_of` failure is gone (other focus failures remain).

- [ ] **Step 6: Commit** `git add .claude/skills/counselqueue-domain && git commit -m "feat(kit): counselqueue-domain skill with story index and open questions"` (with the Co-Authored-By line).

---

### Task 2: counselqueue-queue-engine skill

**Files:**
- Create: `.claude/skills/counselqueue-queue-engine/SKILL.md`, `references/prototype-engine.md`

**Interfaces:**
- Consumes: names from Task 1.
- Produces: service function names that backend plans must use, in `backend/apps/queue/services/`: `assign_counsellor(centre, stream) -> Counsellor|None`, `next_token(centre, stream) -> str`, `check_in(centre, data, source, actor=None) -> Student` (raises `DuplicateToken(existing)`, `NoCounsellorOnDuty`, `CentreNotLive`), `eta_for(student) -> Eta(position:int, minutes:int, at:datetime)`, `call_next(counsellor, actor)`, `call_token(counsellor, token_str, actor)`, `start_session`, `complete_session`, `mark_missed`, `release`, `requeue`, `move(student, counsellor, actor)`, `pull_forward(student, actor)`, `record_consent(student, by)`, `close_centre(centre, actor) -> int`.

- [ ] **Step 1: Confirm red**: `python3 scripts/check_kit.py --only focus` shows the `select_for_update` failure for queue-engine and the divergences failure.

- [ ] **Step 2: Write `SKILL.md`**

````markdown
---
name: counselqueue-queue-engine
description: The CounselQueue queue rules as testable specs — counsellor assignment, token numbering, duplicate detection, ETA/position, call next, call by token, pull forward, missed call/no-show, move, release, requeue, consent gate, late flag, centre close. Load when implementing or testing anything that changes a student's status or queue order.
---

# Queue engine

All functions live in `backend/apps/queue/services/` and are the **only** code allowed to change `Student.status`, `counsellor`, `queue_at` or `priority`. Each runs in `transaction.atomic()` and writes an `AuditEvent`. The prototype's JS version is annotated in [prototype-engine](references/prototype-engine.md).

## Queue order
A counsellor's queue = their students with status `waiting`, ordered by `(-priority, queue_at, id)`. "Next" = first. `queue_at` starts at check-in time and resets to now on a first miss or requeue. A move keeps it (CQ-35).

## Assignment (CQ-19, CQ-37)
`assign_counsellor(centre, stream)`:
1. Candidates = counsellors at the centre with `duty == on_desk` and `stream in streams`.
2. If none: candidates = `on_desk` counsellors (any stream), flagged `stream_mismatch=True` for the UI warning.
3. If still none → raise `NoCounsellorOnDuty`. The student sees the front-desk message, and reception can still add them after someone is on desk.
4. Pick the lowest `load` = waiting count + (1 if they have a called/in_session student), then the lowest `avg_session` (below), then desk label.
Lock the candidate counsellor rows with `select_for_update()` inside the check-in transaction.

## Token numbering (CQ-19)
`next_token(centre, stream)`: `TokenSequence.objects.select_for_update().get_or_create(centre=centre)`, then `last_number += 1`, save, and return `f"{stream}-{last_number:02d}"`. One sequence per centre, shared across streams. Numbers never repeat or go back, including after release or no-show. The number grows past 99 naturally (`PCM-100`).

## Duplicate detection (CQ-20, CQ-30)
Before issuing, look for a student at the same centre with the same normalised mobile and status in (waiting, called, in_session). If found, raise `DuplicateToken(existing)`. The message is "A token is already open for this number — {token}." Self check-in then shows that token's live status; the desk gets a link to the record. Other centres or dates are ignored.

## Average session & ETA (CQ-21)
- `avg_session(counsellor)` = mean(`ended_at - started_at`) over today's `done` students at this centre. If there are none, use `expected_session_min`.
- `eta_for(student)`: `pos` = index in queue (0-based); `remaining_current` = `max(2 min, avg - (now - current.started_at))` if in session, `avg` if called-not-started, else 0. `minutes = ceil((remaining_current + pos*avg)/60s)`, and `position = pos + 1` (never ≤ 0). `at = now + minutes`. Always shown as approximate ("about").

## Transitions (guards → effects)
- `call_next(c)`: guard "no called/in_session student at c" (else error naming that token); guard queue not empty → `call_token(c, queue[0].token)`.
- `call_token(c, raw)`: token = `raw.strip().upper()`; unknown at this centre → "No token {token} at this centre today."; `done` → "Token {token} was already counselled at {HH:MM}."; `released` → "Token {token} was released." + rejoin route; `no_show` → same with requeue route; `in_session`/`called` elsewhere → error. If on another desk: set `counsellor=c` (warn if stream not covered), send `desk_changed`. Then status `called`, `called_at=now`, send `turn_called`.
- `start_session(s)`: status must be `called`; consent must be `given` (else "Consent is pending — record verbal consent or resend the request."). Set `in_session` and `started_at`.
- `complete_session(s)`: must be `in_session`. Set `done` and `ended_at`, send `session_done`, and return the next token or None.
- `mark_missed(s)`: must be `called`. `recalls += 1`. If `recalls >= recall_limit`: set `no_show` and send `missed_final`. Else set `waiting`, `queue_at=now`, `called_at=None`, and send `missed_first`.
- `release(s)`: status in (waiting, called). Set `released`, send `released`.
- `requeue(s, actor)`: status in (no_show, released, done). Set `waiting`, `queue_at=now`, `recalls=0`, `called_at/started_at/ended_at=None`. Keep the token. Audit the actor.
- `move(s, c, actor)`: status `waiting`, `c != s.counsellor`, same centre. Set counsellor; `queue_at` unchanged; send `desk_changed`; warn on stream mismatch.
- `pull_forward(s, actor)`: status `waiting` and not already first. Set `priority = max(priority in queue) + 1`, audit `pulled_forward`.
- `record_consent(s, by)`: `consent=given`, `consent_at=now`, `consent_by=by` (None = student).
- `close_centre(centre)`: all `waiting` → `not_counselled`; centre `closed`; return the count. A closed centre cannot go live again.
- `set_duty(c, duty)`: never moves existing students (CQ-37).

## Late flag (CQ-33)
`is_late(s) = s.status == waiting and now - s.queue_at > wait_sla_min`. It clears on call because the status changes. A rejoin resets `queue_at`.

## Concurrency
Every mutating service locks the rows it reads to make a decision: `select_for_update()` on the student, the counsellor(s) and the `TokenSequence`. Tests must include two check-ins racing (use `TransactionTestCase` with threads, or assert that the lock calls are made).

## Prototype divergences (PRD wins)
- The prototype has no `released` status and lets `callToken` call a released token. Implement `released` and reject calling it with a rejoin route (CQ-25, CQ-40).
- The prototype `reassign` resets status only. We keep `queue_at` (original order, CQ-35) and forbid moving in-session students.
- The prototype `moveToTop` hacks `checkinAt`. Use `priority` so check-in time stays true (CQ-41, CQ-60 export).
- The prototype `requeue` doesn't record who did it. Audit it (CQ-36).
- The prototype's closing leaves waiting students. Mark them `not_counselled` (CQ-8).
- The prototype's third failed login mentions "Reset your password". There is no reset flow in this release (CQ-2).
- The prototype stores everything in localStorage. Ours lives server-side; only the student's `access_key` is kept on the device (CQ-26).
````

- [ ] **Step 3: Write `references/prototype-engine.md`**: paste the prototype functions `avgSession`, `etaFor`, `assignCounsellor`, `nextToken`, `checkIn`, `callToken`, `callNext`, `startSession`, `endSession`, `markNoShow`, `requeue`, `giveConsent`, `addNote`, `moveToTop`, `reassign` verbatim. Extract them with:

```bash
f="CounselQueue — staff console.html"
s=$(grep -n 'function avgSession' "$f" | cut -d: -f1); e=$(grep -n 'function qrSVG' "$f" | cut -d: -f1)
{ echo '# Prototype engine (reference only — PRD and SKILL.md win)'; echo; echo 'From `CounselQueue — staff console.html`. Divergences are listed in ../SKILL.md.'; echo; echo '```js'; sed -n "${s},$((e-1))p" "$f"; echo '```'; } > .claude/skills/counselqueue-queue-engine/references/prototype-engine.md
```

- [ ] **Step 4: Run** `python3 scripts/check_kit.py --only focus`. The queue-engine and divergence failures should be gone. `--only skills` should not list queue-engine.

- [ ] **Step 5: Commit** `feat(kit): counselqueue-queue-engine skill`.

---

### Task 3: counselqueue-messaging skill

**Files:** Create `.claude/skills/counselqueue-messaging/SKILL.md`

**Interfaces:**
- Produces: `backend/apps/messaging/providers/base.py::MessagingProvider.send(to: str, body: str) -> SendResult(provider_id: str, status: str)`, `stub.py::StubProvider`, `services.py::send_template(student, template: str, **vars) -> Message`, `services.py::send_otp(mobile) -> None`, `services.py::verify_otp(mobile, code) -> bool`, and the template keys below.

- [ ] **Step 1: Confirm red**: `python3 scripts/check_kit.py --only strings` lists the missing templates.

- [ ] **Step 2: Write `SKILL.md`**

````markdown
---
name: counselqueue-messaging
description: CounselQueue WhatsApp and OTP — provider interface, stub backend, every message template verbatim with trigger and variables, OTP rules, delivery-failure flagging and resend. Load when sending any student message or touching messaging code or tests.
---

# Messaging

All sends go through `apps.messaging.services.send_template(student, key, **vars)`. It renders the body, creates a `Message` row, calls the provider from `settings.MESSAGING_PROVIDER` (default `apps.messaging.providers.stub.StubProvider`) and stores the result. **Messaging never changes a student's status or queue position (CQ-58).** If `CentreSettings.whatsapp_enabled` is False, it records `status=failed` with reason `disabled`.

## Provider interface
```python
class MessagingProvider(Protocol):
    def send(self, to: str, body: str) -> SendResult: ...  # SendResult(provider_id, status in queued|sent|delivered|failed)
```
`StubProvider` logs to the console and returns `sent`, or `failed` if `to in settings.MESSAGING_STUB_FAIL_TO`. The delivery-status webhook (future real provider) goes to `POST /api/messaging/status/`, which updates `Message.status`.

## Templates (key → trigger → body)
Variables: `{city} {token} {counsellor} {desk} {link} {code} {minutes} {recalls} {close_time}`. `{link}` = the student's live token URL `/t/{access_key}` (CQ-26).

| Key | Trigger | Body |
|---|---|---|
| `otp_code` | student submits details (CQ-18) | Your Careers360 check-in code is {code}. It expires in {minutes} minutes. |
| `token_confirm_self` | self check-in token issued (CQ-54) | Careers360 {city}: you're in the queue. Token {token}, counsellor {counsellor} at {desk}. We'll message you when it's your turn. Track live: {link} |
| `token_confirm_desk` | desk check-in token issued (CQ-54, CQ-24) | Careers360 {city}: our front desk has checked you in. Token {token}, counsellor {counsellor} at {desk}. Reply YES to confirm it's you and allow us to use these details for counselling. We'll message you when it's your turn. Track live: {link} |
| `consent_request` | resend from session screen (CQ-42) | Careers360: please confirm it's you and allow us to use your details for counselling — reply YES or open {link} |
| `turn_called` | counsellor calls (CQ-23, CQ-55) | It's your turn. Please go to {desk} — {counsellor}. Your place is held for two calls. *(+ if consent pending:)* Reply YES to confirm you're here and consent to your details being used for counselling. |
| `missed_first` | first miss (CQ-46, CQ-56) | We called {token} and missed you. You're back in the queue — next call is the last one. |
| `missed_final` | no-show (CQ-46, CQ-56) | We called {token} {recalls} times. Visit the front desk to get back in the queue. |
| `desk_changed` | move / cross-desk call (CQ-35, CQ-40, CQ-56) | You've been moved to {counsellor}, {desk}. Token {token} stays the same. |
| `released` | student releases (CQ-25, CQ-56) | Token {token} is released. You can check in again before {close_time}. |
| `session_done` | complete (CQ-49, CQ-57) | Thanks for meeting {counsellor}. Your shortlist and next steps are on the way. Rate this session 1–5: {link} |

Inbound "YES" (future provider webhook) → `record_consent(student, by=None)`. In this release the `{link}` token page has a "Confirm it's me" button that does the same.

## OTP (CQ-18)
4-digit code, stored hashed with `expires_at` = now + `settings.OTP_TTL_MIN` (10). Resend is allowed after `settings.OTP_RESEND_SEC` (30). `settings.OTP_MAX_ATTEMPTS` (5) wrong tries invalidate the code. A wrong code shows "That code doesn't match — check your WhatsApp". In DEBUG/stub mode, the code `settings.OTP_STUB_CODE` (e.g. "1234") is accepted, matching the prototype shortcut. The verification result is a short-lived signed `verification_id` required by the check-in POST.

## Delivery failure (CQ-58)
A `Message` with status `failed` for key `turn_called` sets a flag the hall queue and desk show: "WhatsApp didn't reach them — {template label}. Call out their token." Resend = `POST /api/students/{id}/messages/{message_id}/resend/`. It is never a status change.
````

- [ ] **Step 3: Run** `python3 scripts/check_kit.py --only strings`. The template failures are gone; the ui-spec strings remain.

- [ ] **Step 4: Commit** `feat(kit): counselqueue-messaging skill`.

---

### Task 4: counselqueue-ui-spec skill + screens + design tokens

**Files:** Create `.claude/skills/counselqueue-ui-spec/SKILL.md`, `references/screens.md`, `references/design-tokens.md`

**Interfaces:**
- Produces: the validation function names mirrored front and back: `normalise_mobile(raw) -> str` (strip spaces, dashes, leading `+91`/`0`), `valid_mobile`, `valid_email`. Also the exact strings.

- [ ] **Step 1: Confirm red**: `python3 scripts/check_kit.py --only strings` lists the EXACT strings.

- [ ] **Step 2: Write `SKILL.md`**

````markdown
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
- Avg wait before any call: "—"
- What to bring: "Marksheets, entrance scorecard, photo ID, and a parent or guardian — all optional."

**Token screen (CQ-21…28)**
- Position: "{n} ahead of you at {desk}" · "About {m} min" · "Expected around {HH:MM}" (always "about"/approximate).
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
````

- [ ] **Step 3: Write `references/screens.md`**

```markdown
# Screens
## Student (mobile-first, one-hand, no horizontal scroll, works on slow 3G — CQ-12)
Route `/c/:centreSlug`, 4-step progress bar: **Details → Goals → Verify → Token**.
1. **Landing**: centre city, venue, date, hours; hall stats (waiting, counsellors on site, avg wait, polled 10s, CQ-13); "How it works" 3 steps (fill details → token on WhatsApp → sit anywhere until called, CQ-14); what to bring; front desk contact; "Check in" CTA. If the device has a live `access_key` → redirect to `/t/:key` (CQ-26). Not live / closed states replace the CTA.
2. **Details** (CQ-15): name, school, mobile, parent's mobile, email, stream (6 chips + hint), class.
3. **Goals** (CQ-16): course/career text, exams chips (None exclusive), clarity (4 options), help chips (≥1), consent checkbox (CQ-17, unticked), Back keeps values.
4. **Verify** (CQ-18): "Check your WhatsApp", 4-digit code input, resend after 30s countdown, "← Change number" returns to Details with everything kept.
5. **Token** `/t/:accessKey` (CQ-19, 21–28): token large; stream, counsellor, desk, venue, check-in time, expected time, name, mobile; state block per status (waiting position/ETA · next · called · in session · done+rating · no-show · released); release button (waiting/called); consent-pending banner for desk-added; front desk contact; polled 5s.

## Staff console `/console` (desktop and tablet; left rail nav from role; sign out in the top bar on every screen)
- **Sign-in** (CQ-1/2): email, password with show/hide (default hidden), error area, helpdesk notice after 3 failures.
- **Reception → Hall queue** (CQ-31–36): header hall-level late count; search box above tabs; tabs "All" + one per counsellor in desk order with live counts + late badge; table token/name/counsellor/desk/stream/mobile/waited/status/flags (consent pending, WA failed); row actions: Move, Requeue (no_show/released/done), open record.
- **Reception → Add a student** (CQ-29/30): two groups "who they are" / "what they want from the session"; duplicate warning with "Open {token}".
- **Counsellor → My queue** (CQ-37/38/39/40/41): duty toggle (On desk / On break / Off duty); header figures; centre context line; "Call {token}" primary; "Call a token" input; queue rows with pull-forward (not on top row).
- **Counsellor → Live session** (CQ-42–49): intake summary (above) → editable details form → notes list + add → outcome/follow-up/colleges → timer (elapsed / target, over-target state shows my waiting count) → Start (disabled while consent pending with reason + "Record verbal consent" + "Resend request") / Not turned up / Complete.
- **Counsellor → My students / My centres** (CQ-50).
- **Ops → Live centres** (CQ-5): per live centre, counsellor cards (duty, serving, queue, avg) each with "Open desk".
- **Ops → Centres & dates** (CQ-6/7/8/10): list + create/edit form; go live (with uncovered warning); close (with waiting count confirm); coverage chips.
- **Ops → Counsellors** (CQ-9/11): list with roster (centre, city, date, desk) + form; conflict warning.
- **Ops → All students** (CQ-59/60): filters (text, counsellor, centre, stream, status) + clear all + count; Export CSV `counselqueue_{city}_{date}.csv` (or `counselqueue_all_{today}.csv`).
- **Ops → Insights** (CQ-61): headline tiles; stream demand bars; help-with ranked; clarity counts; outcomes incl "Not set"; follow-ups; rating avg (n).
- **Hall board** `/board/:centreSlug` (CQ-51–53): full-screen, no chrome; header centre/venue/date/clock/total waiting; panel per counsellor (desk, name, serving token largest, next token, waiting count, duty state); recently called strip (last 6); standing line; polled 5s; readable across a hall.
```

- [ ] **Step 4: Write `references/design-tokens.md`**: extract both `:root` blocks verbatim:

```bash
f1="CounselQueue — staff console.html"; f2="Careers360 counselling — student check-in.html"
{ echo '# Design tokens (copied from prototypes)'; echo; echo 'Fonts: Instrument Sans (UI) + Instrument Serif (display) from Google Fonts.'; echo 'Staff console + board use the navy palette. The student flow uses the Careers360 warm palette (`--c360-*`) plus the brand gradient `linear-gradient(120deg,#C0392B 0%,#E85D3A 55%,#F39C12 100%)` for primary CTAs. Both support dark mode.'; echo; echo '## Staff console'; echo '```css'; sed -n '/<style>/,/<\/style>/p' "$f1" | sed -n '1,/^}/p'; sed -n '/prefers-color-scheme: dark/,/^}/p' "$f1" | head -20; echo '```'; echo; echo '## Student check-in'; echo '```css'; grep -E -- '--c360-[a-z-]+:' "$f2" | sort -u; echo '```'; } > .claude/skills/counselqueue-ui-spec/references/design-tokens.md
```
Then open the file and trim any non-token CSS so only `:root` variables, the dark-mode overrides and the font import remain.

- [ ] **Step 5: Run** `python3 scripts/check_kit.py --only strings` → `kit OK`. Run `--only focus` → `normalise_mobile` is satisfied.

- [ ] **Step 6: Commit** `feat(kit): counselqueue-ui-spec skill with screens and design tokens`.

---

### Task 5: django-backend-conventions skill

**Files:** Create `.claude/skills/django-backend-conventions/SKILL.md`

- [ ] **Step 1: Confirm red**: `--only focus` shows `select_for_update` and `localdate` missing for backend-conventions.

- [ ] **Step 2: Write `SKILL.md`**

````markdown
---
name: django-backend-conventions
description: How the CounselQueue backend is built — Django 4.2 LTS + DRF + MySQL project layout, services layer, locking, auth and role permissions, public student API, polling endpoints, CSV export, settings, and pytest-django testing per acceptance criterion. Load before writing or reviewing any code under backend/.
---

# Backend conventions (`backend/`)

## Stack (pin in `requirements.txt`)
`Django>=4.2,<4.3`, `djangorestframework`, `djangorestframework-simplejwt`, `mysqlclient`, `django-environ`, `django-cors-headers`; dev: `pytest`, `pytest-django`, `factory-boy`, `freezegun`, `ruff`. Python 3.11+.

## Layout
```
backend/
  manage.py  requirements.txt  pytest.ini  .env.example
  config/settings/{base,local,test}.py  config/urls.py
  apps/
    accounts/    StaffUser (AbstractBaseUser, USERNAME_FIELD=email), login lockout counter, permissions.py (IsOpsLead, IsReception, IsCounsellor, RoleIn(...))
    centres/     Centre, CentreSettings, services (create/edit/go_live/close, coverage, duplicate warn)
    counsellors/ Counsellor, services (create, set_duty, roster conflicts)
    queue/       Student, TokenSequence, Note, AuditEvent; services/{assignment,tokens,checkin,eta,transitions,consent}.py; selectors.py (read queries)
    messaging/   Message, OtpCode, providers/{base,stub}.py, services.py, templates.py
    insights/    selectors.py (aggregations), export.py (CSV)
    public/      student-facing views (no auth)
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
| `GET/POST counsellors/`, `PATCH counsellors/{id}/`, `POST counsellors/{id}/duty/` | ops / self | 9, 11, 37 |
| `GET centres/{id}/hall/?q=&counsellor=` | reception, ops | 31–34, 58 |
| `POST centres/{id}/checkins/` | reception | 29, 30 |
| `GET desk/queue/` · `POST desk/call-next/` · `POST desk/call-token/` | counsellor (ops as_counsellor) | 38–41 |
| `POST students/{id}/{start,complete,missed,move,requeue,pull-forward,consent}/` | per role | 35, 36, 41, 42, 46, 49 |
| `PATCH students/{id}/` · `POST students/{id}/notes/` · `POST students/{id}/messages/{mid}/resend/` | counsellor/ops | 44, 45, 48, 58 |
| `GET students/?filters` · `GET students/export.csv` | ops (counsellor: own) | 50, 59, 60 |
| `GET insights/?centre=` | ops | 61 |
| `GET live/` | ops | 5 |
Polling endpoints (`public/tokens`, `public/board`, `hall`, `desk/queue`, `public/centres`) must be single-query-per-panel (`select_related`/`prefetch_related`), with no N+1, and return in under 100 ms on seed data.

## Testing
- pytest-django + factory-boy; `freezegun` for waits and timers. One test per AC, named `test_cq<id>_<behaviour>`. Services are tested directly, views with `APIClient` for permissions and response shape.
- Required cross-cutting tests: role matrix (each role × each endpoint → 200/403), concurrency (two check-ins → distinct tokens), messaging never changes status, stub failure path.
- Commands: `cd backend && pytest -q`, `ruff check .`, `python manage.py makemigrations --check`.
- Seed: `python manage.py seed_demo` recreates the prototype's Gwalior/Indore/Jaipur data and users (passwords only from env in non-local environments).
````

- [ ] **Step 3: Run** `--only focus` → `kit OK` for focus.
- [ ] **Step 4: Commit** `feat(kit): django-backend-conventions skill`.

---

### Task 6: react-frontend-conventions skill

**Files:** Create `.claude/skills/react-frontend-conventions/SKILL.md`

- [ ] **Step 1: Confirm red**: `--only skills` lists `missing skill react-frontend-conventions`.
- [ ] **Step 2: Write `SKILL.md`**

````markdown
---
name: react-frontend-conventions
description: How the CounselQueue frontend is built — React 19 + Vite + TypeScript, routes for student flow, token page, staff console and hall board, TanStack Query polling, React Hook Form + Zod mirroring backend validation, role-gated navigation, design tokens, and Vitest + Testing Library tests per acceptance criterion. Load before writing or reviewing any code under frontend/.
---

# Frontend conventions (`frontend/`)

## Stack
React 19, Vite, TypeScript (strict), React Router 7 (data routers), TanStack Query 5, React Hook Form + Zod, plain CSS modules + `src/styles/tokens.css` (from counselqueue-ui-spec design tokens). Tests: Vitest, @testing-library/react, MSW for API mocks. Node 20+.

## Layout
```
frontend/src/
  app/        router.tsx, providers.tsx, RequireRole.tsx
  api/        client.ts (fetch wrapper, JWT, error → {code,message}), queryKeys.ts, one hooks file per resource (useHall.ts, useDeskQueue.ts, useToken.ts …)
  features/
    student/  Landing, DetailsStep, GoalsStep, VerifyStep, TokenPage, checkinSchema.ts
    auth/     SignIn, useAuth
    hall/     HallQueue, AddStudent, SearchBox, CounsellorTabs
    desk/     MyQueue, LiveSession, IntakeSummary, SessionTimer, MyStudents, MyCentres
    ops/      LiveCentres, Centres, Counsellors, AllStudents, Insights, DeskBanner
    board/    HallBoard
  lib/        mobile.ts (normaliseMobile), format.ts (fmtTime, fmtMins, "—"), nav.ts (NAV per role)
  styles/     tokens.css, global.css
```

## Rules
- Server state lives only in TanStack Query. Live views poll with `refetchInterval`: token, board, desk queue and hall at 5000 ms; landing hall stats at 10000 ms. Set `refetchIntervalInBackground: false`.
- The only thing stored on the device is the student's `access_key` in localStorage (CQ-26). Wrap it in try/catch, because the page must work without it. Staff tokens are held in memory, with refresh in an httpOnly cookie or memory.
- Navigation comes from `lib/nav.ts` (the role matrix in counselqueue-domain). `RequireRole` redirects unknown/forbidden routes to the role's default view (CQ-3). Sign out: clear the query cache and tokens, then `navigate('/console/login', {replace: true})` (CQ-4).
- Forms: Zod schemas mirror counselqueue-ui-spec rules and messages exactly. Show all errors at once, and keep values. The multi-step student form keeps state in one `useForm` across steps.
- Copy comes verbatim from counselqueue-ui-spec. Server error `message` is shown as returned.
- Student pages: mobile-first, 16px gutters, no horizontal scroll at 320px, tap targets ≥44px, small bundle (lazy-load the console and board routes).
- Hall board: full-screen route with no auth chrome; token numbers use `clamp()` to stay readable across a hall.
- Accessibility: labels on every input, `aria-live="polite"` for status changes on the token page and queue.

## Routes
`/c/:centreSlug` (student) · `/t/:accessKey` (token) · `/board/:centreSlug` · `/console/login` · `/console/{hall,add,queue,session,mine,roster,live,centres,counsellors,students,insights}` · `/console/desk/:counsellorId/{queue,session,mine}` (ops only, shows DeskBanner).

## Testing
One test per UI acceptance criterion: `it("CQ-15 reports all failing fields together", …)`. MSW handlers per endpoint. Use fake timers for polling and the session timer. Commands: `cd frontend && npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.
````

- [ ] **Step 3: Run** `--only skills` → `kit OK`.
- [ ] **Step 4: Commit** `feat(kit): react-frontend-conventions skill`.

---

### Task 7: Agents

**Files:** Create `.claude/agents/django-backend-dev.md`, `react-frontend-dev.md`, `prd-story-verifier.md`

- [ ] **Step 1: Confirm red**: `--only agents` shows 3 missing.
- [ ] **Step 2: Write `django-backend-dev.md`**

```markdown
---
name: django-backend-dev
description: Builds CounselQueue backend features in backend/ (Django 4.2 + DRF + MySQL) story by story from prd_doc.md, test-first. Use when a CQ-* story or epic needs models, services, APIs or backend tests.
tools: Read, Write, Edit, Bash, Grep, Glob
skills: counselqueue-domain, counselqueue-queue-engine, counselqueue-messaging, counselqueue-ui-spec, django-backend-conventions
---

You implement CounselQueue backend work. Before any code, load and follow these skills: counselqueue-domain, counselqueue-queue-engine, counselqueue-messaging, counselqueue-ui-spec, django-backend-conventions. The PRD (`prd_doc.md`) wins over the prototypes.

For each story you are given:
1. Read the story's acceptance criteria in `prd_doc.md` and its row in `.claude/skills/counselqueue-domain/references/stories.md` (check dependencies exist).
2. Write failing tests first, one per AC, named `test_cq<id>_<behaviour>`. Run `cd backend && pytest -q <file>` and see them fail.
3. Implement the minimum in services/selectors, then thin views/serializers. Use exact strings from counselqueue-ui-spec.
4. Run `pytest -q`, `ruff check .`, `python manage.py makemigrations --check`. All must pass.
5. Commit per story: `feat(backend): CQ-<id> <summary>`.
Report: stories done, tests added, commands run with results, and any AC you could not satisfy (never claim done without passing output).
```

- [ ] **Step 3: Write `react-frontend-dev.md`**

```markdown
---
name: react-frontend-dev
description: Builds CounselQueue frontend screens in frontend/ (React 19 + Vite + TypeScript + TanStack Query) story by story from prd_doc.md, test-first, using the HTML prototypes as the visual reference. Use when a CQ-* story needs UI, forms, polling views or frontend tests.
tools: Read, Write, Edit, Bash, Grep, Glob
skills: counselqueue-domain, counselqueue-ui-spec, react-frontend-conventions
---

You implement CounselQueue frontend work. Before any code, load and follow: counselqueue-domain, counselqueue-ui-spec, react-frontend-conventions. The visual reference is the prototype HTML in the project root (`CounselQueue — staff console.html`, `Careers360 counselling — student check-in.html`). Match its layout and tokens, but take behaviour from the PRD.

For each story:
1. Read its ACs in `prd_doc.md` and the screen in `.claude/skills/counselqueue-ui-spec/references/screens.md`. Confirm the backend endpoint exists (django-backend-conventions API map). If it is missing, mock it with MSW and say so.
2. Write failing tests (`it("CQ-<id> …")`), then run `cd frontend && npm test -- <file>`.
3. Implement with verbatim copy and Zod rules from counselqueue-ui-spec.
4. Run `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`. All must pass.
5. Commit per story: `feat(frontend): CQ-<id> <summary>`.
Report: stories done, tests, command results, and gaps.
```

- [ ] **Step 4: Write `prd-story-verifier.md`**

```markdown
---
name: prd-story-verifier
description: Read-only checker that verifies CQ-* stories against the code — for each acceptance criterion in prd_doc.md reports PASS / FAIL / MISSING with file:line evidence and the test that proves it. Use after a story is implemented or before a release.
tools: Read, Grep, Glob, Bash
skills: counselqueue-domain, counselqueue-queue-engine, counselqueue-messaging, counselqueue-ui-spec
---

You verify, you never edit files. Load counselqueue-domain, counselqueue-queue-engine, counselqueue-messaging and counselqueue-ui-spec.

Given one or more CQ ids:
1. Extract every acceptance criterion for each id from `prd_doc.md`.
2. For each AC, find the implementing code and the test (`test_cq<id>_*` in backend/tests, `CQ-<id>` in frontend tests). You may run tests read-only: `cd backend && pytest -q -k cq<id>`, `cd frontend && npx vitest run -t "CQ-<id>"`.
3. Check exact strings against counselqueue-ui-spec, and rules against the queue-engine skill.
Output a table: `AC | PASS/FAIL/MISSING | evidence (file:line) | test`. Then list the failures, most severe first. Do not suggest that something passes without evidence.
```

- [ ] **Step 5: Run** `--only agents` → `kit OK`.
- [ ] **Step 6: Commit** `feat(kit): backend, frontend and verifier agents`.

---

### Task 8: CLAUDE.md + build roadmap

**Files:** Create `CLAUDE.md`

- [ ] **Step 1: Confirm red**: `--only claude` → `missing CLAUDE.md`.
- [ ] **Step 2: Write `CLAUDE.md`**

```markdown
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
```

- [ ] **Step 3: Run the full suite**: `python3 scripts/check_kit.py` → `kit OK`, exit 0.
- [ ] **Step 4: Commit** `docs: CLAUDE.md project map and build roadmap`.

---

### Task 9: End-to-end kit verification

- [ ] **Step 1:** `python3 scripts/check_kit.py; echo exit=$?` → `kit OK` / `exit=0`.
- [ ] **Step 2: Negative test of the validator**: temporarily rename `stories.md` to `stories.bak`, run the validator, and expect `FAIL: stories.md missing CQ-1…`. Rename it back and expect `kit OK`.
- [ ] **Step 3:** Start a new Claude Code session in `counselling/`. Confirm the 6 skills appear in the skill list and the 3 agents appear in the agent types.
- [ ] **Step 4: Smoke-test the verifier**: dispatch `prd-story-verifier` with "Verify CQ-19". Expected: every AC is MISSING (no backend yet), and the output cites the assignment rule and token format from the skills.
- [ ] **Step 5:** `git log --oneline` shows the task commits; `git status` is clean.

---

## Self-review (done)
- **Spec coverage:** all 61 stories are indexed (Task 1, enforced by the validator). Each rule family has a skill: auth/roles → domain + backend; setup → domain + ui-spec; check-in/queue → queue-engine; messaging → messaging; board/insights → ui-spec screens + backend API map. The app build is deliberately deferred to the roadmap plans (this plan = the kit).
- **Placeholders:** none. The prototype-extracted files are produced by exact commands.
- **Name consistency:** status/role/template/service names are defined in Tasks 1–3 and reused verbatim in 5–7.
- **Review Focus:** all 5 items are pinned by validator `FOCUS` checks in their owning tasks.
