#!/usr/bin/env bash
# One-shot setup for CounselQueue on a fresh laptop (macOS/Linux). SQLite, no MySQL needed.
# Usage:  ./setup.sh          # install + migrate + seed
#         ./setup.sh run      # also start backend (8000) and frontend (5173)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

command -v python3 >/dev/null || { echo "python3 (3.9+) is required"; exit 1; }
command -v node >/dev/null || { echo "Node 18+ is required (see frontend/.nvmrc; try: nvm install)"; exit 1; }

echo "==> Backend"
cd "$ROOT/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$KEY|" .env && rm -f .env.bak
  echo "created backend/.env"
fi
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo

echo "==> Frontend"
cd "$ROOT/frontend"
[ -f .env ] || { cp .env.example .env; echo "created frontend/.env"; }
npm install --no-audit --no-fund

cat <<'M'

Setup done. Start the app (two terminals, or run: ./setup.sh run):
  backend : cd backend  && .venv/bin/python manage.py runserver 8000
  frontend: cd frontend && npm run dev
Student  : http://localhost:5173/c/gwalior-demo   (OTP 1234)
Console  : http://localhost:5173/console/login
  reception@careers360.com / desk123   meera@careers360.com / desk123   admin@careers360.com / admin123
M

if [ "${1:-}" = "run" ]; then
  trap 'kill 0' EXIT
  (cd "$ROOT/backend" && .venv/bin/python manage.py runserver 8000) &
  (cd "$ROOT/frontend" && npm run dev) &
  wait
fi
