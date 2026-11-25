"""PPE-602: External system health check script.

Can be run via cron, Docker HEALTHCHECK, or external monitoring agents (e.g. Uptime Kuma)
to verify that the server is alive and the camera source is connected.

Exit codes:
0: Healthy (server responds and camera is connected)
1: Unhealthy (server down or camera offline)
"""
import sys
import urllib3
import requests

# Suppress self-signed certificate warnings for local healthcheck
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "https://127.0.0.1:8000/api/health"

try:
    try:
        r = requests.get(URL, timeout=5, verify=False)
    except Exception:
        # Fallback to HTTP if TLS is not active
        if URL.startswith("https://"):
            r = requests.get(URL.replace("https://", "http://"), timeout=5)
        else:
            raise
    if not r.ok:
        print(f"CRITICAL: HTTP {r.status_code}")
        sys.exit(1)
    data = r.json()
    if not data.get("camera", False):
        print(f"WARNING: Kamera uzilgan (camera=false, status={data.get('status')})")
        sys.exit(1)
    print(f"OK: Server faol, kamera ulangan (FPS: {data.get('fps')})")
    sys.exit(0)
except Exception as e:
    print(f"CRITICAL: Tizimga ulanib bo'lmadi - {e}")
    sys.exit(1)
