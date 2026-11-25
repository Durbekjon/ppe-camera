"""What happens on a violation: snapshot to disk, row in SQLite, Telegram message to the supervisor."""
import json
import logging
import queue
import shutil
import threading
import time
from datetime import datetime

import cv2
import requests

from . import config, dataset, db, privacy

log = logging.getLogger("alerts")

SNAPSHOTS = config.DATA / "snapshots"
CLEANUP_EVERY_S = 3600
LABELS = {"helmet": "kaskasiz", "vest": "jiletsiz", "entry": "taqiqlangan hududda"}


def describe(missing):
    return ", ".join(LABELS[m] for m in missing)


def telegram_configured():
    return bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID)


def telegram_send(caption, photo_path=None):
    """Send a message (with optional photo). Returns (ok, error text)."""
    if not telegram_configured():
        return False, "Telegram sozlanmagan"
    base = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    try:
        if photo_path:
            with open(photo_path, "rb") as f:
                r = requests.post(
                    f"{base}/sendPhoto",
                    data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption},
                    files={"photo": f},
                    timeout=10,
                )
        else:
            r = requests.post(f"{base}/sendMessage", data={"chat_id": config.TELEGRAM_CHAT_ID, "text": caption}, timeout=10)
        if r.ok:
            return True, ""
        return False, f"HTTP {r.status_code}: {r.json().get('description', '')}"
    except Exception as e:  # never include the URL: it contains the token
        return False, type(e).__name__


def telegram_send_album(caption, photo_paths):
    """Send 2-10 photos as one album with a single caption. Returns (ok, error text)."""
    if not telegram_configured():
        return False, "Telegram sozlanmagan"
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMediaGroup"
    files = {}
    try:
        for i, path in enumerate(photo_paths):
            files[f"p{i}"] = open(path, "rb")
        media = [{"type": "photo", "media": f"attach://{name}"} for name in files]
        media[0]["caption"] = caption
        r = requests.post(
            url, data={"chat_id": config.TELEGRAM_CHAT_ID, "media": json.dumps(media)}, files=files, timeout=20
        )
        if r.ok:
            return True, ""
        return False, f"HTTP {r.status_code}: {r.json().get('description', '')}"
    except Exception as e:  # never include the URL: it contains the token
        return False, type(e).__name__
    finally:
        for f in files.values():
            f.close()


def group_caption(items):
    """One caption for several ordinary alerts; `items` are (single caption, photo path, summary line)."""
    lines = [line for _, _, line in items]
    shown = lines[:10]
    if len(lines) > len(shown):
        shown.append(f"... va yana {len(lines) - len(shown)} ta")
    return "\n".join([f"⚠️ Xavfsizlik qoidasi buzildi: {len(lines)} ta hodisa", *shown])


def expire_snapshots():
    """Delete snapshots past the retention period and unlink them from their incidents."""
    for name in privacy.delete_old_snapshots(SNAPSHOTS, config.RETENTION_DAYS):
        db.execute("UPDATE incidents SET snapshot = '' WHERE snapshot = ?", (name,))
    # Stored clean frames and exported copies follow the same retention rule.
    for name in privacy.delete_old_snapshots(dataset.RAW, config.RETENTION_DAYS):
        db.execute("UPDATE incidents SET raw = '', detections = '' WHERE raw = ?", (name,))
    if dataset.EXPORTS.is_dir():
        for folder in [p for p in dataset.EXPORTS.iterdir() if p.is_dir()]:
            if privacy.delete_old_snapshots(folder, config.RETENTION_DAYS) and not any(folder.glob("*.jpg")):
                shutil.rmtree(folder)  # the labels file goes with the last image


class AlertManager:
    def __init__(self):
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        self._queue = queue.Queue(maxsize=20)
        threading.Thread(target=self._worker, daemon=True, name="telegram").start()
        threading.Thread(target=self._cleanup_loop, daemon=True, name="cleanup").start()
        if not telegram_configured():
            log.warning("Telegram sozlanmagan (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID yo'q): xabarlar yuborilmaydi")

    def _cleanup_loop(self):
        while True:
            try:
                expire_snapshots()
            except Exception:
                log.exception("Eski suratlarni tozalashda xato")
            time.sleep(CLEANUP_EVERY_S)

    def handle(self, event, frame, regions=None, clean=None, detections=()):
        """Called from the pipeline thread with the annotated frame.

        `regions` are the areas to blur, found on the clean frame; None means search `frame` itself.
        `clean` is the frame before drawing; it is stored (blurred the same way) for retraining.
        """
        now = datetime.now()
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        # Track IDs repeat between cameras, so the camera number keeps file names apart.
        camera = f"c{event.camera_index}_" if event.camera_index else ""
        name = f"{now.strftime('%Y%m%d_%H%M%S')}_{camera}{event.track_id}.jpg"
        # The same blurred file goes to the dashboard and to Telegram.
        cv2.imwrite(str(SNAPSHOTS / name), privacy.anonymize(frame, regions))
        raw, seen = "", ""
        if clean is not None and config.SAVE_RAW:
            dataset.RAW.mkdir(parents=True, exist_ok=True)
            if cv2.imwrite(str(dataset.RAW / name), privacy.anonymize(clean, regions)):
                raw = name
                seen = json.dumps([
                    {"role": d.role, "conf": round(d.conf, 3), "box": [round(v, 1) for v in d.box]} for d in detections
                ])
        incident_id = db.add_incident(ts, event.missing, event.zone, event.track_id, name, event.zone_name, raw, seen, event.camera)
        what = describe(event.missing)
        where = f" — zona: {event.zone_name}" if event.zone else ""
        source = f" [{event.camera}]" if event.camera else ""
        log.warning("HODISA #%d%s: ishchi %s%s", incident_id, source, what, where)
        if telegram_configured():
            if "entry" in event.missing:
                head = "🚨 TAQIQLANGAN HUDUDGA KIRILDI!"
            elif event.zone:
                head = "🚨 XAVFLI ZONA! Ishchi himoyasiz"
            else:
                head = "⚠️ Xavfsizlik qoidasi buzildi"
            place = f"\nKamera: {event.camera}" if event.camera else ""
            place += f"\nZona: {event.zone_name}" if event.zone_name else ""
            caption = f"{head}\nHolat: ishchi {what}{place}\nVaqt: {ts}\nHodisa №{incident_id}"
            line = f"№{incident_id}{source} — ishchi {what}, {ts}"
            try:
                self._queue.put_nowait((event.zone, (caption, str(SNAPSHOTS / name), line)))
            except queue.Full:
                log.error("Telegram navbati to'la; xabar tashlab yuborildi")
        return incident_id

    def _worker(self):
        pending, deadline = [], None  # ordinary alerts waiting to be grouped
        while True:
            wait = None if deadline is None else max(0, deadline - time.monotonic())
            try:
                zone, item = self._queue.get(timeout=wait)
            except queue.Empty:
                pass
            else:
                if zone:  # urgent: goes out at once, on its own
                    self._deliver([item])
                else:
                    if not pending:
                        deadline = time.monotonic() + config.TELEGRAM_GROUP_S
                    pending.append(item)
            if deadline is not None and time.monotonic() >= deadline:
                self._deliver(pending)
                pending, deadline = [], None

    def _deliver(self, items):
        if len(items) == 1:
            ok, err = telegram_send(items[0][0], items[0][1])
        else:  # Telegram albums hold at most 10 photos; the caption still counts every alert
            ok, err = telegram_send_album(group_caption(items), [path for _, path, _ in items[:10]])
        if ok:
            log.info("Telegram xabari yuborildi (%d ta hodisa)", len(items))
        else:
            log.error("Telegram xabari yuborilmadi (%d ta hodisa): %s", len(items), err)
