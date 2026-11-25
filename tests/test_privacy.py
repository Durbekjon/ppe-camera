from datetime import datetime

import cv2
import numpy as np
import pytest

from app import alerts, config, db, privacy
from app.violations import Event

PHOTO = str(config.ROOT / "testdata" / "images" / "hardhat_worker_pd.jpg")


def photo():
    image = cv2.imread(PHOTO)
    return cv2.resize(image, (960, int(image.shape[0] * 960 / image.shape[1])))


def detail(image, box):
    x1, y1, x2, y2 = (max(0, int(v)) for v in box)
    return float(np.abs(np.diff(image[y1:y2, x1:x2].astype(int), axis=1)).mean())


def test_real_face_is_found_and_blurred():
    image = photo()
    faces = privacy.find_faces(image)
    assert faces
    blurred = privacy.anonymize(image)
    assert detail(blurred, faces[0]) < 0.6 * detail(image, faces[0])
    assert np.array_equal(blurred[-50:], image[-50:])  # the rest of the picture is untouched


def test_person_without_a_found_face_gets_the_head_blurred(monkeypatch):
    monkeypatch.setattr(privacy, "find_faces", lambda image: [])
    assert privacy.face_regions(np.zeros((500, 500, 3), np.uint8), [(100, 100, 300, 500)]) == [(120, 100, 280, 200)]


def test_found_face_replaces_the_head_guess(monkeypatch):
    monkeypatch.setattr(privacy, "find_faces", lambda image: [(150, 120, 250, 220)])
    regions = privacy.face_regions(np.zeros((500, 500, 3), np.uint8), [(100, 100, 300, 500)])
    assert regions == [(135, 100, 265, 240)]


def test_failure_blurs_the_whole_picture(monkeypatch):
    def boom(*args):
        raise RuntimeError("model missing")

    monkeypatch.setattr(privacy, "face_regions", boom)
    image = np.random.default_rng(1).integers(0, 255, (360, 480, 3), np.uint8)
    out = privacy.anonymize(image)
    assert detail(out, (0, 0, 480, 360)) < 0.2 * detail(image, (0, 0, 480, 360))


@pytest.mark.parametrize("enabled", [True, False])
def test_saved_snapshot_is_the_blurred_one(tmp_path, monkeypatch, enabled):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "BLUR_FACES", enabled)
    db.init(tmp_path / "t.db")
    image = photo()
    face = privacy.find_faces(image)[0]
    manager = alerts.AlertManager()
    manager.handle(Event(1, ("helmet",), False, (0, 0, 1, 1)), image)
    saved = cv2.imread(str(tmp_path / db.list_incidents()[0]["snapshot"]))
    assert (detail(saved, face) < 0.6 * detail(image, face)) is enabled


def test_old_snapshots_expire_but_incidents_remain(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(config, "RETENTION_DAYS", 30)
    db.init(tmp_path / "t.db")
    new_name = datetime.now().strftime("%Y%m%d_%H%M%S") + "_2.jpg"
    for name in ("20200101_120000_1.jpg", new_name):
        (tmp_path / name).write_bytes(b"x")
        db.add_incident("2026-11-25 10:00:00", ("helmet",), 0, 1, name)
    (tmp_path / "keep.txt").write_text("not a snapshot")
    alerts.expire_snapshots()
    assert sorted(p.name for p in tmp_path.glob("*.jpg")) == [new_name]
    assert (tmp_path / "keep.txt").exists()
    assert [r["snapshot"] for r in db.list_incidents()] == [new_name, ""]


def test_zero_days_keeps_everything(tmp_path):
    (tmp_path / "20200101_120000_1.jpg").write_bytes(b"x")
    assert privacy.delete_old_snapshots(tmp_path, 0) == []
