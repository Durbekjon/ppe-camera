import cv2
import numpy as np
import pytest

from app import config, tamper
from app.hub import SEVERITY

PHOTO = cv2.imread(str(config.ROOT / "testdata/images/hardhat_worker_pd.jpg"))


def covered_frames():
    return {
        "black": np.zeros_like(PHOTO),
        "hand": cv2.GaussianBlur((PHOTO * 0.15).astype(np.uint8), (0, 0), 25),
        "cloth": np.full_like(PHOTO, 120),
        "out of focus": cv2.GaussianBlur(PHOTO, (0, 0), 20),
    }


def test_real_scenes_are_fine():
    cap = cv2.VideoCapture(str(config.ROOT / "testdata/stills.mp4"))
    seen = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        seen += 1
        assert tamper.view_ok(frame)
    assert seen > 100


@pytest.mark.parametrize("name", list(covered_frames()))
def test_covered_views_are_not_fine(name):
    assert not tamper.view_ok(covered_frames()[name])


def test_short_cover_is_ignored_and_long_one_reported_once_then_restored():
    guard = tamper.ViewGuard()
    black = np.zeros_like(PHOTO)
    assert [guard.update(black, t / 10) for t in range(25)] == [None] * 25  # 2.5 s: not yet
    assert guard.update(PHOTO, 2.6) is None and not guard.blocked  # uncovered in time
    events = [guard.update(black, 3 + t / 10) for t in range(60)]
    assert events.count("blocked") == 1 and guard.blocked
    events = [guard.update(PHOTO, 10 + t / 10) for t in range(30)]
    assert events.count("restored") == 1 and not guard.blocked


def test_blocked_ranks_between_danger_and_offline():
    assert SEVERITY.index("danger") < SEVERITY.index("blocked") < SEVERITY.index("offline")
