"""Telegram alerts waiting to be delivered.

The queue lives in SQLite, so an alert survives a lost connection or a restart. A failed delivery is retried
with growing pauses. A timeout does not tell whether Telegram got the message, so an alert can occasionally
arrive twice; that is preferred to losing it.
"""
import logging
import re
import time

from . import config, db

log = logging.getLogger("outbox")

RETRY_PAUSES_S = (10, 30, 60, 120, 300, 600, 900)  # the last one repeats
MIN_GAP_S = 1.0  # between two sends, so a backlog does not run into Telegram's rate limit
ALBUM_MAX = 10


def add(urgent, caption, photo, line, now=None):
    now = time.time() if now is None else now
    db.execute(
        "INSERT INTO outbox (urgent, caption, photo, line, created, next_try, attempts) VALUES (?, ?, ?, ?, ?, ?, 0)",
        (int(urgent), caption, photo, line, now, now),
    )


def pending():
    return db.query("SELECT COUNT(*) AS n FROM outbox")[0]["n"]


def next_batch(now):
    """The rows to send in one message now, or [].

    Order: a new urgent alert (alone), then new ordinary alerts once their grouping window has passed
    (together), then due retries (one by one, so a message Telegram rejects cannot hold others back).
    """
    urgent = db.query("SELECT * FROM outbox WHERE attempts = 0 AND urgent = 1 ORDER BY id LIMIT 1")
    if urgent:
        return urgent
    fresh = db.query("SELECT * FROM outbox WHERE attempts = 0 AND urgent = 0 ORDER BY id LIMIT ?", (ALBUM_MAX,))
    if fresh and (len(fresh) == ALBUM_MAX or now - fresh[0]["created"] >= config.TELEGRAM_GROUP_S):
        return fresh
    return db.query(
        "SELECT * FROM outbox WHERE attempts > 0 AND next_try <= ? ORDER BY urgent DESC, id LIMIT 1", (now,)
    )


def pause_after(attempts, error):
    asked = re.search(r"retry after (\d+)", error)  # Telegram's rate-limit answer
    pause = RETRY_PAUSES_S[min(attempts, len(RETRY_PAUSES_S)) - 1]
    return max(pause, int(asked.group(1))) if asked else pause


def delivered(rows):
    for row in rows:
        db.execute("DELETE FROM outbox WHERE id = ?", (row["id"],))


def failed(rows, error, now):
    for row in rows:
        attempts = row["attempts"] + 1
        db.execute("UPDATE outbox SET attempts = ?, next_try = ? WHERE id = ?",
                   (attempts, now + pause_after(attempts, error), row["id"]))


def drop_expired(now):
    """Give up on alerts older than the retry period; say so in the log."""
    limit = now - config.TELEGRAM_RETRY_HOURS * 3600
    old = db.query("SELECT line FROM outbox WHERE created < ? AND attempts > 0", (limit,))
    for row in old:
        log.error("Telegramga yuborib bo'lmadi, bekor qilindi: %s", row["line"])
    if old:
        db.execute("DELETE FROM outbox WHERE created < ? AND attempts > 0", (limit,))
    return len(old)
