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
