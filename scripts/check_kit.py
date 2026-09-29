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
# (file relative to SK, phrase) pairs pinning fixes from the final branch review.
REVIEW = [
    ("counselqueue-domain/SKILL.md", "`Posting`"),                      # 1 roster
    ("counselqueue-queue-engine/SKILL.md", "`Posting`"),
    ("django-backend-conventions/SKILL.md", "postings/"),
    ("counselqueue-queue-engine/SKILL.md", "`priority = 0`"),           # 2
    ("counselqueue-queue-engine/SKILL.md", "NoCounsellorForStream"),    # 3
    ("counselqueue-ui-spec/SKILL.md", "No counsellor for your stream is on desk yet"),
    ("counselqueue-queue-engine/SKILL.md", "is_next"),                  # 4
    ("counselqueue-ui-spec/SKILL.md", "is_next"),
    ("counselqueue-queue-engine/SKILL.md", "busy-desk guard lives in `call_token`"),  # 5
    ("counselqueue-queue-engine/SKILL.md", "order_by(\"id\")"),         # 6
    ("counselqueue-queue-engine/SKILL.md", "same-mobile race"),
    ("counselqueue-domain/SKILL.md", "`SessionRecord`"),               # 7
    ("counselqueue-queue-engine/SKILL.md", "`SessionRecord`"),
    ("counselqueue-messaging/SKILL.md", "single-use"),                  # 8
    ("counselqueue-messaging/SKILL.md", "bound to the normalised mobile"),
    ("django-backend-conventions/SKILL.md", "GET students/{id}/"),      # 9
    ("counselqueue-queue-engine/SKILL.md", "## Metrics"),               # 10
    ("counselqueue-queue-engine/SKILL.md", "remain actionable"),        # 13
    ("counselqueue-queue-engine/SKILL.md", "Token {token} was released — requeue it to call."),  # 15
    ("counselqueue-ui-spec/SKILL.md", "Token {token} was released — requeue it to call."),
    ("counselqueue-domain/SKILL.md", "inside `token_confirm_desk`"),    # 16
    ("django-backend-conventions/SKILL.md", "delegates to `queue.services.close_centre`"),  # 19
]
AGENT_MODELS = {"haiku", "sonnet", "opus"}
VERIFIER_TOOLS = {"Read", "Grep", "Glob", "Bash"}
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
        if fm.get("model") not in AGENT_MODELS:
            errs.append(f"{a} needs model: one of {sorted(AGENT_MODELS)}")
    tools = {x.strip() for x in frontmatter(read(AG / "prd-story-verifier.md")).get("tools", "").split(",") if x.strip()}
    if tools - VERIFIER_TOOLS:
        errs.append(f"prd-story-verifier must be read-only; disallowed tools: {sorted(tools - VERIFIER_TOOLS)}")
    if "Bash" in tools and "Only these Bash commands" not in read(AG / "prd-story-verifier.md"):
        errs.append("prd-story-verifier has Bash but no Bash allowlist in its prompt")


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


def check_review(errs):
    for rel, phrase in REVIEW:
        if phrase not in read(SK / rel):
            errs.append(f"review fix {phrase!r} missing in {rel}")


def check_claude(errs):
    text = read(ROOT / "CLAUDE.md")
    if not text:
        errs.append("missing CLAUDE.md")
        return
    for name in SKILLS + AGENTS:
        if name not in text:
            errs.append(f"CLAUDE.md does not mention {name}")
    if "## Model routing" not in text:
        errs.append("CLAUDE.md missing '## Model routing' section")
    settings = read(ROOT / ".claude" / "settings.json")
    if '"opusplan"' not in settings or "CLAUDE_CODE_SUBAGENT_MODEL" not in settings:
        errs.append(".claude/settings.json must set model opusplan and CLAUDE_CODE_SUBAGENT_MODEL")


CHECKS = {"skills": check_skills, "agents": check_agents, "stories": check_stories,
          "strings": check_strings, "focus": check_focus, "review": check_review, "claude": check_claude}


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
