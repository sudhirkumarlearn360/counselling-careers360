# Scope by phase (CounselQueue CMS)

Agreed in the CounselQueue scope discussion. Anything marked **Phase 2 / Future** is built and kept in the code
but hidden in the UI behind a flag in `frontend/src/lib/phase.ts` (set `VITE_PHASE2=all` to switch everything on for a demo).
The backend API is unchanged, so switching a feature on needs no server work.

| Item | Decision | Where it is applied |
|---|---|---|
| Hall Board | **Phase 2** | nav item hidden; `/console/board` redirects; public `/board/:slug` says "coming in Phase 2" |
| Student Status | **Phase 2** | Status column + filter hidden on All students / My students |
| Insights | **Phase 2** | nav item hidden; `/console/insights` redirects |
| Hall Queue | **Phase 2 for the operations lead** (front desk keeps theirs) | ops nav item hidden; reception unchanged |
| Page Editor | **Phase 2** | not built |
| Call a Student from My Queue | **Future** | "Call a token" box hidden; "Call {next}" stays |
| Pull Forward from My Queue | **Future** | button hidden |
| "What they said at check-in" | **Future** | intake summary hidden; the Live session shows the required student details/edit form only |
| Check-in / Waited / Session in Student Detail | **Future** | Wait / Session columns hidden |
| Student Detail fields / duty states | **Finalised** | duty labels are **On Desk, On Break, Off Duty** |
| Add a Centre | **Changed** | Email and Password fields added: they create the centre's front-desk sign-in (`POST ops/centres`; password ≥ 8 chars, write-only; editable later) |
| Venue filter | **Changed** | on All students, Venue options depend on the selected Centre; changing the Centre resets the Venue |
| All Students filters | **Changed** | filters are staged and take effect on **Apply**; **Clear** resets them |

Open points to confirm with Product: which screen "Student Status" refers to (applied to the status column and filter on
the records lists), and whether the front desk's Hall queue stays in Phase 1 (assumed yes).
