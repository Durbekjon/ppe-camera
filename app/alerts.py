"""What happens on a violation: snapshot to disk, row in SQLite, Telegram message to the supervisor."""
import json
import logging
import shutil
import threading
import time
import weakref
from pathlib import Path
from datetime import datetime

import cv2
import requests

from . import config, dataset, db, outbox, privacy

log = logging.getLogger("alerts")

SNAPSHOTS = config.DATA / "snapshots"
CLEANUP_EVERY_S = 3600
_managers = weakref.WeakSet()  # so tests can stop every sender thread
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


def group_caption(lines):
    """One caption for several ordinary alerts, from their summary lines."""
    shown = lines[:10]
    if len(lines) > len(shown):
        shown.append(f"... va yana {len(lines) - len(shown)} ta")
    return "\n".join([f"⚠️ Xavfsizlik qoidasi buzildi: {len(lines)} ta hodisa", *shown])


def deliver(rows):
    """Send one message for these outbox rows. Returns (ok, error text)."""
    photos = [row["photo"] for row in rows if Path(row["photo"]).is_file()]
    if len(rows) == 1:
        if photos:
            return telegram_send(rows[0]["caption"], photos[0])
        return telegram_send(rows[0]["caption"] + "\n(surat saqlanmagan)")  # expired while waiting
    caption = group_caption([row["line"] for row in rows])
    if len(photos) > 1:
        return telegram_send_album(caption, photos)
    return telegram_send(caption, photos[0] if photos else None)


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
        self._wake, self._closed = threading.Event(), threading.Event()
        self._sender = threading.Thread(target=self._worker, daemon=True, name="telegram")
        self._sender.start()
        _managers.add(self)
        threading.Thread(target=self._cleanup_loop, daemon=True, name="cleanup").start()
        if not telegram_configured():
            log.warning("Telegram sozlanmagan (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID yo'q): xabarlar yuborilmaydi")

    def _cleanup_loop(self):
        while not self._closed.is_set():
            try:
                expire_snapshots()
            except Exception:
                log.exception("Eski suratlarni tozalashda xato")
            self._closed.wait(CLEANUP_EVERY_S)

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
            outbox.add(event.zone, caption, str(SNAPSHOTS / name), line)
            self._wake.set()
        return incident_id

    def close(self):
        """Stop the threads; unsent alerts stay in the database for the next start."""
        self._closed.set()
        self._wake.set()
        self._sender.join(timeout=2)

    def send_next(self, now=None):
        """Send at most one waiting message. Returns True if one was attempted."""
        now = time.time() if now is None else now
        outbox.drop_expired(now)
        rows = outbox.next_batch(now)
        if not rows:
            return False
        ok, err = deliver(rows)
        if ok:
            outbox.delivered(rows)
            log.info("Telegram xabari yuborildi (%d ta hodisa)", len(rows))
        else:
            outbox.failed(rows, err, now)
            log.error("Telegram xabari yuborilmadi (%d ta hodisa): %s. Qayta urinib ko'riladi, navbatda: %d",
                      len(rows), err, outbox.pending())
        return True

    def _worker(self):
        while not self._closed.is_set():
            sent = False
            try:
                if telegram_configured():
                    sent = self.send_next()
            except Exception:
                log.exception("Telegram navbatida xato")
            if sent:
                self._closed.wait(outbox.MIN_GAP_S)
            else:
                self._wake.wait(0.2)
                self._wake.clear()
