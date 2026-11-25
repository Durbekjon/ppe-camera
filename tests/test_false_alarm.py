import json
from datetime import datetime

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import alerts, auth, config, dataset, db, main
from app.detector import PERSON, Detection
from app.violations import Event


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(dataset, "RAW", tmp_path / "raw")
    monkeypatch.setattr(dataset, "EXPORTS", tmp_path / "exports")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "RETENTION_DAYS", 30)
    db.init(tmp_path / "t.db")
    auth._failures.clear()
    auth.set_user("watcher", "password-123", auth.SUPERVISOR)
    client = TestClient(main.app, client=("127.0.0.1", 5000))
    client.post("/api/login", json={"username": "watcher", "password": "password-123"})
    return tmp_path, client, alerts.AlertManager()


def incident(manager, track_id=1):
    clean = np.full((200, 300, 3), 120, np.uint8)
    drawn = clean.copy()
    cv2.rectangle(drawn, (20, 20), (200, 180), (0, 0, 255), 3)
    return manager.handle(Event(track_id, ("helmet",), True, (20, 20, 200, 180)), drawn, [], clean,
                          [Detection(PERSON, 0.9, (20, 20, 200, 180))])


def mark(client, incident_id, value=True):
    return client.post(f"/api/incidents/{incident_id}/false-alarm", json={"value": value})


def test_supervisor_marks_and_unmarks_and_report_follows(env):
    _, client, manager = env
    first = incident(manager)
    incident(manager, 2)
    today = datetime.now().strftime("%Y-%m-%d")
    assert mark(client, first).status_code == 200
    assert db.report(today)["total"] == 1 and db.report(today)["zone"] == 1
    rows = client.get("/api/incidents").json()
    assert [r["false_alarm"] for r in rows] == [0, 1] and "detections" not in rows[0]
    mark(client, first, False)
    assert db.report(today)["total"] == 2


def test_marking_needs_login_and_an_existing_incident(env):
    _, client, manager = env
    assert mark(client, 999).status_code == 404
    client.cookies.clear()
    assert mark(client, incident(manager)).status_code == 401


def test_export_has_the_clean_frame_not_the_drawn_one(env):
    _, client, manager = env
    first = incident(manager)
    incident(manager, 2)  # not marked: must not be exported
    mark(client, first)
    folder, exported, skipped = dataset.export_false_alarms()
    labels = json.loads((folder / "labels.json").read_text())
    assert (exported, skipped) == (1, 0) and [x["incident"] for x in labels] == [first]
    image = cv2.imread(str(folder / labels[0]["image"]))
    assert abs(int(image[20, 100, 2]) - 120) < 10  # no red box
    assert labels[0]["detections"][0]["role"] == PERSON


def test_incident_without_a_stored_frame_is_skipped(env):
    _, client, _ = env
    old = db.add_incident("2026-11-25 10:00:00", ("helmet",), 0, 1, "x.jpg")
    mark(client, old)
    assert dataset.export_false_alarms() == (None, 0, 1)


def test_save_raw_can_be_switched_off(env, monkeypatch):
    tmp, _, manager = env
    monkeypatch.setattr(config, "SAVE_RAW", False)
    incident(manager)
    assert not list(tmp.glob("raw/*.jpg"))


def test_raw_frames_and_exports_expire(env):
    tmp, _, _ = env
    name = "20200101_120000_1.jpg"
    for folder in (tmp / "raw", tmp / "exports" / "20200102_000000"):
        folder.mkdir(parents=True)
        (folder / name).write_bytes(b"x")
    (tmp / "exports" / "20200102_000000" / "labels.json").write_text("[]")
    db.add_incident("2020-01-01 12:00:00", ("helmet",), 0, 1, "", raw=name, detections="[]")
    alerts.expire_snapshots()
    assert not (tmp / "raw" / name).exists() and not (tmp / "exports" / "20200102_000000").exists()
    assert db.query("SELECT raw FROM incidents")[0]["raw"] == ""
