import io
import zipfile
from types import SimpleNamespace
from xml.etree import ElementTree

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


class _Playing:
    """A fake player process that is still playing until terminated."""

    def __init__(self, command, **kwargs):
        self.name, self.stopped = command[-1].rsplit("/", 1)[-1], False

    def poll(self):
        return 0 if self.stopped else None

    def terminate(self):
        self.stopped = True


def test_zone_warning_interrupts_an_ordinary_one_but_not_another_zone_warning(tmp_path, monkeypatch):
    for key in ("helmet", "zone", "entry"):
        (tmp_path / f"{key}.mp3").write_bytes(b"x")
    started = []

    def popen(command, **kwargs):
        started.append(_Playing(command))
        return started[-1]

    monkeypatch.setattr(tts, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(tts, "_find_player", lambda: ["fake"])
    monkeypatch.setattr(tts.subprocess, "Popen", popen)
    monkeypatch.setattr(tts, "_current_proc", None)
    assert tts.play_local("helmet") and not tts.play_local("helmet")
    assert tts.play_local("zone") and started[0].stopped
    assert not tts.play_local("helmet") and not tts.play_local("entry") and not started[1].stopped
    started[1].stopped = True  # finished
    assert tts.play_local("helmet")
    assert [p.name for p in started] == ["helmet.mp3", "zone.mp3", "helmet.mp3"]


def test_trend_includes_quiet_days(tmp_path):
    client = _auth_client(tmp_path)
    db.add_incident("2026-11-19 10:00:00", ("helmet",), 0, 1, "")
    db.add_incident("2026-11-25 10:00:00", ("helmet",), 1, 2, "")
    days = client.get("/api/trend?start=2026-11-19&end=2026-11-25").json()["days"]
    assert [d["total"] for d in days] == [1, 0, 0, 0, 0, 0, 1]
    assert len(client.get("/api/trend?days=30").json()["days"]) == 30


def test_bad_periods_are_rejected_not_crashing(tmp_path):
    client = _auth_client(tmp_path)
    for query in ("end=abc", "end=2026-13-45", "start=abc&end=def", "start=2026-11-25&end=2026-11-01",
                  "start=2000-01-01&end=2026-01-01", "end=0001-01-01&days=30"):
        for path in ("/api/trend", "/api/export.xlsx"):
            assert client.get(f"{path}?{query}").status_code == 400, (path, query)


def test_excel_values_are_in_uzbek_and_control_characters_are_dropped():
    data = export.build_xlsx([{"id": 1, "ts": "t", "missing": "helmet,entry", "zone": 1,
                               "zone_name": "A\x01<B>", "camera": "K", "status": "hal_qilindi"}])
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        sheet = zf.read("xl/worksheets/sheet1.xml").decode()
    ElementTree.fromstring(sheet.encode())
    assert "Kaskasiz, Taqiqlangan hududda" in sheet and "Hal qilindi" in sheet and "A&lt;B&gt;" in sheet
