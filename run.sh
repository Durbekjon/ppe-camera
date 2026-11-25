#!/bin/sh
# One-command start: creates the virtualenv on first run, then launches the dashboard.
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then
  echo "Birinchi ishga tushirish: kutubxonalar o'rnatilmoqda (bir necha daqiqa)..."
  [ ! -x .venv/bin/python ] && (python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv)
  .venv/bin/pip install -q -r requirements.txt
fi
[ -z "$PORT" ] && [ -f .env ] && PORT=$(grep -E '^PORT=' .env | cut -d= -f2)
PORT=${PORT:-8000}
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --no-access-log
