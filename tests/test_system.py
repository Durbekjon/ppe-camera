import json

import pytest
from fastapi.testclient import TestClient

from app import alerts, auth, config, db, main, outbox, system

TOKEN = "123456789:" + "S" * 35
CHAT = "987654321"


class FakeHub:
    def __init__(self, manager):
        self.alerts, self.buttons = manager, None


class Listener:
    def __init__(self, alive=True, ok_at=None, error=""):
        self._alive, self.ok_at, self.error = alive, ok_at, error

    def alive(self):
        return self._alive


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", TOKEN)
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", CHAT)
    monkeypatch.setattr(config, "TELEGRAM_BUTTONS", True)
    db.init(tmp_path / "t.db")
    manager = alerts.AlertManager()
    manager.close()
    answers = []
    monkeypatch.setattr(alerts, "telegram_send", lambda *a, **k: answers.pop(0))
    return manager, answers


def test_nothing_sent_yet_is_not_reported_as_working(env):
    manager, _ = env
    assert system.telegram_state(manager.health, 0)["level"] == "idle"


def test_failure_then_recovery(env):
    manager, answers = env
    outbox.add(True, "c", "", "l", 1000)
    answers += [(False, "ReadTimeout"), (True, "")]
    manager.send_next(1000)
    state = system.telegram_state(manager.health, manager.health.error_at + 7)
    assert state["level"] == "bad" and state["waiting"] == 1 and state["last_error"] == "ReadTimeout"
    assert state["last_error_s"] == 7 and state["last_ok_s"] is None
    manager.send_next(1011)
    state = system.telegram_state(manager.health, manager.health.ok_at)
    assert state["level"] == "ok" and state["waiting"] == 0 and state["last_error"] == ""


def test_old_retry_after_a_later_success_is_a_warning(env):
    manager, answers = env
    outbox.add(True, "a", "", "a", 1000)
    answers += [(False, "ReadTimeout"), (True, "")]
    manager.send_next(1000)
    outbox.add(True, "b", "", "b", 1001)
    manager.send_next(1001)
    assert system.telegram_state(manager.health, manager.health.ok_at)["level"] == "warn"


def test_buttons_states(env, monkeypatch):
    assert system.buttons_state(None)["level"] == "bad"
    assert system.buttons_state(Listener(alive=False, ok_at=1))["level"] == "bad"
    assert system.buttons_state(Listener())["level"] == "idle"
    assert system.buttons_state(Listener(ok_at=1))["level"] == "ok"
    assert "409" in system.buttons_state(Listener(ok_at=1, error="HTTP 409: Conflict"))["text"]
    monkeypatch.setattr(config, "TELEGRAM_BUTTONS", False)
    assert system.buttons_state(None)["level"] == "off"


def test_endpoint_needs_login_and_shows_no_secrets(env, monkeypatch):
    manager, _ = env
    manager.health.error_at, manager.health.error = 1.0, f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    hub = FakeHub(manager)
    hub.buttons = Listener(error=f"https://api.telegram.org/bot{TOKEN}/getUpdates")
    monkeypatch.setattr(main, "hub", hub)
    client = TestClient(main.app, client=("127.0.0.1", 5000))
    assert client.get("/api/system").status_code == 401
    auth.set_user("watcher", "password-123", auth.SUPERVISOR)
    client.post("/api/login", json={"username": "watcher", "password": "password-123"})
    r = client.get("/api/system")
    assert r.status_code == 200 and r.json()["retention_days"] == config.RETENTION_DAYS
    text = json.dumps(r.json())
    assert TOKEN not in text and CHAT not in text


@pytest.mark.parametrize("launcher", ["run.sh", "docker-entrypoint.sh", "deploy/ppe-camera.service"])
def test_every_launcher_limits_the_shutdown_wait(launcher):
    # an open video stream would otherwise keep the server from stopping
    assert "--timeout-graceful-shutdown 3" in (config.ROOT / launcher).read_text()


def test_run_sh_keeps_the_mac_awake_only_while_the_app_runs():
    text = (config.ROOT / "run.sh").read_text()
    # -w $$ ties caffeinate to this process, which `exec` turns into the server
    assert "caffeinate -dimsu -w $$ &" in text and text.index("caffeinate") < text.index("exec .venv/bin/uvicorn")
