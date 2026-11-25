#!/bin/sh
# Self-signed certificate for HTTPS on the local network.
# Usage: tools/make_cert.sh 192.168.1.20     (this computer's address on the network)
set -e
[ -n "$1" ] || { echo "Foydalanish: tools/make_cert.sh <kompyuterning IP manzili>"; exit 1; }
cd "$(dirname "$0")/.."
mkdir -p data/certs
if [ -e data/certs/key.pem ]; then
  echo "data/certs/key.pem allaqachon bor. Yangisini yaratish uchun avval data/certs papkasini o'chiring."
  exit 1
fi
umask 077
openssl req -x509 -newkey rsa:2048 -sha256 -days 365 -nodes \
  -keyout data/certs/key.pem -out data/certs/cert.pem \
  -subj "/CN=$1" -addext "subjectAltName=IP:$1,IP:127.0.0.1,DNS:localhost" 2>/dev/null
echo "Tayyor. .env fayliga qo'shing:"
echo "HOST=0.0.0.0"
echo "TLS_CERT=data/certs/cert.pem"
echo "TLS_KEY=data/certs/key.pem"
