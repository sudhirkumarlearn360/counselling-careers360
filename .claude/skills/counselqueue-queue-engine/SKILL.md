---
name: counselqueue-queue-engine
description: The CounselQueue queue rules as testable specs — counsellor assignment, token numbering, duplicate detection, ETA/position, call next, call by token, pull forward, missed call/no-show, move, release, requeue, consent gate, late flag, centre close. Load when implementing or testing anything that changes a student's status or queue order.
---

# Queue engine

All functions live in `backend/apps/queue/services/` and are the **only** code allowed to change `Student.status`, `counsellor`, `queue_at` or `priority`. Each runs in `transaction.atomic()` and writes an `AuditEvent`. The prototype's JS version is annotated in [prototype-engine](references/prototype-engine.md).

## Queue order
A counsellor's queue = their students at the centre with status `waiting`, ordered by `(-priority, queue_at, id)`. "Next" = first. `queue_at` starts at check-in time and resets to now on a first miss or requeue. A move keeps it (CQ-35). Pull-forward `priority` is per-desk and temporary: `priority = 0` is set on a first miss, requeue and move, so the student really rejoins at the back, or at their original time on the new desk.

## Assignment (CQ-19, CQ-37)
`assign_counsellor(centre, stream)`:
1. Candidates = the centre's `Posting`s with `duty == on_desk` whose counsellor has `stream in streams`.
2. If none: raise `NoCounsellorForStream` (strict stream routing, CQ-19). Self check-in shows "No counsellor for your stream is on desk yet — please see the front desk." If nobody at all is on desk, raise `NoCounsellorOnDuty` ("No counsellor is on desk yet — please see the front desk."). At the desk (CQ-29), reception sees the same error and may pick a counsellor manually with the CQ-35 stream warning. There is **no silent fallback** to an uncovered counsellor.
3. Pick the lowest `load` = waiting count + (1 if they have a called/in_session student), then the lowest `avg_session` (below), then desk label.
Lock candidate posting rows with `select_for_update()` in `order_by("id")` inside the check-in transaction.

## Token numbering (CQ-19)
`next_token(centre, stream)`: the `TokenSequence` row already exists (created with the Centre). Use `TokenSequence.objects.select_for_update().get(centre=centre)`, then `last_number += 1`, save, and return `f"{stream}-{last_number:02d}"`. One sequence per centre, shared across streams. Numbers never repeat or go back, including after release or no-show. The number grows past 99 naturally (`PCM-100`).

## Duplicate detection (CQ-20, CQ-30)
Before issuing, look for a student at the same centre with the same normalised mobile and status in (waiting, called, in_session). If found, raise `DuplicateToken(existing)`. The message is "A token is already open for this number — {token}." Self check-in then shows that token's live status; the desk gets a link to the record. Other centres or dates are ignored.

## Average session & ETA (CQ-21)
- `avg_session(counsellor)` = mean(`ended_at - started_at`) over today's `done` students at this centre. If there are none, use `expected_session_min`.
- `avg_session` reads `SessionRecord` rows (not `Student` fields), so requeued students don't lose history.
- `eta_for(student) -> Eta(ahead, is_next, minutes, at)`: `pos` = index in the waiting queue (0-based). `ahead = pos` counts waiting students in front only; the student currently called or in session is **not** counted as ahead. `is_next = (pos == 0)`, and the UI shows the "You're next" state instead of the position block (CQ-22). Show "{n} ahead" only when `ahead ≥ 1`; `ahead` is never negative. `remaining_current` = `max(2 min, avg - (now - current.started_at))` if in session, `avg` if called-not-started, else 0. `minutes = ceil((remaining_current + pos*avg)/60s)`, and `at = now + minutes`. Always shown as approximate ("about").

## Transitions (guards → effects)
- `call_next(c)`: guard queue not empty ("Your queue is clear — new check-ins land here as students scan in.") → `call_token(c, queue[0].token)`.
- `call_token(c, raw)`: the busy-desk guard lives in `call_token`, so `call_next` inherits it: if c already has a called/in_session student → "Finish {token} before calling the next student." The token lookup is **centre-wide** (not scoped to c's own students). token = `raw.strip().upper()`. Unknown at this centre → "No token {token} at this centre today."; `done` → "Token {token} was already counselled at {HH:MM}."; `released` → "Token {token} was released — requeue it to call."; `no_show` → "Token {token} was marked no-show — requeue it to call."; `not_counselled` → "Token {token} wasn't counselled before closing."; `called`/`in_session` at another desk → "Token {token} is already with {counsellor} at {desk}." If waiting on another desk: set `counsellor=c` (warn if stream not covered), send `desk_changed`. Then status `called`, `called_at=now`, send `turn_called`.
- `start_session(s)`: status must be `called`; consent must be `given` (else "Consent is pending — record verbal consent or resend the request."). Set `in_session` and `started_at`.
- `complete_session(s)`: must be `in_session`. Set `done` and `ended_at`, write a `SessionRecord`, send `session_done`, and return the next token or None.
- `mark_missed(s)`: must be `called`. `recalls += 1`. If `recalls >= recall_limit`: set `no_show` and send `missed_final`. Else set `waiting`, `queue_at=now`, `priority = 0`, `called_at=None`, and send `missed_first`.
- `release(s)`: status in (waiting, called). Set `released`, send `released`.
- `requeue(s, actor)`: status in (no_show, released, done). Set `waiting`, `queue_at=now`, `priority = 0`, `recalls=0`, `called_at/started_at/ended_at=None`. Earlier sessions survive in `SessionRecord`. Keep the token. Audit the actor.
- `move(s, c, actor)`: status `waiting`, `c != s.counsellor`, same centre. Set counsellor; `queue_at` unchanged; `priority = 0`; send `desk_changed`; warn on stream mismatch.
- `pull_forward(s, actor)`: status `waiting` and not already first. Set `priority = max(priority in queue) + 1`, audit `pulled_forward`.
- `record_consent(s, by)`: `consent=given`, `consent_at=now`, `consent_by=by` (None = student).
- `close_centre(centre)`: all `waiting` → `not_counselled`; centre `closed`; return the count. Students already `called` or `in_session` remain actionable after close (start, complete, miss), so a session in progress is never cut off. A miss after close ends as `not_counselled`, not back in a queue. A closed centre cannot go live again. `centres` services delegate here.
- `set_duty(posting, duty)`: never moves existing students (CQ-37).

## Late flag (CQ-33)
`is_late(s) = s.status == waiting and now - s.queue_at > wait_sla_min`. It clears on call because the status changes. A rejoin resets `queue_at`.

## Concurrency
Every mutating service locks the rows it reads to make a decision. Lock order is fixed to avoid deadlocks: **1. `TokenSequence` for the centre → 2. postings `order_by("id")` → 3. student**. Check-in: the first statement in the transaction is `TokenSequence.objects.select_for_update().get(centre=…)`, which serialises check-ins per centre. Then the duplicate check (safe now because it runs under that lock), then assignment, then numbering. Required tests (`TransactionTestCase` with two threads, real MySQL): a different-mobile race gives distinct tokens, and a same-mobile race gives exactly one token plus one `DuplicateToken`. Asserting that lock calls were made is not enough.

## Metrics (single definitions; every screen and export uses these)
- **Wait** = `called_at − queue_at` over students who have been called (the current wait for waiting students = `now − queue_at`). The average wait today = the mean over called students; "—" if none (CQ-13).
- **Session length** = `ended_at − started_at` from `SessionRecord`.
- **Counselled today** (CQ-38) = count of `SessionRecord` for that counsellor and centre today.
- **Counsellors on site** (CQ-13) = postings with duty `on_desk` or `on_break`.
- **No-show rate** (CQ-61) = no_show / (done + no_show); "—" when the denominator is 0.
- **Counselled or queued** (CQ-61) = students with status in (waiting, called, in_session, done).
- Every average states its n: "{value} (from {n})".

## Prototype divergences (PRD wins)
- The prototype has no `released` status and lets `callToken` call a released token. Implement `released` and reject calling it with a rejoin route (CQ-25, CQ-40).
- The prototype `assignCounsellor` silently falls back to a counsellor outside the stream. We raise `NoCounsellorForStream` (CQ-19).
- The prototype `reassign` resets status only. We keep `queue_at` (original order, CQ-35) and forbid moving in-session students.
- The prototype `moveToTop` hacks `checkinAt`. Use `priority` so check-in time stays true (CQ-41, CQ-60 export).
- The prototype `requeue` doesn't record who did it. Audit it (CQ-36).
- The prototype's closing leaves waiting students. Mark them `not_counselled` (CQ-8).
- The prototype's third failed login mentions "Reset your password". There is no reset flow in this release (CQ-2).
- The prototype stores everything in localStorage. Ours lives server-side; only the student's `access_key` is kept on the device (CQ-26).
