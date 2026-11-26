import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import alerts, auth, config, db, hub, main
from app.cameras import parse_cameras
from app.detector import PERSON, Detection

ZONE = {"name": "A", "points": [[0, 0], [1, 0], [1, 1], [0, 1]], "rule": "no_entry"}


class FakeDetector:
    def __init__(self, *args):
        pass

    def detect(self, frame):
        return [Detection(PERSON, 0.9, (100.0, 50.0, 300.0, 350.0))]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(hub, "Detector", FakeDetector)
    monkeypatch.setattr(config, "SKELETON", False)  # the fake people have no skeletons; see test_pose.py
    monkeypatch.setattr(hub, "ZONE_FILE", tmp_path / "zones.json")
    monkeypatch.setattr(hub, "LEGACY_ZONE_FILE", tmp_path / "zone.json")
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    (tmp_path / "snapshots").mkdir()
    db.init(tmp_path / "t.db")
    auth._failures.clear()
    auth.set_user("boss", "password-123", auth.ADMIN)
    cameras = hub.Hub([("Kirish", "a.mp4"), ("Sex", "b.mp4")])  # not started: no video threads
    monkeypatch.setattr(main, "hub", cameras)
    client = TestClient(main.app, client=("127.0.0.1", 5000))
    client.post("/api/login", json={"username": "boss", "password": "password-123"})
    return tmp_path, cameras, client


def feed(pipeline, seconds=3.0):
    for i in range(int(seconds * 10)):
        pipeline.process(np.zeros((400, 600, 3), np.uint8), i / 10)


def test_parse_cameras():
    assert parse_cameras("", "0") == [("Kamera 1", "0")]
    assert parse_cameras("Kirish=0; Sex=http://h/v?a=1 ;", "9") == [("Kirish", "0"), ("Sex", "http://h/v?a=1")]


@pytest.mark.parametrize("spec", ["0", "A=", "=0", "A=0;a=1", "A=0;B=1;C=2;D=3;E=4", "rtsp://u:SECRET@h/s?x=1"])
def test_bad_camera_settings_do_not_echo_secrets(spec):
    with pytest.raises(ValueError) as error:
        parse_cameras(spec, "0")
    assert "SECRET" not in str(error.value)


def test_zones_belong_to_one_camera_and_survive_a_restart(setup):
    _, cameras, client = setup
    assert client.post("/api/zones?camera=Sex", json={"zones": [ZONE]}).status_code == 200
    assert client.get("/api/zones?camera=Kirish").json() == {"zones": []}
    assert [z["name"] for z in client.get("/api/zones?camera=Sex").json()["zones"]] == ["A"]
    again = hub.Hub([("Kirish", "a.mp4"), ("Sex", "b.mp4")])
    assert [z.name for z in again.get("Sex").engine.zones] == ["A"] and again.get("Kirish").engine.zones == []


def test_zones_of_a_removed_camera_are_not_lost(setup):
    _, cameras, _ = setup
    cameras.set_zones("Sex", [ZONE])
    fewer = hub.Hub([("Kirish", "a.mp4")])
    fewer.set_zones("Kirish", [ZONE])
    assert hub.Hub([("Sex", "b.mp4")]).get("Sex").engine.zones[0].name == "A"


def test_demo_mode_zones_do_not_guard_the_real_camera(setup, monkeypatch):
    _, cameras, client = setup
    sex = cameras.get("Sex")
    monkeypatch.setattr(type(sex), "set_demo", lambda self, on: setattr(self, "demo", on))  # no video threads
    assert client.post("/api/demo?camera=Sex", json={"on": True}).json() == {"demo": True}
    assert client.post("/api/zones?camera=Sex", json={"zones": [ZONE]}).status_code == 200
    assert [z.name for z in sex.engine.zones] == ["A"]
    client.post("/api/demo?camera=Sex", json={"on": False})
    assert sex.engine.zones == [] and client.get("/api/zones?camera=Sex").json() == {"zones": []}
    client.post("/api/demo?camera=Sex", json={"on": True})  # the demo zone comes back, also after a restart
    assert [z.name for z in sex.engine.zones] == ["A"]
    assert hub.Hub([("Kirish", "a.mp4"), ("Sex", "b.mp4")]).get("Sex").engine.zones == []


def test_incidents_carry_their_camera_and_files_do_not_collide(setup):
    _, cameras, client = setup
    for p in cameras.cameras.values():
        feed(p)  # both cameras give their person track ID 1 within the same second
    rows = client.get("/api/incidents").json()
    assert sorted(r["camera"] for r in rows) == ["Kirish", "Sex"]
    assert len({r["snapshot"] for r in rows}) == 2


def test_status_is_per_camera_and_header_shows_the_worst(setup):
    _, cameras, client = setup
    for p in cameras.cameras.values():
        p.video.connected = True
    cameras.set_zones("Sex", [ZONE])
    feed(cameras.get("Sex"))
    s = client.get("/api/status?camera=Kirish").json()
    assert s["name"] == "Kirish" and s["status"] == "safe"
    assert s["overall"] == {"status": "zone", "camera": "Sex"} and s["voice"]["camera"] == "Sex"
    assert [c["name"] for c in s["cameras"]] == ["Kirish", "Sex"]


def test_unknown_camera_and_frames(setup):
    _, cameras, client = setup
    for url in ("/video?camera=x", "/api/status?camera=x", "/api/zones?camera=x", "/api/frame?camera=x"):
        assert client.get(url).status_code == 404, url
    assert client.get("/api/frame?camera=Sex").status_code == 503
    sex = cameras.get("Sex")
    sex.video.connected, sex.jpeg = True, b"jpegbytes"
    assert client.get("/api/frame?camera=Sex").content == b"jpegbytes"
    client.cookies.clear()
    assert client.get("/api/frame?camera=Sex").status_code == 401


def test_health_checks_all_cameras(setup):
    _, cameras, client = setup
    # Public endpoint: no auth needed
    client.cookies.clear()
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "people" not in data
    assert data["status"] == "warning"
    assert data["camera"] is False
    assert "Kirish" in data["cameras"] and "Sex" in data["cameras"]
    assert data["cameras"]["Kirish"]["connected"] is False

    # One connected, one disconnected -> still warning
    cameras.cameras["Kirish"].video.connected = True
    cameras.cameras["Kirish"].fps = 12.5
    data = client.get("/api/health").json()
    assert data["status"] == "warning"
    assert data["camera"] is False
    assert data["cameras"]["Kirish"]["connected"] is True
    assert data["cameras"]["Sex"]["connected"] is False

    # Both connected -> ok
    cameras.cameras["Sex"].video.connected = True
    cameras.cameras["Sex"].fps = 17.5
    data = client.get("/api/health").json()
    assert data["status"] == "ok"
    assert data["camera"] is True
    assert data["fps"] == 30.0


def test_camera_disconnect_alert_contains_camera_name(monkeypatch):
    sent = []
    class Recorder:
        def notify(self, text):
            sent.append(text)

    p = hub.Pipeline("Darvoza", 1, "0", None, Recorder(), hub.Voice())
    p.video.connected = False

    # Call actual pipeline code: disconnected at t=100.0
    p._check_connection(100.0)
    assert len(sent) == 0  # < 10 seconds: no alert yet

    # Call actual pipeline code: >10s elapsed at t=111.0
    p._check_connection(111.0)
    assert len(sent) == 1
    assert "[Darvoza]" in sent[0]
    assert "aloqa uzildi" in sent[0]

    # Reconnect at t=115.0: call actual pipeline code
    p.video.connected = True
    p._check_connection(115.0)
    assert len(sent) == 2
    assert "[Darvoza]" in sent[1]
    assert "aloqa qayta tiklandi" in sent[1]


def test_a_stopped_camera_releases_the_source_and_starts_again(setup, monkeypatch):
    _, cameras, client = setup
    started = []
    monkeypatch.setattr(hub.Pipeline, "_source", lambda self: "c.mp4")
    monkeypatch.setattr("app.pipeline.VideoSource.start", lambda self: started.append(self))
    sex = cameras.get("Sex")
    sex.video.connected, sex.jpeg = True, b"old"

    r = client.post("/api/camera/run?camera=Sex", json={"on": False})
    assert r.json() == {"running": False}
    assert sex.video.connected is False and sex.jpeg is None
    s = client.get("/api/status?camera=Sex").json()
    assert s["running"] is False and s["status"] == "stopped"
    assert s["overall"]["status"] != "stopped" or all(c["status"] == "stopped" for c in s["cameras"])
    assert client.get("/api/frame?camera=Sex").status_code == 503
    assert client.get("/api/health").json()["cameras"]["Sex"]["running"] is False

    sex._check_connection(100.0)
    sex._check_connection(200.0)
    assert sex._cam_alert_sent is False  # a stop is deliberate, not an outage

    sex.set_demo(False)  # switching mode while stopped must not open the camera
    assert started == []

    assert client.post("/api/camera/run?camera=Sex", json={"on": True}).json() == {"running": True}
    assert started == [sex.video] and cameras.get("Kirish").running is True
    assert client.post("/api/camera/run?camera=x", json={"on": True}).status_code == 404
