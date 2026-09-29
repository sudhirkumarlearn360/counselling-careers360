#!/usr/bin/env python3
"""End-to-end smoke test against a running backend (seeded with `manage.py seed_demo`).

    backend/.venv/bin/python manage.py runserver 8000     # in backend/
    python3 scripts/smoke_e2e.py [http://127.0.0.1:8000/api/1]

Drives a whole counselling day over HTTP: student check-in with OTP, front-desk check-in, counsellor
call/consent/start/complete, rating, hall board, ops insights and CSV export, sign-out.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/1").rstrip("/")
SLUG = "gwalior-demo"
steps = []


def call(method, path, body=None, token=None, raw=False):
    req = urllib.request.Request(f"{BASE}/{path}", method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            payload = r.read()
            return r.status, (payload if raw else json.loads(payload)), r.headers
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def ok(label, cond, detail=""):
    steps.append((label, bool(cond)))
    print(("PASS " if cond else "FAIL ") + label + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        sys.exit(1)


def login(email, password):
    s, b, _ = call("POST", "auth/login", {"email": email, "password": password})
    ok(f"sign in {email}", s == 200, b)
    return b["data"]["access"], b["data"]["refresh"], b["data"]["user"]


# --- student ---------------------------------------------------------------------------------------
s, b, _ = call("GET", f"public/centres/{SLUG}")
ok("landing is open for check-in", s == 200 and b["data"]["open"], b)
mobile = "98110 77001"
s, b, _ = call("POST", f"public/centres/{SLUG}/otp/send", {"mobile": mobile})
ok("OTP sent", s in (200, 429), b)  # 429 = re-run within the resend wait: the previous code is still valid
s, b, _ = call("POST", f"public/centres/{SLUG}/otp/verify", {"mobile": mobile, "code": "1234"})
ok("OTP verified", s == 200, b)
vid = b["data"]["verification_id"]
form = {"name": "Smoke Student", "school": "DPS Gwalior", "mobile": mobile, "stream": "PCM", "klass": "Class 12",
        "course": "B.Tech", "exams": ["JEE"], "clarity": "Need help shortlisting", "help": ["College selection"],
        "consent": True, "verification_id": vid}
s, b, _ = call("POST", f"public/centres/{SLUG}/check-in", form)
ok("student token issued", s == 201, b)
key, token = b["data"]["access_key"], b["data"]["token"]["token"]
print(f"     token {token} → {b['data']['token']['counsellor']} at {b['data']['token']['desk']}")
s, b, _ = call("POST", f"public/centres/{SLUG}/check-in", form)
ok("verification can't be reused", s == 400 and b["code"] == "verification_required", b)

# --- front desk ------------------------------------------------------------------------------------
racc, rref, ruser = login("reception@careers360.com", "desk123")
centre_id = ruser["centre"]["id"]
s, b, _ = call("POST", f"hall/centres/{centre_id}/check-in",
               {"name": "Walk In", "mobile": "9811077002", "stream": "PCM", "help": ["Course selection"]}, racc)
ok("desk check-in issues a token", s == 201 and "issued to" in b["message"], b)
desk_token, desk_id = b["data"]["token"], b["data"]["id"]
s, b, _ = call("POST", f"hall/centres/{centre_id}/check-in",
               {"name": "Walk In", "mobile": "9811077002", "stream": "PCM", "help": ["Course selection"]}, racc)
ok("duplicate at the desk is blocked", s == 409 and desk_token in b["message"], b)
s, b, _ = call("GET", f"hall/centres/{centre_id}/queue", token=racc)
tokens = [r["token"] for r in b["data"]["rows"]]
ok("hall queue lists both new tokens", token in tokens and desk_token in tokens, tokens)
ok("hall tabs: All first", b["data"]["tabs"][0]["key"] == "all")
s, b, _ = call("GET", f"hall/centres/{centre_id}/queue?q=7002", token=racc)
ok("search by last four digits", [r["token"] for r in b["data"]["rows"]] == [desk_token])

# --- counsellor ------------------------------------------------------------------------------------
macc, mref, muser = login("meera@careers360.com", "desk123")
s, b, _ = call("GET", "desk/queue", token=macc)
ok("desk queue loads", s == 200 and b["data"]["centre"]["city"] == "Gwalior", b)
cur = b["data"]["current"]
if cur:  # the seed leaves a session in progress: finish it so the desk is free
    if cur["status"] == "called":
        call("POST", f"desk/students/{cur['id']}/start", token=macc)
    s, b, _ = call("POST", f"desk/students/{cur['id']}/complete", token=macc)
    ok("finished the seeded session", s == 200, b)
s, b, _ = call("POST", "desk/call-token", {"token": token.lower()}, macc)
ok("call by token (case-insensitive)", s == 200 and b["data"]["current"]["token"] == token, b)
s, b, _ = call("GET", f"public/tokens/{key}")
ok("student sees it's their turn", b["data"]["state"]["kind"] == "called", b)
s, b, _ = call("POST", "desk/call-next", token=macc)
ok("second call is blocked while a student is called", s == 409 and "Finish" in b["message"], b)
s, q, _ = call("GET", "desk/queue", token=macc)
me = q["data"]["current"]
s, b, _ = call("POST", f"desk/students/{me['id']}/start", token=macc)
ok("session starts (self check-in consent given)", s == 200 and b["data"]["current"]["status"] == "in_session", b)
s, b, _ = call("POST", f"desk/students/{me['id']}/notes", {"text": "Interested in NIT Bhopal."}, macc)
ok("note added", s == 201 and b["data"]["notes"][0]["author"] == "Meera Iyer", b)
s, b, _ = call("PATCH", f"desk/students/{me['id']}", {"outcome": "ready", "budget": "4-8 L"}, macc)
ok("outcome saved", s == 200 and b["data"]["outcome"] == "ready", b)
s, b, _ = call("POST", f"desk/students/{me['id']}/complete", token=macc)
ok("session completed", s == 200 and "Done" in b["data"]["message"], b)

# --- student after the session ----------------------------------------------------------------------
s, b, _ = call("GET", f"public/tokens/{key}")
ok("token page shows session complete and can be rated", b["data"]["state"]["kind"] == "done" and b["data"]["can_rate"], b)
s, b, _ = call("POST", f"public/tokens/{key}/rating", {"rating": 5})
ok("rated 5", s == 200 and b["data"]["rating"] == 5, b)
s, b, _ = call("POST", f"public/tokens/{key}/rating", {"rating": 4})
ok("rating can't be changed", s == 409, b)
s, b, _ = call("GET", f"public/board/{SLUG}")
ok("board shows the recently called token", token in b["data"]["recently_called"], b["data"]["recently_called"])

# --- ops ---------------------------------------------------------------------------------------------
aacc, aref, _ = login("admin@careers360.com", "admin123")
s, b, _ = call("GET", "ops/live", token=aacc)
ok("live centres", s == 200 and b["data"][0]["counsellors"], b)
s, b, _ = call("GET", f"desk/queue?as_counsellor={muser['counsellor']}", token=aacc)
ok("ops opens a counsellor's desk", s == 200, b)
s, b, _ = call("GET", "ops/insights", token=aacc)
ok("insights", s == 200 and b["data"]["rating"]["n"] >= 1, b)
s, b, h = call("GET", "ops/students/export?status=done", token=aacc, raw=True)
csv_text = b.decode()
ok("CSV export (filtered)", s == 200 and token in csv_text and "attachment" in h["Content-Disposition"], h["Content-Disposition"])
s, b, _ = call("GET", "ops/students/export", token=racc, raw=True)
ok("reception can't export", s == 403)
s, b, _ = call("GET", "ops/students", token=macc)
ok("counsellor can't see all students", s == 403)

# --- sign out ----------------------------------------------------------------------------------------
s, b, _ = call("POST", "auth/logout", {"refresh": mref})
ok("sign out", s == 200)
s, b, _ = call("POST", "auth/refresh", {"refresh": mref})
ok("the signed-out session can't be refreshed", s == 401, b)

print(f"\n{sum(1 for _, p in steps if p)}/{len(steps)} steps passed")
