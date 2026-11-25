import io
import zipfile
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import auth, config, db, export, hub, main, tts


def _auth_client(tmp_path):
    db.init(tmp_path / "t.db")
    auth._failures.clear()
    auth.set_user("admin", "password-123", auth.ADMIN)
    client = TestClient(main.app, client=("127.0.0.1", 5000))
    client.post("/api/login", json={"username": "admin", "password": "password-123"})
    return client


def test_local_audio_plays_when_enabled(tmp_path, monkeypatch):
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / "helmet.mp3").write_bytes(b"fake-mp3")
    monkeypatch.setattr(tts, "AUDIO_DIR", audio_dir)
    monkeypatch.setattr(config, "LOCAL_AUDIO", True)
    monkeypatch.setattr(tts, "_find_player", lambda: ["true"])

    called = []

    class DummyProc:
        def poll(self):
            return 0

    def fake_popen(cmd, **kwargs):
        called.append(cmd)
        return DummyProc()

    monkeypatch.setattr(tts.subprocess, "Popen", fake_popen)
    tts._current_proc = None

    v = hub.Voice()
    ev = SimpleNamespace(missing=("helmet",), zone=False, camera="Kamera 1")
    v.warn(ev, now=10.0)

    assert len(called) == 1
    assert called[0][0] == "true"
    assert called[0][1].endswith("helmet.mp3")


def test_local_audio_skipped_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOCAL_AUDIO", False)
    played = []
    monkeypatch.setattr(tts, "play_local", lambda k: played.append(k))
    v = hub.Voice()
    v.warn(SimpleNamespace(missing=("helmet",), zone=False, camera="C1"), now=10.0)
    assert played == []


def test_trend_and_xlsx_export(tmp_path):
    client = _auth_client(tmp_path)
    db.add_incident("2026-11-20 10:00:00", ("helmet",), 0, 1, "a.jpg", camera="Darvoza")
    db.add_incident("2026-11-20 11:00:00", ("vest",), 1, 2, "b.jpg", zone_name="Z1", camera="Darvoza")
    db.add_incident("2026-11-21 09:00:00", ("helmet",), 0, 3, "c.jpg", camera="Sex")
    # False alarm must be excluded
    fa_id = db.add_incident("2026-11-21 10:00:00", ("helmet",), 0, 4, "d.jpg", camera="Sex")
    db.set_false_alarm(fa_id, True)

    res = client.get("/api/trend?start=2026-11-20&end=2026-11-21")
    assert res.status_code == 200
    days = res.json()["days"]
    assert days == [
        {"date": "2026-11-20", "total": 2, "zone": 1},
        {"date": "2026-11-21", "total": 1, "zone": 0},
    ]

    xlsx_res = client.get("/api/export.xlsx?start=2026-11-20&end=2026-11-21")
    assert xlsx_res.status_code == 200
    assert "spreadsheetml" in xlsx_res.headers["content-type"]
    assert "hisobot_2026-11-20_2026-11-21.xlsx" in xlsx_res.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(xlsx_res.content)) as zf:
        assert "xl/worksheets/sheet1.xml" in zf.namelist()
        xml_data = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert "Darvoza" in xml_data
        assert "Sex" in xml_data
        assert "d.jpg" not in xml_data
