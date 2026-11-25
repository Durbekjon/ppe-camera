import numpy as np
import pytest

from app import alerts, config, db, outbox
from app.violations import Event


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "TEST")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(config, "TELEGRAM_GROUP_S", 5.0)
    monkeypatch.setattr(config, "TELEGRAM_RETRY_HOURS", 24.0)
    db.init(tmp_path / "t.db")
    answers, sent = [], []

    def send(caption, photo=None, reply_markup=None):
        sent.append(caption)
        return answers.pop(0) if answers else (True, "")

    monkeypatch.setattr(alerts, "telegram_send", send)
    monkeypatch.setattr(alerts, "telegram_send_album", lambda caption, photos: send(caption))
    manager = alerts.AlertManager()
    manager.close()  # the test drives the queue itself, with its own clock
    return tmp_path, manager, answers, sent


def add(tmp, urgent, name, now=1000.0):
    (tmp / f"{name}.jpg").write_bytes(b"x")
    outbox.add(urgent, f"caption {name}", str(tmp / f"{name}.jpg"), f"line {name}", now)


def test_timeout_is_retried_until_it_succeeds(env):
    tmp, manager, answers, sent = env
    add(tmp, True, "a")
    answers += [(False, "ReadTimeout"), (False, "ConnectionError")]
    assert manager.send_next(1000) and outbox.pending() == 1
    assert not manager.send_next(1009)  # still pausing
    assert manager.send_next(1010)
    assert not manager.send_next(1039) and manager.send_next(1040)
    assert sent == ["caption a"] * 3 and outbox.pending() == 0


def test_waiting_retry_does_not_delay_a_new_zone_alert(env):
    tmp, manager, answers, sent = env
    add(tmp, False, "old")
    answers.append((False, "ReadTimeout"))
    manager.send_next(1006)
    add(tmp, True, "zone", 1100)  # the old one is due as well
    manager.send_next(1100)
    assert sent[-1] == "caption zone"


def test_new_alerts_wait_for_the_group_then_go_together(env):
    tmp, manager, _, sent = env
    add(tmp, False, "a")
    add(tmp, False, "b", 1002)
    assert not manager.send_next(1004)
    assert manager.send_next(1005) and outbox.pending() == 0
    assert "2 ta hodisa" in sent[0] and "line b" in sent[0]


def test_rejected_group_is_retried_one_by_one(env):
    tmp, manager, answers, sent = env
    add(tmp, False, "bad")
    add(tmp, False, "good")
    answers += [(False, "HTTP 400: Bad Request"), (False, "HTTP 400: Bad Request")]
    manager.send_next(1005)
    manager.send_next(1015)  # "bad" fails again on its own
    manager.send_next(1015)
    assert sent[1:] == ["caption bad", "caption good"] and outbox.pending() == 1


def test_rate_limit_pause_is_respected():
    assert outbox.pause_after(1, "HTTP 429: Too Many Requests: retry after 45") == 45
    assert outbox.pause_after(1, "ReadTimeout") == 10 and outbox.pause_after(50, "ReadTimeout") == 900


def test_gives_up_after_the_retry_period_and_logs_it(env, caplog):
    tmp, manager, answers, _ = env
    add(tmp, True, "a")
    answers.append((False, "ConnectionError"))
    manager.send_next(1000)
    assert not manager.send_next(1000 + 24 * 3600 + 1) and outbox.pending() == 0
    assert "line a" in caplog.text


def test_unsent_alert_survives_a_restart(env):
    tmp, manager, _, sent = env
    manager.handle(Event(1, ("helmet",), True, (0, 0, 1, 1)), np.zeros((48, 64, 3), np.uint8), [])
    db.init(tmp / "t.db")  # the program starts again
    again = alerts.AlertManager()
    again.close()
    again.send_next()
    assert len(sent) == 1 and outbox.pending() == 0


def test_photo_deleted_meanwhile_still_sends_the_text(env):
    tmp, manager, _, sent = env
    add(tmp, True, "a")
    (tmp / "a.jpg").unlink()
    manager.send_next(1000)
    assert sent == ["caption a\n(surat saqlanmagan)"]


def test_camera_notice_is_text_only_and_retried_while_offline(env):
    _, manager, answers, sent = env
    answers.append((False, "ConnectionError"))
    assert manager.notify("kamera uzildi\nVaqt: 10:00")
    now = outbox.time.time()
    manager.send_next(now)
    assert outbox.pending() == 1
    manager.send_next(now + 11)
    assert sent == ["kamera uzildi\nVaqt: 10:00"] * 2 and outbox.pending() == 0  # no "photo missing" note


def test_notice_is_skipped_without_telegram(env, monkeypatch):
    _, manager, _, _ = env
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    assert manager.notify("x") is False and outbox.pending() == 0
