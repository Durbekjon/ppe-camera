#!/bin/sh
# One-command start: creates the virtualenv on first run, then launches the dashboard.
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then
  echo "Birinchi ishga tushirish: kutubxonalar o'rnatilmoqda (bir necha daqiqa)..."
  [ ! -x .venv/bin/python ] && (python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv)
  .venv/bin/pip install -q -r requirements.txt
fi
# .env holds secrets: readable by its owner only.
[ -f .env ] && chmod 600 .env
# Environment variables win over .env.
setting() { [ -f .env ] && grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- || true; }
PORT=${PORT:-$(setting PORT)}
HOST=${HOST:-$(setting HOST)}
TLS_CERT=${TLS_CERT:-$(setting TLS_CERT)}
TLS_KEY=${TLS_KEY:-$(setting TLS_KEY)}
PORT=${PORT:-8000}
HOST=${HOST:-127.0.0.1}

# The video stream never ends by itself: without a limit, stopping the app would wait for open dashboards forever.
set -- app.main:app --host "$HOST" --port "$PORT" --no-access-log --timeout-graceful-shutdown 3
if [ -n "$TLS_CERT" ] || [ -n "$TLS_KEY" ]; then
  if [ ! -f "$TLS_CERT" ] || [ ! -f "$TLS_KEY" ]; then
    echo "TLS_CERT va TLS_KEY ikkalasi ham mavjud faylni ko'rsatishi kerak (tools/make_cert.sh)." >&2
    exit 1
  fi
  set -- "$@" --ssl-certfile "$TLS_CERT" --ssl-keyfile "$TLS_KEY"
elif [ "$HOST" != "127.0.0.1" ] && [ "$HOST" != "localhost" ] && [ "$HOST" != "::1" ]; then
  echo "Tarmoqqa ochish (HOST=$HOST) uchun HTTPS shart: tools/make_cert.sh <IP>" >&2
  exit 1
fi
exec .venv/bin/uvicorn "$@"
