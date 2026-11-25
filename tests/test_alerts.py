import numpy as np

from app import alerts, config, db
from app.violations import Event


class FakeResponse:
    ok, status_code = True, 200

    def json(self):
        return {}


def test_incident_saved_and_telegram_photo_sent(tmp_path, monkeypatch):
    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append((url, data, bool(files)))
        return FakeResponse()

    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(alerts.requests, "post", fake_post)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "TEST")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "TELEGRAM_GROUP_S", 0.1)
    db.init(tmp_path / "t.db")

    manager = alerts.AlertManager()
    incident_id = manager.handle(Event(7, ("helmet",), True, (0, 0, 10, 10)), np.zeros((48, 64, 3), np.uint8))
    import time
    for _ in range(100):
        if calls:
            break
        time.sleep(0.02)

    row = db.list_incidents()[0]
    assert row["id"] == incident_id and row["missing"] == "helmet" and row["zone"] == 1
    assert (tmp_path / row["snapshot"]).exists()
    url, data, has_photo = calls[0]
    assert url.endswith("/botTEST/sendPhoto") and data["chat_id"] == "42" and has_photo
    assert "XAVFLI ZONA" in data["caption"] and "kaskasiz" in data["caption"] and row["ts"] in data["caption"]
    assert db.report(row["ts"][:10])["total"] == 1 and db.report("2000-01-01")["total"] == 0


def test_telegram_failure_is_reported_without_leaking_token(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("https://api.telegram.org/botSECRET/sendMessage unreachable")

    monkeypatch.setattr(alerts.requests, "post", boom)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "SECRET")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    ok, err = alerts.telegram_send("x")
    assert not ok and "SECRET" not in err


def test_telegram_not_configured(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    assert alerts.telegram_send("x") == (False, "Telegram sozlanmagan")


def test_ordinary_alerts_are_grouped_and_zone_alert_is_immediate(tmp_path, monkeypatch):
    import json
    import time

    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append((url.rsplit("/", 1)[1], data, len(files or {})))
        return FakeResponse()

    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(alerts.requests, "post", fake_post)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "TEST")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "TELEGRAM_GROUP_S", 1.0)
    db.init(tmp_path / "t.db")
    manager = alerts.AlertManager()
    frame = np.zeros((48, 64, 3), np.uint8)
    for track_id, zone in ((1, False), (2, False), (3, True)):
        manager.handle(Event(track_id, ("helmet",), zone, (0, 0, 10, 10)), frame)

    time.sleep(0.3)  # inside the grouping window: only the zone alert is out
    assert [c[0] for c in calls] == ["sendPhoto"] and "XAVFLI ZONA" in calls[0][1]["caption"]
    time.sleep(1.2)
    method, data, photos = calls[1]
    assert len(calls) == 2 and method == "sendMediaGroup" and photos == 2
    assert "2 ta hodisa" in json.loads(data["media"])[0]["caption"]
    assert len(db.list_incidents()) == 3


def test_format_and_send_daily_summary(tmp_path, monkeypatch):
    calls = []

    def fake_post(url, data=None, files=None, timeout=None):
        calls.append((url, data))
        return FakeResponse()

    monkeypatch.setattr(alerts.requests, "post", fake_post)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "TEST")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    db.init(tmp_path / "summary.db")

    # When no incidents:
    empty_rep = db.report("2026-11-25")
    empty_text = alerts.format_daily_summary(empty_rep)
    assert "hech qanday qoidabuzarlik qayd etilmadi" in empty_text

    # Add incidents at different hours
    db.add_incident("2026-11-25 10:15:00", ("helmet",), 0, 1, "s1.jpg")
    db.add_incident("2026-11-25 14:05:00", ("helmet", "vest"), 1, 2, "s2.jpg")
    db.add_incident("2026-11-25 14:45:00", ("helmet",), 0, 3, "s3.jpg")

    rep = db.report("2026-11-25")
    assert rep["total"] == 3 and rep["zone"] == 1
    text = alerts.format_daily_summary(rep)
    assert "Jami qoidabuzarliklar: 3 ta" in text
    assert "Xavfli zonadagi buzilishlar: 1 ta" in text
    assert "Eng xavfli soat: 14:00–15:00 (2 ta hodisa)" in text

    ok, msg = alerts.send_daily_summary("2026-11-25")
    assert ok
    assert len(calls) == 1
    assert calls[0][0].endswith("/sendMessage")
    assert "Eng xavfli soat: 14:00–15:00" in calls[0][1]["text"]


def test_send_background_is_non_blocking(monkeypatch):
    import threading
    import time

    started = threading.Event()
    unblock = threading.Event()

    def slow_post(url, data=None, files=None, timeout=None):
        started.set()
        unblock.wait(timeout=2.0)
        return FakeResponse()

    monkeypatch.setattr(alerts.requests, "post", slow_post)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "TEST")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")

    t0 = time.monotonic()
    t = alerts.send_background("Non-blocking camera alert")
    t1 = time.monotonic()

    # Must return immediately (< 0.1s)
    assert t1 - t0 < 0.1
    assert started.wait(timeout=1.0)
    unblock.set()
    t.join(timeout=1.0)
