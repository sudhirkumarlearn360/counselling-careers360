CounselQueue
Created By: Sumit Mishra

Prototype: https://claude.ai/artifact/N6Hsv1AtrDUQ3PUgX6NrEN?sk=k4cozV7VF7_6PJaVZd-hVw

Student Flow: https://claude.ai/artifact/7aptJmw5xNC8BY2cndSqNi?sk=Ii24nI9VcJHjy2nkwjGN8Q

Jira Stories:
CQ-1 — As a counselling staff member, I want to sign in with my own work account so that the system knows which desk and centre I'm working from without me picking it each morning.

Scenario: As a counsellor, receptionist or operations lead arriving at a venue, I open the console and sign in once. The system puts me straight into my own centre and desk. This removes the daily setup step and makes every action attributable to a named person.

Acceptance Criteria:

Sign-in

Email and password are both required; submitting with either blank shows "Enter your work email and password".

Email is matched case-insensitively and with surrounding spaces ignored.

A password visibility toggle is available and defaults to hidden.

Landing behaviour

A receptionist lands on the hall queue of the centre they're rostered to.

A counsellor lands on their own queue, with their desk and centre already selected.

An operations lead lands on the live centres overview.

Scope

No centre, desk or role selector is shown anywhere after sign-in; all three come from the account.

Business Impact:

Operational efficiency: removes per-session setup and the misconfiguration it causes (a counsellor working the wrong desk's queue).

Risk and compliance: every student record opened is attributable to a named staff member.

Additional Notes: Prerequisite for CQ-2 to CQ-5. Account creation is out of scope for this story.

CQ-2 — As a staff member who mistypes my password, I want to be told clearly what went wrong and what to do next so that I'm not stuck at the door with a hall filling up.

Scenario: As a staff member signing in at the start of a busy day, I get it wrong once or twice. I need an error I can act on, and after repeated failures, a route to help.

Acceptance Criteria:

Error messaging

A wrong email or wrong password produces one identical message: "That email and password don't match an account."

The message does not reveal whether the email exists.

The email I typed stays in the field; the password field is cleared.

Repeated failures

On the third consecutive failure, an additional notice appears with the IT helpdesk number and email.

The failure count resets to zero on a successful sign-in.

Non-existent cases

No self-service password reset exists in this release; the helpdesk is the only route. Do not build a reset flow.

Business Impact:

Operational efficiency: a stuck counsellor at 10am is a closed desk for the first hour; routing to the helpdesk on-screen shortens that.

Additional Notes: Depends on CQ-1.

CQ-3 — As an organisation handling student data, I want each person to see only the screens their role needs so that a counsellor can't browse the full student database and reception can't change centre setup.

Scenario: As any signed-in staff member, the navigation I see is built from my role alone. Anything outside it is not shown and not reachable.

Acceptance Criteria:

Front desk

Sees hall queue, add a student, hall board.

Does not see centre setup, counsellor management, the all-students database or insights.

Counsellor

Sees my queue, live session, my students, my centres.

"My students" is limited to students assigned to me.

Operations lead

Sees live centres, centres and dates, counsellors, all students, insights, hall queue, hall board.

Enforcement

Attempting to reach a screen outside my role returns me to my own default screen.

No role produces an empty navigation.

Business Impact:

Risk and compliance: limits exposure of minors' contact details to the staff who need them for the session in front of them.

Operational efficiency: each role's navigation stays short enough to use one-handed at a desk.

Additional Notes: Depends on CQ-1.

CQ-4 — As a staff member finishing my shift, I want to sign out so that the next person on the same laptop can't act as me.

Acceptance Criteria:

Sign out

Sign out is available from every screen.

After signing out, I return to the sign-in screen and cannot get back in with the browser back action.

State

Signing out does not change any student's status, queue position or session.

A session left open with a student in progress is still in progress when anyone signs in again.

Business Impact:

Risk and compliance: shared venue laptops are the norm; unattributed actions are the main audit gap.

Additional Notes: Depends on CQ-1.

CQ-5 — As an operations lead, I want to open a specific counsellor's desk so that I can help clear a backlog without asking them to hand over their laptop.

Scenario: As the operations lead watching the live view, I see one desk with twelve people waiting. I open that desk and work it directly.

Acceptance Criteria:

Entry

Every counsellor card in the live view has a control to open that desk.

Opening a desk switches my centre context to that counsellor's centre.

Attribution banner

A persistent banner names whose desk I'm viewing.

The banner states that actions are recorded against that counsellor.

The banner carries a control back to live centres.

Capability

I can call, start, complete, note and no-show exactly as that counsellor could.

Notes I add are attributed to the counsellor whose desk it is, not to me.

Boundaries

Opening a desk does not appear in my own navigation as a permanent item.

A counsellor cannot open another counsellor's desk.

Business Impact:

Operational efficiency: lets a lead absorb a spike at one desk instead of the hall waiting for it to clear.

Additional Notes: Depends on CQ-3. Flagged in open questions — attribution of a lead's actions to the counsellor may not be acceptable to the counselling team.

EPIC 2 — Centre and counsellor setup
CQ-6 — As an operations lead, I want to create a counselling centre for a city and date so that students and staff have somewhere to check into before the team travels.

Acceptance Criteria:

Required information

City, venue, date, opening time, closing time and expected student count are captured.

City and venue are mandatory; saving without either shows "City and venue are both needed."

Closing time must be later than opening time.

Defaults and state

A newly created centre is in planned state, not live.

A planned centre accepts no check-ins.

Duplicates

Creating a second centre in the same city on the same date is allowed but shows a warning that one already exists.

Business Impact:

Enablement: unblocks CQ-7 to CQ-12; no standalone user-facing outcome.

CQ-7 — As an operations lead, I want to correct a centre's details after creating it so that a venue change two days before the drive doesn't strand students at the wrong address.

Acceptance Criteria:

Editable fields

City, venue, date, timings and expected students can all be changed.

Edits apply to planned and live centres.

Live centres

Editing a live centre does not reset tokens, queue order or completed sessions.

The new venue appears on student token screens and the hall board immediately.

Bounds

Editing a centre does not change any counsellor's assignment to it.

Business Impact:

Operational efficiency: venue changes are common; without this, the fix is a phone tree.

Additional Notes: Depends on CQ-6.

CQ-8 — As an operations lead, I want to set a centre live on the morning of the drive so that check-ins only open when the hall is actually staffed.

Acceptance Criteria:

Going live

A planned centre can be set live in one action.

Once live, the student check-in page for that centre accepts submissions.

Closing

A live centre can be closed at the end of the day.

Closing shows a confirmation naming how many students are still waiting.

Students still waiting when a centre closes are marked as not counselled, not as no-shows.

Non-existent cases

A closed centre cannot be reopened in this release; a new centre is created instead.

Business Impact:

Operational efficiency: prevents tokens being issued to a hall with no counsellors in it.

Additional Notes: Depends on CQ-6. Closing behaviour for waiting students needs sign-off — see open questions.

CQ-9 — As an operations lead, I want to add a counsellor and say which streams they handle so that students reach someone who can actually advise on their subject.

Acceptance Criteria:

Required information

Name, mobile, centre, desk label and at least one stream are captured.

Saving without a name or without any stream shows "A name and at least one stream are needed."

Streams

Streams offered are Science – PCM, Science – PCB, Science – PCMB, Commerce, Humanities / Arts, Other.

A counsellor may hold any combination, including all six.

Initial state

A newly added counsellor starts off duty and receives no students until they mark themselves on desk.

Desks

Two counsellors at the same centre may not hold the same desk label; the second attempt is rejected with the clash named.

Business Impact:

Conversion quality: stream-matched counselling is the difference between advice and a brochure hand-out.

Additional Notes: Depends on CQ-6. Consumed by CQ-12 and CQ-37.

CQ-10 — As an operations lead, I want to see which streams are uncovered at a centre so that I don't open a hall where commerce students have nobody to talk to.

Acceptance Criteria:

Coverage display

Each centre shows the combined list of streams covered by its assigned counsellors.

Streams with no assigned counsellor are named explicitly as uncovered.

Warning

Setting a centre live with any uncovered stream shows a warning naming the uncovered streams, and allows the lead to continue.

Business Impact:

Conversion: an uncovered stream either turns students away or routes them to the wrong advice.

Additional Notes: Depends on CQ-8 and CQ-9.

CQ-11 — As an operations lead, I want to see each counsellor's roster across upcoming centres so that I don't book the same person into two cities on the same date.

Acceptance Criteria:

Display

The counsellor list shows the centre, city, date and desk each counsellor is posted to.

Conflict

Assigning a counsellor to a second centre on a date they're already assigned shows a conflict warning naming the other city.

Business Impact:

Operational efficiency: double-booking is discovered at the venue today, when it costs a whole desk-day.

Student self check-in
CQ-12 — As a student arriving at a counselling centre, I want to scan the code at the entrance and reach my centre's check-in page so that I can join the queue without standing in a line.

Acceptance Criteria:

Landing

Scanning the centre's code opens the check-in page for that centre only.

The page names the city, venue, date and timings.

No app install, account or password is required.

Wrong or old code

A code for a centre that is not live shows "This centre isn't open for check-in" with the centre's date.

A code for a closed centre shows the closing time and directs the student to the front desk.

Device

The page is usable on a phone held one-handed, on a slow connection, with no horizontal scrolling.

Business Impact:

Activation: self check-in is the mechanism that removes the single-person bottleneck at the door.

Operational efficiency: every self check-in is a desk interaction the front desk doesn't have.

Additional Notes: Depends on CQ-8.

CQ-13 — As a student deciding whether to wait, I want to see how busy the hall is before I fill anything in so that I can judge whether to join now or come back after lunch.

Acceptance Criteria:

Live figures

Number currently waiting across the centre.

Number of counsellors on site.

Average wait so far today.

Empty state

Before any student has been called, average wait shows a dash, not zero.

Refresh

Figures update without the student reloading the page.

Business Impact:

Activation: visible wait reduces abandonment at the door, the loss the current process can't even measure.

Additional Notes: Depends on CQ-12.

CQ-14 — As a student who's never done this before, I want to know what happens after I check in and what I should have with me so that I'm not caught out when I sit down.

Acceptance Criteria:

Process explanation

Three steps are shown: fill details, receive token on WhatsApp, sit anywhere until called.

What to bring

Marksheets, entrance scorecard, photo ID and parent/guardian are listed.

The list is explicitly stated as optional, not mandatory.

Help

Front desk contact number, venue and opening hours are shown on both the landing page and the token page.

Business Impact:

Session quality: students arriving at the desk with documents shortens sessions and reduces follow-ups.

Additional Notes: Depends on CQ-12.

CQ-15 — As a student checking in, I want to give my personal details in one short screen so that the form doesn't feel like an exam.

Acceptance Criteria:

Fields captured

Student name, school, mobile number, parent's contact number, email, stream, class.

Validation

Name is required and must be at least three characters.

School is required.

Mobile must be exactly ten digits; a non-ten-digit entry blocks submission with "A 10-digit mobile number is needed for the turn alert."

Parent's number, if entered, must also be ten digits; blank is accepted.

Email, if entered, must contain a valid address format; blank is accepted.

Error behaviour

All failing fields are reported together on submit, not one at a time.

Entered values are preserved when validation fails.

Stream

Options are exactly the six from CQ-9.

The screen states that the stream chosen decides which counsellor the student is sent to.

Business Impact:

Data quality: the sheet-and-paper process loses numbers and names; validated capture at source is what makes follow-up possible at all.

Additional Notes: Depends on CQ-12. Step one of two; step two is CQ-16.

CQ-16 — As a student, I want to say what I actually need help with before I sit down so that the session starts with my question instead of my name.

Acceptance Criteria:

Fields captured

Course or career being targeted, free text.

Entrance exams being prepared for or considered — multiple selections from JEE, NEET, CUET, CLAT, Other, None / not sure.

How clear the student is about the college or course choice — one of: very clear, have shortlisted options, need help shortlisting, completely confused.

What they'd like help with — multiple selections from college selection, course selection, college and course comparison, admission / counselling, cut-offs and college chances, entrance exams, Other.

Validation

Course or career is required; the screen makes clear that "not sure" is an acceptable answer.

At least one help-with selection is required.

Exams may be left entirely unselected.

"None / not sure" on exams is selectable alongside nothing else; selecting it clears other exam selections.

Navigation

A back control returns to step one with all previously entered values intact.

Progress across the four steps is visible at the top.

Business Impact:

Session quality: the counsellor opens on the student's question, which is where the 15-minute target comes from.

Insight: aggregated help-with and clarity answers are what tell operations how to staff the next city.

Additional Notes: Depends on CQ-15. Mirrors the current paper form exactly.

CQ-17 — As a student, I want to agree to how my details will be used before I hand them over so that I know what I'm consenting to.

Acceptance Criteria:

Consent capture

A single explicit tick is required before the token is issued.

The statement covers counsellor use of the details for advice and contact about admissions, and the right to withdraw.

Consent is not pre-ticked.

Blocking

Submitting without consent shows "Tick the consent line so a counsellor can advise you" and does not issue a token.

Record

The time consent was given is recorded against the student.

A self check-in student is recorded as consent given; no further consent step is asked of them.

Business Impact:

Risk and compliance: the current process has no consent record at all for minors' contact data.

Additional Notes: Depends on CQ-16. Paired with CQ-24 for desk-added students.

CQ-18 — As a student, I want my mobile number verified before the token is issued so that nobody else can book a token against my number.

Acceptance Criteria:

Verification

A code is sent to the number entered.

The token is not issued until a code is entered.

Recovery

A control returns me to the details step to correct the number.

Returning preserves every other answer.

Failure paths

An incorrect code shows "That code doesn't match — check your WhatsApp" and allows a retry.

A resend control is available after a wait.

Business Impact:

Data quality: an unverified number breaks the turn alert and every follow-up after it.

Additional Notes: Depends on CQ-15. Retry limits and resend interval need product sign-off — see open questions.

CQ-19 — As a student, I want a token with my counsellor's name and desk on it so that I know exactly where to go when I'm called.

Acceptance Criteria:

Token content

Token number, stream, counsellor name, desk, venue, check-in time, expected session time, student name and mobile.

Assignment rule

The student is assigned to an on-desk counsellor who covers their stream.

Where more than one qualifies, the one with the shortest queue is chosen.

Where queues are equal, the one with the faster average session is chosen.

Token numbering

The token carries the stream code and a running number for that centre.

Numbers never repeat within a centre-day, including after cancellations and no-shows.

Delivery

The token is shown on screen and sent to the verified WhatsApp number.

Business Impact:

Operational efficiency: replaces the person standing up calling names, which is the stated failure point.

Conversion quality: stream-matched routing at the point of check-in.

Additional Notes: Depends on CQ-9, CQ-17, CQ-18.

CQ-20 — As a student who already has a token, I want to be stopped from taking a second one so that I don't lose my place by checking in twice.

Acceptance Criteria:

Duplicate detection

A check-in with a mobile number that already has a waiting, called or in-session token at the same centre is blocked.

The message names the existing token: "A token is already open for this number — PCM-07."

The student is shown that existing token's live status rather than a dead end.

Permitted repeats

A number whose previous token is completed, released or a no-show may check in again and receives a new number.

Scope

Duplicate checking applies within a centre-day only; the same number may check in at a different city on another date.

Business Impact:

Operational efficiency: duplicate tokens inflate the queue and make wait estimates wrong for everyone behind them.

Additional Notes: Depends on CQ-19.

Student queue experience
CQ-21 — As a waiting student, I want to see how many people are ahead of me and roughly how long it'll be so that I can get a chai instead of standing by the desk.

Acceptance Criteria:

Position

Number of people ahead at my desk, not across the hall.

Estimated wait in minutes.

The expected clock time my turn falls around.

Calculation basis

The estimate uses the actual average session length at that desk so far today.

Before any session completes at that desk, the counsellor's expected session length is used.

The estimate accounts for the session currently running.

Live behaviour

Position and estimate update without the student reloading.

When a student ahead of me is removed or moved, my position updates.

Boundaries

The estimate is always presented as approximate.

Position is never shown as a negative number or zero while I'm still waiting.

Business Impact:

Abandonment: visible progress is what keeps a student in the building for a 40-minute wait.

Additional Notes: Depends on CQ-19.

CQ-22 — As a waiting student, I want a clear heads-up when I'm next so that I'm at the desk when my name comes up.

Acceptance Criteria:

Next state

When nobody is ahead of me, the screen states that I'm next and names the desk to stay near.

The position and estimate block is replaced by this state, not shown alongside it.

Board consistency

My token shows as next up on the hall board for that desk at the same time.

Business Impact:

Operational efficiency: reduces the recall and no-show rate, which is what stalls a desk between students.

Additional Notes: Depends on CQ-21.

CQ-23 — As a student being called, I want to be told it's my turn and where to go so that I don't miss my slot while sitting twenty feet away.

Acceptance Criteria:

On-screen state

The screen states it's my turn and names the desk and counsellor.

It states that my place is held for two calls.

Message

A WhatsApp goes to my verified number at the same moment.

Persistence

The called state stays on screen until the counsellor starts, completes or releases the session.

Business Impact:

Operational efficiency: the stated problem — students missing their turn — is removed by a message rather than a raised voice.

Additional Notes: Depends on CQ-22 and CQ-39.

CQ-24 — As a student the front desk checked in for me, I want to confirm on my own phone that it's me and that I agree to how my details are used so that consent is mine and not typed by someone else.

Acceptance Criteria:

Trigger

A student added by the front desk is recorded as consent pending.

A WhatsApp asks them to confirm identity and agree to counselling use.

Confirmation

A single action on the student's phone records consent and the time it was given.

The token screen shows consent pending until then.

Fallbacks

The counsellor can record consent given verbally at the desk, attributed to the counsellor.

A session cannot be started while consent is pending.

Business Impact:

Risk and compliance: closes the gap where staff-entered students have no recorded consent.

Additional Notes: Depends on CQ-29 and CQ-42.

CQ-25 — As a student who has to leave, I want to give up my turn so that the queue behind me isn't waiting on somebody who's gone.

Acceptance Criteria:

Release

Release is available while waiting or called; not once a session has started.

A confirmation is required before releasing.

Effects

The token moves to released and leaves every queue and the board.

Everyone behind me moves up and their estimates recalculate.

A WhatsApp confirms the release and states I can check in again before closing.

Return

Checking in again issues a new token number; the old one is not reinstated.

Business Impact:

Wait accuracy: phantom tokens are what make estimated waits wrong, which is what destroys trust in them.

Additional Notes: Depends on CQ-21.

CQ-26 — As a student who closed the page or lost the message, I want to get back to my live token so that I don't have to check in again and go to the back of the queue.

Acceptance Criteria:

Recovery on device

Reopening the check-in page on the same phone returns me to my live token, not to a blank form.

Recovery elsewhere

The WhatsApp confirmation carries a link back to the live token.

Last resort

The token page states that the front desk can find a token from the mobile number.

Business Impact:

Abandonment: a lost slip is currently an unrecoverable place in the queue.

Additional Notes: Depends on CQ-19 and CQ-34.

CQ-27 — As a student mid-session and after it, I want my screen to reflect where I actually am so that I'm not still watching a queue position while sitting in front of the counsellor.

Acceptance Criteria:

In session

Once the counsellor starts, the screen states the session is in progress and names counsellor and desk.

Position, estimate and release controls are removed.

Completed

Once marked done, the screen states the session is complete and that the shortlist and next steps are coming.

Missed twice

A student marked no-show sees that they were called twice and is directed to the front desk to rejoin.

Business Impact:

Operational efficiency: removes the "am I still in the queue?" questions that go to the front desk.

Additional Notes: Depends on CQ-23, CQ-40, CQ-46.

CQ-28 — As a student who has just finished, I want to rate the session so that the team knows which counsellors are actually helping.

Acceptance Criteria:

Prompt

A one-to-five rating appears on the token screen once the session is complete.

The same prompt is sent on WhatsApp.

Behaviour

Rating is optional; the screen is fully usable without it.

Once submitted, the rating is shown back and cannot be changed.

Reporting

Ratings roll up per counsellor and per centre.

Business Impact:

Quality: the only direct read on counselling quality; currently there is none.

Additional Notes: Depends on CQ-27.

Front desk
CQ-29 — As a receptionist, I want to check in a student who can't do it themselves so that nobody is excluded for not having a phone or data.

Acceptance Criteria:

Questions

The desk form captures exactly the same questions as the student form in CQ-15 and CQ-16.

Fields are grouped as "who they are" and "what they want from the session".

Validation

Name and ten-digit mobile are required.

Parent's number, if entered, must be ten digits.

At least one help-with selection is required.

All failing fields report together on submit.

Outcome

The token issues under the same assignment rule as CQ-19.

A confirmation names the token and the counsellor it went to.

The student is recorded as added at reception, with consent pending per CQ-24.

After submit

The desk returns to the hall queue with the new token visible.

The form clears fully, ready for the next student.

Business Impact:

Inclusion: students without smartphones are a material share of tier-2 and tier-3 footfall.

Data quality: the desk path captures the same fields, so records are consistent regardless of entry route.

Additional Notes: Depends on CQ-9.

CQ-30 — As a receptionist, I want to be warned when the number I'm typing already has a token so that I don't issue a second one to the same student.

Acceptance Criteria:

Detection

The duplicate rule from CQ-20 applies to desk-entered check-ins.

The existing token number is named in the message.

Action

The receptionist can open the existing token record directly from the warning.

No token is issued while the duplicate stands.

Business Impact:

Wait accuracy: duplicate entries at the desk are the likeliest source, since the student can't see their own record.

Additional Notes: Depends on CQ-29.

CQ-31 — As a receptionist, I want to see everyone currently in the hall in one list so that I can answer "how long more?" without walking to a desk.

Acceptance Criteria:

Content

Every student currently waiting, called or in session at my centre.

Each row shows token, name, counsellor, desk, stream, mobile and time waited.

Ordered by check-in time, earliest first.

Status

Each row carries its status.

Rows with consent still pending are flagged.

Empty state

With nobody waiting, the list states that tokens appear as students scan in.

Business Impact:

Operational efficiency: replaces the sheet the desk currently keeps, and the walk to each counsellor.

Additional Notes: Depends on CQ-19 and CQ-29.

CQ-32 — As a receptionist, I want to see the hall split by counsellor so that I can tell at a glance which desk is drowning.

Acceptance Criteria:

Tabs

The first tab is all students and is selected by default.

One tab follows per counsellor at the centre, in desk order.

Each tab shows a live count of students currently in that desk's queue.

Overdue flag

A tab whose queue contains anyone past the wait promise carries a late badge with the count.

Behaviour

Selecting a tab filters the list to that counsellor only.

The selected tab persists while I work elsewhere in the queue and return.

Edge cases

A counsellor who is off duty still gets a tab if students are assigned to them.

A counsellor with an empty queue shows a zero count, not a hidden tab.

Business Impact:

Operational efficiency: the load imbalance that currently goes unnoticed until a student complains becomes visible in one glance.

Additional Notes: Depends on CQ-31.

CQ-33 — As a receptionist, I want anyone waiting too long to stand out so that I can act before they walk out.

Acceptance Criteria:

Threshold

A wait promise is defined for the centre; students past it are flagged.

The flag appears on the row, on the counsellor's tab and as a hall-level count in the header.

Behaviour

The flag clears the moment the student is called.

A student who is called, missed and returned to the queue has their waiting time measured from the point they rejoined.

Business Impact:

Abandonment: the stated failure — students who get left out entirely — becomes a visible, actionable state.

Additional Notes: Depends on CQ-32.

CQ-34 — As a receptionist, I want to find any student from today by name, number or token so that "I lost my slip" takes ten seconds.

Acceptance Criteria:

Search scope

Matches on name, mobile number or token.

Partial matches are supported, including the last four digits of a number.

Searching covers every status for the day, including completed, no-show and released — not just those waiting.

Behaviour

Search sits above the counsellor tabs and takes precedence over the selected tab.

Clearing search returns to the previously selected tab.

The result count is stated.

Empty state

No match shows the searched term back and suggests trying the last four digits.

Business Impact:

Operational efficiency: merges the lost-token desk job into the queue screen instead of a separate register.

Additional Notes: Depends on CQ-32.

CQ-35 — As a receptionist, I want to move a student to a different counsellor so that a long queue at one desk doesn't make someone wait for no reason.

Acceptance Criteria:

Action

Any waiting student's row offers a move to another counsellor at the same centre.

The picker shows each counsellor's current queue length.

The student's current counsellor is not offered.

Effects

The token number does not change.

The student joins the new queue at their original check-in time, not at the back.

A WhatsApp tells the student the new counsellor and desk and confirms the token is unchanged.

Restrictions

A student in session cannot be moved.

A student may be moved to a counsellor who doesn't cover their stream, with a warning shown first.

Business Impact:

Wait time: manual load balancing for the cases the automatic rule can't foresee, such as a counsellor leaving early.

Additional Notes: Depends on CQ-31.

CQ-36 — As a receptionist, I want to put a missed or finished student back in the queue so that someone who stepped out isn't written off for the day.

Acceptance Criteria:

Eligibility

Available for students marked no-show, released or completed.

Not available for students currently waiting, called or in session.

Effects

The student returns as waiting with their original token number.

Their wait time restarts from the point they rejoined.

Their recall count resets, giving them a fresh two calls.

Record

The rejoin is visible on the student's record, including who did it and when.

Business Impact:

Recovery: turns a no-show into a counselled student instead of a lost lead.

Additional Notes: Depends on CQ-34 and CQ-46.

Counsellor desk
CQ-37 — As a counsellor, I want to mark myself on desk, on a break or off duty so that students stop being queued to an empty chair.

Acceptance Criteria:

States

Exactly three: on desk, on break, off duty.

The current state is always visible on my queue screen.

Effects

Only on-desk counsellors receive new automatic assignments.

Going on break or off duty does not move students already in my queue.

My state shows on the hall board and in the front desk load view.

Edge case

Going on break with a session in progress is allowed; the session continues.

Business Impact:

Wait time: routing to an absent counsellor is a queue that never moves, which is what the current process can't detect at all.

Additional Notes: Depends on CQ-9. Consumed by CQ-19.

CQ-38 — As a counsellor, I want to see my queue and my day's numbers when I sit down so that I know where I stand without asking anyone.

Acceptance Criteria:

Header figures

Number in my queue and number waiting across the hall.

Number I've counselled today.

My average session length against the target.

Number in my queue past the wait promise.

Queue list

Ordered by check-in time, earliest first.

Each row shows token, name, stream, class, time waited, and whether they self checked in or were added at the desk.

The next student is visually distinguished from the rest.

Consent-pending students are flagged in the list.

Empty state

An empty queue states that new check-ins land here as students scan in.

Centre context

The centre, venue, date and hours I'm working are named on the screen.

Business Impact:

Operational efficiency: replaces the shared sheet and the person calling names.

Additional Notes: Depends on CQ-19 and CQ-37.

CQ-39 — As a counsellor, I want to call the next student with one action so that I'm not deciding who's next between every session.

Acceptance Criteria:

Action

One control calls the longest-waiting student in my queue.

The control names the token it will call.

Guards

The control is unavailable while I already have a called or in-session student, with an explanation naming that token.

The control is unavailable when my queue is empty.

Effects

The student moves to called and the call time is recorded.

The student is notified per CQ-23.

My screen moves to the live session view.

Business Impact:

Operational efficiency: the core fix for "nobody knows who's next", stated as the main pain.

Additional Notes: Depends on CQ-38.

CQ-40 — As a counsellor, I want to call a specific token a student reads out to me so that someone who walked up out of order is still handled properly.

Acceptance Criteria:

Entry

A token can be typed and called directly.

Entry is case-insensitive and tolerant of surrounding spaces.

Validation

A token that doesn't exist at this centre today shows "No token PCM-22 at this centre today."

A token already completed shows the time it was counselled.

A released token is reported as released, with a route to rejoin it.

Cross-desk

Calling a token assigned to another desk reassigns it to me and notifies the student of the change.

This is allowed even when the student's stream isn't one of mine, with a warning.

Business Impact:

Operational efficiency: handles the out-of-order reality of a hall without breaking the record of who saw whom.

Additional Notes: Depends on CQ-39.

CQ-41 — As a counsellor, I want to pull a specific student forward so that a student who's been waiting far too long or has a train to catch can be seen next.

Acceptance Criteria:

Action

Any waiting student below the top of my queue can be pulled to the front.

The top student has no pull-forward control.

Effects

The pulled student becomes next; everyone else keeps their relative order.

Wait estimates recalculate for everyone in the queue.

Record

The record shows the student was pulled forward and by whom.

Business Impact:

Fairness and recovery: gives the desk a sanctioned way to handle the exceptions that otherwise become queue-jumping.

Additional Notes: Depends on CQ-38.

CQ-42 — As a counsellor, I want consent in place before I start so that I'm not advising a student whose details I'm not cleared to use.

Acceptance Criteria:

Blocking

The start control is unavailable while consent is pending.

The reason is stated on screen, not left to be guessed.

Routes to consent

The student's own confirmation from WhatsApp clears it (CQ-24).

The counsellor can record consent taken verbally, attributed to the counsellor with a timestamp.

The consent request WhatsApp can be resent from the session screen.

Non-existent cases

Self checked-in students never reach this state, as consent is captured in their form.

Business Impact:

Risk and compliance: makes the consent gate a hard stop rather than an instruction in a briefing.

Additional Notes: Depends on CQ-24.

CQ-43 — As a counsellor, I want to see what the student told us at check-in the moment they sit down so that I don't spend the first three minutes asking what I already know.

Acceptance Criteria:

Content

Course or career targeted, school, parent's contact, stated clarity level.

Entrance exams selected, shown as a set.

Help-with selections, shown as a set.

Unanswered fields

Optional fields left blank show as not answered, not as empty space.

Placement

This appears above the editable details on the live session screen.

Business Impact:

Session quality: recovers the opening minutes of a 15-minute session, directly supporting throughput.

Additional Notes: Depends on CQ-16 and CQ-29.

CQ-44 — As a counsellor, I want to correct or add to the student's details during the session so that a rushed form entry doesn't become a wrong record forever.

Acceptance Criteria:

Editable fields

Name, school, mobile, parent's contact, email, stream, class, targeted course, clarity level.

Home city, target exam, budget, colleges discussed, follow-up date, who accompanied them.

Behaviour

Saving confirms on screen.

Changing the stream does not change the token number or move the student to another desk mid-session.

Validation

Mobile and parent's contact keep the ten-digit rule.

Clearing a required field is rejected with the field named.

Business Impact:

Data quality: the record captured at the desk is the one that feeds follow-up; this is where it gets corrected.

Additional Notes: Depends on CQ-43.

CQ-45 — As a counsellor, I want to write notes during the session so that whoever follows up knows what was actually discussed.

Acceptance Criteria:

Adding

Free-text notes can be added at any point during a session.

Each note records the time and the counsellor's name.

Submitting an empty note is rejected.

Display

Notes show newest last, in time order, with author and time.

Existing notes stay visible while a new one is written.

Persistence

Notes remain on the record after the session is completed.

Notes cannot be deleted in this release.

Business Impact:

Follow-up conversion: a follow-up call with the session context beats a cold call to a name on a sheet.

Additional Notes: Depends on CQ-43.

CQ-46 — As a counsellor, I want a student who doesn't turn up to be handled automatically so that I'm not stuck holding a desk for someone who's gone.

Acceptance Criteria:

First miss

Marking a called student as not turned up returns them to the queue.

Their wait time restarts from that moment.

A WhatsApp tells them they were missed and that the next call is the last.

Second miss

A second miss marks them a no-show and removes them from the queue.

A WhatsApp directs them to the front desk to rejoin.

After

My desk is free to call the next student immediately in both cases.

The recall count is visible on the student's record.

Business Impact:

Operational efficiency: the dead time between students is the largest recoverable loss in a counselling day.

Additional Notes: Depends on CQ-39. Two calls before no-show; confirm with the counselling team — see open questions.

CQ-47 — As a counsellor, I want to see how long the current session has run so that I keep to a pace that clears the queue.

Acceptance Criteria:

Timer

Runs from the moment the session starts, visible on the session screen.

Shows elapsed time and the target length.

Over target

Crossing the target changes the timer state and shows how many students are still waiting for me.

The session is never ended automatically.

Non-existent cases

No timer is shown before a session has been started.

Business Impact:

Throughput: session length is the single biggest lever on how many students a centre-day can serve.

Additional Notes: Depends on CQ-42.

CQ-48 — As a counsellor, I want to record where the conversation landed and when to follow up so that the session turns into an action instead of a memory.

Acceptance Criteria:

Outcome

One of: ready to apply, interested and needs time, just exploring, not a fit.

Outcome may be left unset; unset is reported distinctly from any chosen value.

Follow-up

A follow-up date can be set; it may not be in the past.

Colleges discussed are captured as free text.

Reporting

Outcomes roll up per counsellor and per centre.

Business Impact:

Revenue: the outcome field is what converts a counselling day into a prioritised lead list.

Additional Notes: Depends on CQ-44.

CQ-49 — As a counsellor, I want to mark the session done so that my desk clears and the next student is called up.

Acceptance Criteria:

Completion

Completing records the end time and moves the student to completed.

My desk becomes free to call the next student.

The confirmation names the next token in my queue, or states the queue is now clear.

Student side

A post-session WhatsApp goes out per CQ-57.

The student's screen moves to the completed state.

Guards

A session cannot be completed before it has been started.

Business Impact:

Operational efficiency: the completion step is what keeps every wait estimate in the hall accurate.

Additional Notes: Depends on CQ-47.

CQ-50 — As a counsellor, I want to see everyone I've handled today and what's still to come so that I can review my own day without asking the lead.

Acceptance Criteria:

My students

Every student assigned to me at this centre, newest first, whatever their status.

Each row shows wait, session length, outcome and status.

My centres

Every centre I'm rostered to, with date, venue, hours, my desk and the student count so far.

Live centres are distinguished from upcoming ones.

A live centre offers a direct route into today's queue.

Scope

I cannot see students assigned to other counsellors.

Business Impact:

Operational efficiency: removes the end-of-day reconciliation between counsellor memory and the shared sheet.

Additional Notes: Depends on CQ-3.

Hall display board
CQ-51 — As a student sitting in the hall, I want a screen showing what each desk is serving so that I can follow the queue without watching my phone.

Acceptance Criteria:

Content

One panel per counsellor at the centre, showing desk, counsellor name and the token being served.

Next token and waiting count per desk.

Centre name, venue, date, current time and total waiting.

Empty desk

A desk with nobody in session shows a dash, visually dimmed, not a stale token.

Legibility

Token numbers are the largest element and readable across a hall.

Refresh

The board updates itself with no staff interaction.

Business Impact:

Abandonment: the queue becomes visible to the whole room, which is what the banking token model gets right.

Additional Notes: Depends on CQ-39.

CQ-52 — As a student who stepped out, I want the board to show recently called tokens so that I can tell whether I've been passed.

Acceptance Criteria:

Recently called

The last six called tokens are shown, most recent first.

With none called yet, the strip states nothing has been called.

Standing instruction

The board carries a line telling students to scan at the entrance and keep their phone on.

Business Impact:

Recovery: a student who sees their number just passed goes to the desk instead of waiting indefinitely.

Additional Notes: Depends on CQ-51.

CQ-53 — As a student, I want the board to tell me when a desk is on a break or closed so that I'm not watching a panel that will never move.

Acceptance Criteria:

States

On break shows "back shortly" in place of the next-token line.

Off duty shows the desk as closed.

An on-desk counsellor with an empty queue shows "queue clear".

Consistency

The state matches the counsellor's own setting from CQ-37 with no manual board update.

Business Impact:

Operational efficiency: removes the "is anyone coming back?" questions that go to the front desk.

Additional Notes: Depends on CQ-37 and CQ-51.

Messaging
CQ-54 — As a student, I want my token confirmed on WhatsApp so that I have it even if my browser closes.

Acceptance Criteria:

Trigger and content

Sent the moment a token is issued.

Names the city, token, counsellor and desk, and states that a turn alert will follow.

Route variants

A self check-in gets the confirmation only.

A desk-added student gets a confirmation that also asks for identity and consent confirmation.

Business Impact:

Recovery: WhatsApp is the fallback record when the phone, the browser or the paper slip fails.

Additional Notes: Depends on CQ-19 and CQ-29.

CQ-55 — As a student, I want a message when it's my turn so that I can wander the venue without losing my place.

Acceptance Criteria:

Trigger and content

Sent when the counsellor calls the token.

Names the desk and counsellor, and asks for confirmation of arrival and consent where consent is still pending.

Business Impact:

Operational efficiency: the message is what replaces the person standing up and shouting names.

Additional Notes: Depends on CQ-39.

CQ-56 — As a student who missed a call, I want to be told what happens next so that I know whether I still have a place.

Acceptance Criteria:

First miss

States the token was called and missed, that they're back in the queue, and that the next call is the last.

Second miss

States the number of calls made and directs them to the front desk.

Desk change

A reassigned student is told the new counsellor and desk, and that the token is unchanged.

Release

A released token is confirmed, with a note that they can check in again before closing.

Business Impact:

Recovery: each of these is a case where the student currently just disappears.

Additional Notes: Depends on CQ-46, CQ-35, CQ-25.

CQ-57 — As a student who has finished, I want a closing message so that I know what's coming and can rate the session.

Acceptance Criteria:

Content

Thanks the student, names the counsellor, states that the shortlist and next steps follow, and invites a one-to-five rating.

Timing

Sent when the session is marked done.

Business Impact:

Follow-up conversion: sets the expectation that a follow-up is coming, which is what makes the follow-up call answerable.

Additional Notes: Depends on CQ-49 and CQ-28.

CQ-58 — As a receptionist, I want to know when a message didn't reach a student so that I can catch them in the hall instead of assuming they were told.

Acceptance Criteria:

Failure surfacing

A student whose turn alert failed to deliver is flagged in the hall queue.

The flag names which message failed.

Fallback

The counsellor's screen shows the same flag, so the desk knows a verbal call is needed.

A resend control is available from the student's record.

Scope

Delivery failure never changes the student's queue position or status.

Business Impact:

Risk: silent message failure reintroduces exactly the "student never got called" problem the product exists to fix.

Additional Notes: Depends on CQ-55. Delivery-status behaviour needs confirmation against the messaging provider — see open questions.

Records and insights
CQ-59 — As an operations lead, I want to see every student who has ever attended a centre, filtered however I need so that I can answer a question about one student or one city without a spreadsheet.

Acceptance Criteria:

Content

Every student across all centres, newest first.

Each row shows token, name, mobile, school, stream, targeted course, centre, date, counsellor, wait, session length, outcome and status.

Filters

Free text on name, mobile or token.

Counsellor.

Centre.

Stream.

Status.

Filters combine; a clear-all control resets them.

The count of matching records against the total is stated.

Empty state

No matches states so without clearing the filters the lead has set.

Business Impact:

Operational efficiency: replaces the per-city sheets that currently can't be queried together.

Revenue: the filtered lead list is what the post-drive follow-up works from.

Additional Notes: Depends on CQ-19.

CQ-60 — As an operations lead, I want to export the student records so that the follow-up team can work them in their own tools.

Acceptance Criteria:

Export content

Token, name, school, mobile, parent contact, email, stream, class, targeted course, entrance exams, clarity, help wanted, city, date, counsellor, check-in time, call time, wait, session length, status, outcome, follow-up date and notes.

Behaviour

The export reflects the filters currently applied, not the whole database.

The file is named so that the centre and date are identifiable.

Access

Only the operations lead role can export.

Business Impact:

Revenue: the export is the handover point between the counselling day and the admissions funnel.

Risk and compliance: restricting export to one role limits where minors' contact data can travel.

Additional Notes: Depends on CQ-59. Access restriction to be confirmed against Careers360's data handling policy.

CQ-61 — As an operations lead, I want to see demand, waits and what students asked for so that I staff the next city against evidence instead of last year's guess.

Acceptance Criteria:

Headline figures

Students counselled or queued, average wait against the promise, average session against the target, no-show rate.

Demand

Student count per stream, ranked, shown proportionally.

Intake breakdown

Count per help-with option, ranked.

Count per clarity level.

Outcomes

Count per outcome, with an explicit count of records where no outcome was set.

Follow-ups scheduled and average student rating with the number of ratings behind it.

Empty and thin data

Metrics with no data show a dash, never zero.

Averages state the number of records they're computed from.

Business Impact:

Operational efficiency: stream demand drives counsellor mix for the next city; clarity mix predicts session length and therefore how many desks a hall needs.

Quality: average rating and no-show rate are the two numbers that say whether a centre-day went well.