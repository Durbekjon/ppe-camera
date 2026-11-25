import sqlite3
import pytest
from fastapi.testclient import TestClient

from app import auth, db, main


@pytest.fixture
def env(tmp_path):
    db_path = tmp_path / "test.db"
    db.init(db_path)
    auth._failures.clear()
    auth.set_user("admin_user", "password-admin", auth.ADMIN)
    auth.set_user("watcher_user", "password-supervisor", auth.SUPERVISOR)
    client = TestClient(main.app, client=("127.0.0.1", 5000))
    return tmp_path, db_path, client


def test_db_migration_adds_status_to_old_table(tmp_path):
    # Simulate an old database without 'status' column
    legacy_db = tmp_path / "legacy.db"
    conn = sqlite3.connect(legacy_db)
    conn.execute(
        """CREATE TABLE incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            missing TEXT NOT NULL,
            zone INTEGER NOT NULL,
            track_id INTEGER,
            snapshot TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO incidents (ts, missing, zone, track_id, snapshot) "
        "VALUES ('2026-11-20 10:00:00', 'helmet', 0, 1, 's1.jpg')"
    )
    conn.commit()
    conn.close()

    # Calling db.init on legacy db should migrate without losing data
    db.init(legacy_db)
    rows = db.list_incidents()
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["status"] == "yangi"  # migrated old row gets default 'yangi'


def test_status_update_and_aliases(env):
    _, _, client = env
    id1 = db.add_incident("2026-11-25 09:00:00", ("helmet",), 0, 1, "s1.jpg", camera="Cam1")
    id2 = db.add_incident("2026-11-25 09:30:00", ("vest",), 1, 2, "s2.jpg", camera="Cam2", zone_name="Qurilish")

    # Default is 'yangi'
    incidents = db.list_incidents()
    assert incidents[1]["status"] == "yangi"
    assert incidents[0]["status"] == "yangi"

    # Must be logged in
    r = client.post(f"/api/incidents/{id1}/status", json={"status": "ko'rildi"})
    assert r.status_code == 401

    # Login as supervisor (allowed to update status)
    client.post("/api/login", json={"username": "watcher_user", "password": "password-supervisor"})

    # Update to 'ko'rildi'
    r = client.post(f"/api/incidents/{id1}/status", json={"status": "ko'rildi"})
    assert r.status_code == 200
    assert r.json() == {"id": id1, "status": "ko'rildi"}

    # Update to 'hal_qilindi' using english alias 'resolved'
    r = client.post(f"/api/incidents/{id2}/status", json={"status": "resolved"})
    assert r.status_code == 200
    assert r.json() == {"id": id2, "status": "hal_qilindi"}

    # Invalid status returns 400
    r = client.post(f"/api/incidents/{id1}/status", json={"status": "unknown_status"})
    assert r.status_code == 400

    # Non-existent incident returns 400
    r = client.post("/api/incidents/9999/status", json={"status": "yangi"})
    assert r.status_code == 400


def test_incident_filters(env):
    _, _, client = env
    client.post("/api/login", json={"username": "watcher_user", "password": "password-supervisor"})

    id1 = db.add_incident("2026-11-24 10:00:00", ("helmet",), 0, 1, "s1.jpg", camera="Kirish")
    id2 = db.add_incident("2026-11-25 11:00:00", ("vest",), 1, 2, "s2.jpg", camera="Sex", zone_name="XavfliZona")
    id3 = db.add_incident("2026-11-25 14:00:00", ("helmet", "vest"), 1, 3, "s3.jpg", camera="Kirish", zone_name="XavfliZona")

    db.set_status(id1, "ko'rildi")
    db.set_status(id3, "hal_qilindi")

    # Filter by status
    r = client.get("/api/incidents?status=yangi").json()
    assert len(r) == 1 and r[0]["id"] == id2

    r = client.get("/api/incidents?status=ko'rildi").json()
    assert len(r) == 1 and r[0]["id"] == id1

    r = client.get("/api/incidents?status=hal_qilindi").json()
    assert len(r) == 1 and r[0]["id"] == id3

    # Filter by date
    r = client.get("/api/incidents?date=2026-11-24").json()
    assert len(r) == 1 and r[0]["id"] == id1

    r = client.get("/api/incidents?date=2026-11-25").json()
    assert len(r) == 2 and {r[0]["id"], r[1]["id"]} == {id2, id3}

    # Filter by missing
    r = client.get("/api/incidents?missing=vest").json()
    assert len(r) == 2 and {r[0]["id"], r[1]["id"]} == {id2, id3}

    # Filter by zone (boolean and zone_name)
    r = client.get("/api/incidents?zone=1").json()
    assert len(r) == 2
    r = client.get("/api/incidents?zone=0").json()
    assert len(r) == 1 and r[0]["id"] == id1
    r = client.get("/api/incidents?zone=XavfliZona").json()
    assert len(r) == 2

    # Filter by camera
    r = client.get("/api/incidents?camera=Kirish").json()
    assert len(r) == 2 and {r[0]["id"], r[1]["id"]} == {id1, id3}

    # Combined filter: camera=Kirish and status=hal_qilindi
    r = client.get("/api/incidents?camera=Kirish&status=hal_qilindi").json()
    assert len(r) == 1 and r[0]["id"] == id3


def test_zone_name_filter_and_list_of_names(env):
    _, _, client = env
    client.post("/api/login", json={"username": "watcher_user", "password": "password-supervisor"})
    db.add_incident("2026-11-25 09:00:00", ("helmet",), 0, 1, "a.jpg")
    one = db.add_incident("2026-11-25 09:01:00", ("helmet",), 1, 2, "b.jpg", zone_name="1")
    db.add_incident("2026-11-25 09:02:00", ("helmet",), 1, 3, "c.jpg", zone_name="Kran osti")
    assert client.get("/api/incidents/zone-names").json() == {"names": ["1", "Kran osti"]}
    assert [r["id"] for r in client.get("/api/incidents?zone_name=1").json()] == [one]  # not "any zone"
    assert len(client.get("/api/incidents?zone=1").json()) == 2
