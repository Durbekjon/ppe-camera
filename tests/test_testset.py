import cv2
import pytest

from app import config, evaluate
from tools import label, make_testset


def test_box_round_trip_and_clipping():
    line = label.to_yolo(2, (900, 500, 100, 50), 1000, 1000)  # drawn right-to-left
    cls, box = label.from_yolo(line, 1000, 1000)
    assert cls == 2 and box == pytest.approx((100, 50, 900, 500))
    _, clipped = label.from_yolo(label.to_yolo(0, (-20, 10, 300, 1200), 1000, 1000), 1000, 1000)
    assert clipped == pytest.approx((0, 10, 300, 1000))


def test_testset_feeds_the_evaluation(tmp_path):
    root = tmp_path / "set"
    n = make_testset.extract(config.ROOT / "testdata/stills.mp4", root / "images" / "test", every_s=1.0)
    assert 3 <= n <= 30  # a panning clip of 5 photos: near-identical frames are skipped
    (root / "data.yaml").write_text("path: .\ntest: images/test\nnames: [person, helmet, no_helmet]\n")
    images = sorted((root / "images" / "test").glob("*.jpg"))
    h, w = cv2.imread(str(images[0])).shape[:2]
    label.save(root / "labels" / "test" / (images[0].stem + ".txt"), [(0, (10, 10, 200, 300)), (1, (5, 5, 6, 6))], w, h)
    samples, unlabelled = evaluate.load_split(root / "data.yaml", "test")
    assert len(samples) == n and unlabelled == n - 1
    assert [role for role, _ in samples[0][1]] == ["person"]  # the 1-pixel mis-click was dropped
