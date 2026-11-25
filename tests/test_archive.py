from datetime import datetime

import pytest

from app import alerts, archive, auth, config, dataset, db, outbox

NOW = datetime.now()
NAME = NOW.strftime("%Y%m%d_%H%M%S") + "_c1_1.jpg"


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(config, "RETENTION_DAYS", 30)
    db.init(tmp_path / "live.db")
    auth.set_user("boss", "password-123", auth.ADMIN)
    for folder in (alerts.SNAPSHOTS, dataset.RAW, dataset.EXPORTS / "x"):
        folder.mkdir(parents=True)
        (folder / NAME).write_bytes(b"picture")
    first = db.add_incident("2026-11-25 10:00:00", ("helmet",), 1, 1, NAME, "Z", raw=NAME, camera="K")
    db.set_false_alarm(first, True)
    db.add_incident("2026-11-25 11:00:00", ("entry",), 1, 2, "gone.jpg", camera="K")
    outbox.add(True, "caption", "", "line")
    return tmp_path


def rows():
    return [dict(r) for r in db.query("SELECT * FROM incidents ORDER BY id")]


def test_looking_changes_nothing(data):
    before = rows()
    assert archive.summary() == {"incidents": 2, "unsent": 1, "users": 1, "snapshots": 1, "raw": 1, "exports": 1}
    assert rows() == before and not dataset.ARCHIVE.exists()


def test_archive_empties_the_demo_but_keeps_everything_and_the_users(data):
    folder = archive.create(NOW)
    assert rows() == [] and outbox.pending() == 0 and auth.login("boss", "password-123")
    for kind in ("snapshots/", "raw/", "exports/x/"):
        assert (folder / (kind + NAME)).read_bytes() == b"picture"
    assert not (alerts.SNAPSHOTS / NAME).exists()
    assert db.add_incident("2026-11-25 12:00:00", ("helmet",), 0, 1, "n.jpg") == 1  # numbering restarts
    copy = archive.sqlite3.connect(folder / archive.DB_NAME)
    assert copy.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 2
    assert copy.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0  # no copied password hashes
    copy.close()


def test_restore_brings_back_the_same_rows_and_files(data):
    before = rows()
    folder = archive.create(NOW)
    assert archive.restore(folder.name) == 2
    expected = [dict(before[0]), {**before[1], "snapshot": ""}]  # its picture never existed
    assert rows() == expected and (alerts.SNAPSHOTS / NAME).read_bytes() == b"picture"
    assert outbox.pending() == 0  # old alerts are not sent again


def test_restore_refuses_to_mix_or_to_leave_the_archive_folder(data):
    folder = archive.create(NOW)
    db.add_incident("2026-11-25 12:00:00", ("helmet",), 0, 1, "n.jpg")
    with pytest.raises(ValueError):
        archive.restore(folder.name)
    for name in ("nope", "../live", ""):
        with pytest.raises(ValueError):
            archive.restore(name)


def test_nothing_to_archive(data):
    archive.create(NOW)
    assert archive.create(NOW) is None


def test_archived_pictures_still_expire(data):
    folder = dataset.ARCHIVE / "20261125_000000"
    for kind in ("snapshots", "raw", "exports/x"):
        (folder / kind).mkdir(parents=True)
        (folder / kind / "20200101_120000_1.jpg").write_bytes(b"old")
        (folder / kind / NAME).write_bytes(b"new")
    alerts.expire_snapshots()
    assert not list(folder.rglob("20200101_*.jpg")) and len(list(folder.rglob(NAME))) == 3
