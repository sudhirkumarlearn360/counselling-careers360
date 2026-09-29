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
