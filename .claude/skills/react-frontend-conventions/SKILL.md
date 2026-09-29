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
