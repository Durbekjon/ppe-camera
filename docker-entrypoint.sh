#!/bin/sh
set -e

# Generate local self-signed TLS certificate if missing (PPE-503 compliance)
if [ ! -f data/certs/cert.pem ] || [ ! -f data/certs/key.pem ]; then
  mkdir -p data/certs
  umask 077
  openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
    -keyout data/certs/key.pem -out data/certs/cert.pem \
    -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost" 2>/dev/null || true
fi

SSL_ARGS=""
if [ -f data/certs/cert.pem ] && [ -f data/certs/key.pem ]; then
  SSL_ARGS="--ssl-certfile data/certs/cert.pem --ssl-keyfile data/certs/key.pem"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" $SSL_ARGS --no-access-log
