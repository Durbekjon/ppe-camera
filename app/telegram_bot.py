"""The buttons under Telegram alerts: "Ko'rildi" and "Noto'g'ri signal".

The app asks Telegram for button presses (long polling), so no public address is needed. Only presses from
the configured chat are accepted. Each button carries the incident's time as well as its number, because
numbering starts again after test data is archived.
"""
import json
import logging
import threading
import time

import requests

from . import config, db

log = logging.getLogger("telegram_bot")

SEEN, FALSE, UNDO = "s", "f", "u"
POLL_S = 25
MAX_ROWS = 10


def key(ts: str) -> str:
    return "".join(c for c in ts if c.isdigit())


def keyboard(items, with_numbers=False):
    """Inline keyboard for [(incident id, ts)], reflecting each incident's current state."""
    rows = []
    for incident_id, ts in items[:MAX_ROWS]:
        row = db.query("SELECT ts, status, false_alarm FROM incidents WHERE id = ?", (incident_id,))
        if not row or row[0]["ts"] != ts:
            continue
        number = f" №{incident_id}" if with_numbers else ""
        data = f"{incident_id}:{key(ts)}"
        seen = {"ko'rildi": "👁 Ko'rilgan", "hal_qilindi": "✔️ Hal qilingan"}.get(row[0]["status"], "👁 Ko'rildi")
        mark = ({"text": f"↩️ Belgini olish{number}", "callback_data": f"{UNDO}:{data}"} if row[0]["false_alarm"]
                else {"text": f"❌ Noto'g'ri signal{number}", "callback_data": f"{FALSE}:{data}"})
        rows.append([{"text": seen + number, "callback_data": f"{SEEN}:{data}"}, mark])
    return {"inline_keyboard": rows}


def apply(data: str):
    """Carry out one button press. Return (answer text, (id, ts) or None if there is no such incident)."""
    try:
        action, raw_id, stamp = data.split(":")
        incident_id = int(raw_id)
    except ValueError:
        return "Noma'lum tugma", None
    row = db.query("SELECT ts, status FROM incidents WHERE id = ?", (incident_id,))
    if not row or key(row[0]["ts"]) != stamp:
        return "Bu hodisa topilmadi (arxivlangan bo'lishi mumkin)", None
    item = (incident_id, row[0]["ts"])
    if action == SEEN:
        if row[0]["status"] != "yangi":  # never move "resolved" back
            return "Allaqachon ko'rilgan", item
        db.set_status(incident_id, "ko'rildi")
        return f"№{incident_id}: ko'rildi", item
    if action in (FALSE, UNDO):
        db.set_false_alarm(incident_id, action == FALSE)
        return (f"№{incident_id}: noto'g'ri signal, hisobotdan chiqarildi" if action == FALSE
                else f"№{incident_id}: belgi olib tashlandi"), item
    return "Noma'lum tugma", None


def from_our_chat(message) -> bool:
    chat = (message or {}).get("chat", {})
    wanted = str(config.TELEGRAM_CHAT_ID)
    return wanted in (str(chat.get("id")), "@" + str(chat.get("username")))


class ButtonListener:
    def __init__(self):
        self._stop = threading.Event()
        self._offset = 0
        self.ok_at, self.error = None, ""  # outcome of the latest poll
        self._thread = threading.Thread(target=self._run, daemon=True, name="telegram-buttons")

    def start(self):
        self._thread.start()

    def alive(self):
        return self._thread.is_alive()

    def stop(self):
        self._stop.set()  # the thread is a daemon: a waiting request does not delay shutdown

    def _call(self, method, http_timeout=10, **params):
        """Return (result, error text). The URL holds the token, so exceptions are reduced to their name."""
        try:
            r = requests.post(f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{method}",
                              json=params, timeout=http_timeout)
            body = r.json()
            if r.ok and body.get("ok"):
                return body.get("result"), ""
            return None, f"HTTP {r.status_code}: {body.get('description', '')}"
        except Exception as e:
            return None, type(e).__name__

    def handle(self, update):
        query = update.get("callback_query")
        if not query:
            return
        message = query.get("message")
        if not from_our_chat(message):
            log.warning("Boshqa chatdan tugma bosildi; e'tiborsiz qoldirildi")
            self._call("answerCallbackQuery", callback_query_id=query["id"], text="Ruxsat yo'q")
            return
        answer, item = apply(query.get("data", ""))
        who = query.get("from", {}).get("username") or query.get("from", {}).get("id")
        log.info("Telegram tugmasi (%s): %s", who, answer)
        self._call("answerCallbackQuery", callback_query_id=query["id"], text=answer)
        if item:
            # redraw every incident that was on this message, with its new state
            items = []
            for row in message.get("reply_markup", {}).get("inline_keyboard", []):
                _, raw_id, stamp = row[0]["callback_data"].split(":")
                found = db.query("SELECT id, ts FROM incidents WHERE id = ?", (int(raw_id),))
                if found and key(found[0]["ts"]) == stamp:
                    items.append((found[0]["id"], found[0]["ts"]))
            self._call("editMessageReplyMarkup", chat_id=message["chat"]["id"], message_id=message["message_id"],
                       reply_markup=keyboard(items or [item], with_numbers=len(items) > 1))

    def poll_once(self):
        """One long-poll round. Returns an error text, or "" if all went well."""
        updates, error = self._call("getUpdates", http_timeout=POLL_S + 10, timeout=POLL_S, offset=self._offset,
                                    allowed_updates=["callback_query"])
        self.error = error
        if error:
            return error
        self.ok_at = time.time()
        for update in updates:
            self._offset = update["update_id"] + 1
            try:
                self.handle(update)
            except Exception:
                log.exception("Tugmani bajarishda xato")
        return ""

    def _run(self):
        last_error = ""
        while not self._stop.is_set():
            error = self.poll_once()
            if error:
                if error != last_error:  # say it once, not every few seconds
                    hint = " (shu bot bilan boshqa dastur yoki webhook ishlayotgan bo'lishi mumkin)" if "409" in error else ""
                    log.error("Telegram tugmalarini tinglab bo'lmadi: %s%s", error, hint)
                self._stop.wait(60 if "HTTP 4" in error else 5)
            else:
                self._stop.wait(0.2)
            last_error = error
