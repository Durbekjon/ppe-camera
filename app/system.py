"""What the dashboard's "Tizim holati" card shows. No secrets: no tokens, chat ids or camera addresses."""
import time

from . import alerts, config, db, outbox
from .redact import redact


def _ago(moment, now):
    return None if moment is None else max(0, int(now - moment))


def telegram_state(health, now):
    if not alerts.telegram_configured():
        return {"level": "off", "text": "sozlanmagan"}
    waiting = outbox.pending()
    retrying = db.query("SELECT COUNT(*) AS n FROM outbox WHERE attempts > 0")[0]["n"]
    ok_at, error_at = health.ok_at, health.error_at
    if error_at is not None and (ok_at is None or error_at > ok_at):
        level, text = "bad", "oxirgi yuborish muvaffaqiyatsiz"
    elif retrying:
        level, text = "warn", "ayrim xabarlar qayta yuborilmoqda"
    elif ok_at is not None:
        level, text = "ok", "ishlayapti"
    else:  # configured, but nothing has been sent since the start: do not claim it works
        level, text = "idle", "ishga tushgandan beri xabar yuborilmagan"
    return {"level": level, "text": text, "waiting": waiting, "retrying": retrying,
            "last_ok_s": _ago(ok_at, now), "last_error_s": _ago(error_at, now),
            "last_error": redact(health.error) if level in ("bad", "warn") else ""}


def buttons_state(listener):
    if not (config.TELEGRAM_BUTTONS and alerts.telegram_configured()):
        return {"level": "off", "text": "o'chirilgan"}
    if listener is None or not listener.alive():
        return {"level": "bad", "text": "tinglanmayapti"}
    if listener.error:
        return {"level": "bad", "text": f"xato: {redact(listener.error)}"}
    if listener.ok_at is None:
        return {"level": "idle", "text": "tekshirilmoqda (30 soniyagacha)"}
    return {"level": "ok", "text": "tinglanmoqda"}


def status(hub, now=None):
    now = time.time() if now is None else now
    return {
        "telegram": telegram_state(hub.alerts.health, now),
        "buttons": buttons_state(hub.buttons),
        "skeleton": config.SKELETON,
        "blur_faces": config.BLUR_FACES,
        "retention_days": config.RETENTION_DAYS,
        "local_audio": config.LOCAL_AUDIO,
    }
