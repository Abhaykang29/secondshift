#!/bin/sh
# Local HTTPS for the phone camera page (iPhone Safari requires HTTPS
# for getUserMedia on LAN addresses). Generates a self-signed cert into
# .local/certs (gitignored) and serves the backend with TLS on :8000.
# On the iPhone: open https://<this-machine-LAN-IP>:8000, accept the
# warning once (or install the cert via Settings > General > About >
# Certificate Trust Settings for a permanent fix).
set -e
mkdir -p .local/certs
if [ ! -f .local/certs/cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout .local/certs/key.pem -out .local/certs/cert.pem -days 365 \
    -subj "/CN=secondshift.local" \
    -addext "subjectAltName=DNS:secondshift.local,DNS:localhost,IP:127.0.0.1"
  echo "Wrote .local/certs/cert.pem (self-signed, local only)"
fi
exec .venv/bin/python -m uvicorn secondshift.main:app --app-dir backend \
  --host 0.0.0.0 --port 8000 \
  --ssl-certfile .local/certs/cert.pem --ssl-keyfile .local/certs/key.pem
