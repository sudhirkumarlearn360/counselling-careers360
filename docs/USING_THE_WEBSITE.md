# Using CounselQueue (demo guide + logins)

> Local demo credentials only (created by `seed_demo` when `DEBUG=True`). Don't reuse them anywhere real.

## Start it
```bash
./setup.sh run        # first time on a laptop: installs, migrates, seeds, starts both servers
```
Later: `cd backend && .venv/bin/python manage.py runserver 8000` and `cd frontend && npm run dev`.
Re-seed demo data any time: `cd backend && .venv/bin/python manage.py seed_demo`.

| Service | URL |
|---|---|
| Website (frontend) | http://localhost:5173 |
| API (backend) | http://localhost:8000/api/1 |

## Staff logins  (http://localhost:5173/console/login)

| Role | Email | Password | Sees |
|---|---|---|---|
| Operations lead (Nikhil Bhatia) | `admin@careers360.com` | `admin123` | Live centres, Centres & dates, Counsellors, All students |
| Front desk (Pooja Menon) | `reception@careers360.com` | `desk123` | Hall queue, Add a student |
| Counsellor – Meera Iyer (Desk 1, Gwalior) | `meera@careers360.com` | `desk123` | My queue, Live session, My students, My centres |
| Counsellor – Rahul Verma (Desk 2, Gwalior) | `rahul@careers360.com` | `desk123` | same |
| Counsellor – Aditi Sharma (Desk 3, Gwalior, on break) | `aditi@careers360.com` | `desk123` | same |
| Counsellor – Farid Khan (Desk 1, Indore) | `farid@careers360.com` | `desk123` | same |
| Counsellor – Nisha Rao (Desk 2, Indore) | `nisha@careers360.com` | `desk123` | same |

Counsellor streams: Meera PCM/PCMB · Rahul PCB/PCMB · Aditi COM/HUM/OTH · Farid PCM/COM · Nisha PCB/OTH.

## Student pages (no login)

| Centre | Check-in link (the QR opens this) | Status |
|---|---|---|
| Gwalior – Hotel Landmark | http://localhost:5173/c/gwalior-demo | Live today |
| Indore – Brilliant Convention Centre | http://localhost:5173/c/indore-demo | Planned (+2 days) |
| Jaipur – Hotel Clarks Amer | http://localhost:5173/c/jaipur-demo | Planned (+5 days) |

- **OTP:** `1234` (stub provider, no real WhatsApp/SMS is sent).
- Live token page: `http://localhost:5173/t/<access_key>` (shown after check-in).
- Hall board (Phase 2, hidden): `http://localhost:5173/board/gwalior-demo`.

Seeded students (already checked in at Gwalior), student mobile → parent mobile:
Ankit Patel `9000010001`→`9000020001`, Priya Nair `9000010002`→`9000020002`, Sahil Yadav `9000010003`→`9000020003`,
Fatima Sheikh `9000010004`→`9000020004`, Devansh Gupta `9000010005`→`9000020005`, Ritika Bose `9000010006`→`9000020006`,
Karan Singh, Sneha Kulkarni, Mohit Raj (numbers in `backend/apps/queue/management/commands/seed_demo.py`).
Use a **new** mobile number to check in as a fresh student; an existing one is flagged as a duplicate.

## Walkthrough of a counselling day
1. **Student:** open `/c/gwalior-demo` → fill details (name, mobile, class, stream, goals) → enter OTP `1234` → gets a token and a live status page (position, ETA).
2. **Front desk:** sign in as `reception@…` → *Hall queue* shows everyone waiting; *Add a student* checks in walk-ins by hand.
3. **Counsellor:** sign in as `meera@…` → *My queue* → **Call next** (student is alerted) → *Live session* to take notes/outcome and finish → next.
4. **Operations lead:** sign in as `admin@…` → *Live centres* for the whole hall, *Centres & dates* to add/edit a centre (creates its front-desk login), *Counsellors*, *All students* (filters + CSV export).

## Other
- Django admin: none seeded. Create one with `cd backend && .venv/bin/python manage.py createsuperuser`, then http://localhost:8000/admin.
- Config: `backend/.env` (`SECRET_KEY`, `OTP_STUB_CODE=1234`, `FRONTEND_BASE_URL`, …) and `frontend/.env` (`VITE_API_URL`).
- Show Phase 2 screens (Hall board, Insights): set `VITE_PHASE2=all` in `frontend/.env` and restart `npm run dev`.
- Reset everything: delete `backend/db.sqlite3`, then `./setup.sh`.
