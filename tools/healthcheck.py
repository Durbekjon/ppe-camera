"""PPE-602: External system health check script.

Can be run via cron, Docker HEALTHCHECK, or external monitoring agents (e.g. Uptime Kuma)
to verify that the server is alive and the camera source is connected.

Exit codes:
0: Healthy (server responds and camera is connected)
1: Unhealthy (server down or camera offline)
"""
import sys
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/status"

try:
    r = requests.get(URL, timeout=5)
    if not r.ok:
        print(f"CRITICAL: HTTP {r.status_code}")
        sys.exit(1)
    data = r.json()
    if not data.get("camera", False):
        print(f"WARNING: Kamera uzilgan (camera=false, status={data.get('status')})")
        sys.exit(1)
    print(f"OK: Server faol, kamera ulangan (FPS: {data.get('fps')}, odamlar: {data.get('people')})")
    sys.exit(0)
except Exception as e:
    print(f"CRITICAL: Tizimga ulanib bo'lmadi - {e}")
    sys.exit(1)
