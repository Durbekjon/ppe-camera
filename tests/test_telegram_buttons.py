import json

import numpy as np
import pytest

from app import alerts, config, db, outbox, telegram_bot
from app.violations import Event

CHAT = "42"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "SECRET-TOKEN")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", CHAT)
    monkeypatch.setattr(config, "TELEGRAM_BUTTONS", True)
    monkeypatch.setattr(config, "TELEGRAM_GROUP_S", 0.0)
    db.init(tmp_path / "t.db")
    posts = []

    class Ok:
        ok, status_code = True, 200

        def __init__(self, result=True):
            self.result = result

        def json(self):
            return {"ok": True, "result": self.result}

    def post(url, data=None, files=None, json=None, timeout=None):
        posts.append((url.rsplit("/", 1)[1], data or json))
        return Ok([] if url.endswith("getUpdates") else True)

    monkeypatch.setattr(alerts.requests, "post", post)
    manager = alerts.AlertManager()
    manager.close()  # the test drives the queue itself
    return manager, posts


def incident(manager, track=1, zone=False):
    return manager.handle(Event(track, ("helmet",), zone, (0, 0, 1, 1)), np.zeros((48, 64, 3), np.uint8), [])


def buttons_of(data):
    markup = data["reply_markup"]
    return (json.loads(markup) if isinstance(markup, str) else markup)["inline_keyboard"]


def press(listener, data, chat=CHAT, markup=None):
    listener.handle({"update_id": 1, "callback_query": {"id": "q", "data": data, "from": {"username": "boss"},
                    "message": {"message_id": 5, "chat": {"id": int(chat)},
                                "reply_markup": {"inline_keyboard": markup or [[{"callback_data": data}]]}}}})


def row(incident_id):
    return db.query("SELECT status, false_alarm FROM incidents WHERE id = ?", (incident_id,))[0]


def test_single_alert_has_two_buttons(env):
    manager, posts = env
    first = incident(manager, zone=True)
    manager.send_next()
    method, data = posts[-1]
    texts = [b["text"] for b in buttons_of(data)[0]]
    assert method == "sendPhoto" and texts == ["👁 Ko'rildi", "❌ Noto'g'ri signal"]
    assert all(len(b["callback_data"].encode()) <= 64 for b in buttons_of(data)[0])
    assert buttons_of(data)[0][0]["callback_data"].startswith(f"s:{first}:")


def test_album_is_followed_by_one_message_with_a_row_per_incident(env):
    manager, posts = env
    ids = [incident(manager, 1), incident(manager, 2)]
    manager.send_next(outbox.time.time() + 1)
    assert posts[-1][0] == "sendMediaGroup" and "reply_markup" not in posts[-1][1]
    assert outbox.pending() == 1
    manager.send_next(outbox.time.time() + 1)
    method, data = posts[-1]
    assert method == "sendMessage" and len(buttons_of(data)) == 2 and outbox.pending() == 0
    assert [r[0]["text"].split()[-1] for r in buttons_of(data)] == [f"№{i}" for i in ids]


def test_buttons_can_be_switched_off(env, monkeypatch):
    manager, posts = env
    monkeypatch.setattr(config, "TELEGRAM_BUTTONS", False)
    incident(manager, zone=True)
    manager.send_next()
    assert "reply_markup" not in posts[-1][1]


def test_pressing_buttons_changes_the_incident_and_redraws_them(env):
    manager, posts = env
    first = incident(manager, zone=True)
    manager.send_next()
    seen, false = (b["callback_data"] for b in buttons_of(posts[-1][1])[0])
    listener, before = telegram_bot.ButtonListener(), db.review_count
    press(listener, seen)
    assert row(first)["status"] == "ko'rildi" and db.review_count > before
    press(listener, false)
    assert row(first)["false_alarm"] == 1
    method, data = posts[-1]
    assert method == "editMessageReplyMarkup" and "Belgini olish" in buttons_of(data)[0][1]["text"]
    press(listener, buttons_of(data)[0][1]["callback_data"])
    assert row(first)["false_alarm"] == 0


def test_resolved_incident_is_not_moved_back(env):
    manager, _ = env
    first = incident(manager)
    ts = db.list_incidents()[0]["ts"]
    db.set_status(first, "hal_qilindi")
    telegram_bot.apply(f"s:{first}:{telegram_bot.key(ts)}")
    assert row(first)["status"] == "hal_qilindi"


def test_press_from_another_chat_is_ignored(env):
    manager, posts = env
    first = incident(manager)
    ts = db.list_incidents()[0]["ts"]
    press(telegram_bot.ButtonListener(), f"f:{first}:{telegram_bot.key(ts)}", chat="999")
    assert row(first)["false_alarm"] == 0 and posts[-1][1]["text"] == "Ruxsat yo'q"


def test_old_button_cannot_change_a_new_incident_with_the_same_number(env):
    manager, _ = env
    first = incident(manager)
    answer, item = telegram_bot.apply(f"f:{first}:20200101000000")  # same number, from before an archive
    assert item is None and "topilmadi" in answer and row(first)["false_alarm"] == 0
    for junk in ("", "x", "f:abc:1", "z:1:1"):
        assert telegram_bot.apply(junk)[1] is None


def test_polling_moves_forward_and_errors_never_show_the_token(env, monkeypatch):
    manager, posts = env
    listener = telegram_bot.ButtonListener()
    updates = [{"update_id": 7}]

    class Reply:
        ok, status_code = True, 200

        def json(self):
            return {"ok": True, "result": updates}

    sent = []
    monkeypatch.setattr(telegram_bot.requests, "post", lambda url, json=None, timeout=None: sent.append(json) or Reply())
    assert listener.poll_once() == ""
    listener.poll_once()
    assert sent[0]["offset"] == 0 and sent[1]["offset"] == 8 and sent[0]["timeout"] == telegram_bot.POLL_S

    def boom(url, json=None, timeout=None):
        raise ConnectionError(url)

    monkeypatch.setattr(telegram_bot.requests, "post", boom)
    assert listener.poll_once() == "ConnectionError"


def test_old_outbox_table_is_migrated(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, urgent INTEGER NOT NULL, caption TEXT NOT NULL,"
                " photo TEXT NOT NULL, line TEXT NOT NULL, created REAL NOT NULL, next_try REAL NOT NULL, attempts INTEGER NOT NULL)")
    con.execute("INSERT INTO outbox (urgent, caption, photo, line, created, next_try, attempts) VALUES (1,'c','','l',0,0,0)")
    con.commit()
    con.close()
    db.init(path)
    db.init(path)
    assert db.query("SELECT caption, incidents FROM outbox")[0]["incidents"] == ""
