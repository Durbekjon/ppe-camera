import pytest
from fastapi.testclient import TestClient

from app import auth, db, main

PASSWORD = "correct-horse-1"


@pytest.fixture
def client(tmp_path):
    db.init(tmp_path / "t.db")
    auth._failures.clear()
    auth.set_user("boss", PASSWORD, auth.ADMIN)
    auth.set_user("watcher", PASSWORD, auth.SUPERVISOR)
    return TestClient(main.app, client=("127.0.0.1", 5000))  # no lifespan: the camera pipeline is not started


def sign_in(client, name, password=PASSWORD):
    return client.post("/api/login", json={"username": name, "password": password})


def test_video_api_and_snapshots_need_login(client):
    for path in ("/video", "/api/status", "/api/incidents", "/api/report", "/api/zone", "/api/me",
                 "/snapshots/x.jpg", "/static/app.js", "/static/index.html", "/docs", "/openapi.json"):
        assert client.get(path).status_code == 401, path
    for path in ("/api/zone", "/api/demo", "/api/telegram-test"):
        assert client.post(path, json={}).status_code == 401, path
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/login").status_code == 200


def test_wrong_password_and_unknown_user_are_rejected(client):
    assert sign_in(client, "boss", "wrong-password").status_code == 401
    assert sign_in(client, "nobody").status_code == 401
    assert client.get("/api/me").status_code == 401


def test_cookie_is_protected_and_logout_ends_the_session(client):
    r = sign_in(client, "Boss")
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    token = client.cookies["session"]
    assert client.get("/api/me").json() == {"username": "boss", "role": "admin"}
    assert client.post("/api/logout").status_code == 200
    assert auth.user_for(token) is None  # revoked on the server, not just in the browser


def test_supervisor_can_watch_but_not_change(client):
    sign_in(client, "watcher")
    assert client.get("/api/incidents").status_code == 200
    for path in ("/api/zone", "/api/demo", "/api/telegram-test"):
        assert client.post(path, json={}).status_code == 403, path
    assert client.post("/api/logout").status_code == 200


def test_admin_may_use_admin_actions(client, monkeypatch):
    monkeypatch.setattr(main.alerts, "telegram_send", lambda *a: (True, ""))
    sign_in(client, "boss")
    assert client.post("/api/telegram-test").json() == {"ok": True, "error": ""}


def test_repeated_failures_lock_the_login(client):
    for _ in range(auth.MAX_FAILURES):
        sign_in(client, "boss", "wrong-password")
    assert sign_in(client, "boss").status_code == 429


def test_password_reset_expiry_and_storage(client, monkeypatch):
    token = auth.login("boss", PASSWORD)
    auth.set_user("boss", "another-password", auth.ADMIN)
    assert auth.user_for(token) is None and auth.login("boss", PASSWORD) is None
    token = auth.login("boss", "another-password")
    stored = [r["token"] for r in db.query("SELECT token FROM sessions")]
    assert token not in stored
    later = auth.time.time() + auth.SESSION_S + 1
    monkeypatch.setattr(auth.time, "time", lambda: later)
    assert auth.user_for(token) is None


def test_short_password_is_refused(client):
    with pytest.raises(ValueError):
        auth.set_user("x", "short", auth.ADMIN)
