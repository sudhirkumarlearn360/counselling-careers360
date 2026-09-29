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
