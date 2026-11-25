"""Measure FPS per camera on this computer with 1..N copies of the demo video running at once.

Usage: .venv/bin/python -m tools.measure_fps [max_cameras] [seconds]
Nothing real is touched: temporary database and folders, Telegram off.
The demo video plays at its own frame rate, so no camera can score above that.
"""
import platform
import sys
import tempfile
import time
from pathlib import Path

from app import alerts, config, dataset, db, hub

most = int(sys.argv[1]) if len(sys.argv) > 1 else 2
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 30
tmp = Path(tempfile.mkdtemp())
config.TELEGRAM_BOT_TOKEN = config.TELEGRAM_CHAT_ID = ""
alerts.SNAPSHOTS, dataset.RAW, dataset.EXPORTS = tmp / "snapshots", tmp / "raw", tmp / "exports"
hub.ZONE_FILE, hub.LEGACY_ZONE_FILE = tmp / "zones.json", tmp / "zone.json"
db.init(tmp / "t.db")
print(f"{platform.machine()} {platform.system()}, imgsz={config.IMG_SIZE}, {seconds:.0f} s har bir sinov")
for count in range(1, most + 1):
    h = hub.Hub([(f"K{i}", config.DEMO_VIDEO) for i in range(1, count + 1)])
    for p in h.cameras.values():
        p.demo = False
    h.start()
    time.sleep(8)  # warm up
    first = {n: p.jpeg_seq for n, p in h.cameras.items()}
    start = time.monotonic()
    time.sleep(seconds)
    elapsed = time.monotonic() - start
    fps = [(p.jpeg_seq - first[n]) / elapsed for n, p in h.cameras.items()]
    h.stop()
    print(f"{count} kamera: " + ", ".join(f"{f:.1f}" for f in fps) + f" FPS (jami {sum(fps):.1f})", flush=True)
