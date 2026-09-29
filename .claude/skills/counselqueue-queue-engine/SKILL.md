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
