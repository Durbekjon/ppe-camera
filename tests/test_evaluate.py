import pytest

from app import evaluate
from app.detector import HELMET, NO_HELMET, PERSON

A, B = (0.1, 0.1, 0.3, 0.3), (0.6, 0.6, 0.8, 0.8)
T = {PERSON: 0.4, HELMET: 0.25, NO_HELMET: 0.4}


def test_perfect_predictions():
    table = evaluate.score([("a", [(PERSON, A), (PERSON, B)])], [[(PERSON, 0.9, A), (PERSON, 0.8, B)]], T)
    assert table[PERSON] == {"labels": 2, "precision": 1.0, "recall": 1.0, "ap50": 1.0}


def test_known_average_precision():
    # ranked: right, wrong, right out of 2 labels -> AP = 0.5 * 1 + 0.5 * 2/3
    found = [(PERSON, 0.9, A), (PERSON, 0.8, (0.4, 0.0, 0.5, 0.1)), (PERSON, 0.7, B)]
    row = evaluate.score([("a", [(PERSON, A), (PERSON, B)])], [found], T)[PERSON]
    assert row["ap50"] == pytest.approx(0.5 + 0.5 * 2 / 3) and row["precision"] == pytest.approx(2 / 3)


def test_duplicate_detection_counts_as_false_positive():
    row = evaluate.score([("a", [(PERSON, A)])], [[(PERSON, 0.9, A), (PERSON, 0.8, A)]], T)[PERSON]
    assert row["precision"] == 0.5 and row["recall"] == 1.0


def test_threshold_limits_precision_and_recall_but_not_ap():
    row = evaluate.score([("a", [(PERSON, A)])], [[(PERSON, 0.2, A)]], T)[PERSON]
    assert row["precision"] is None and row["recall"] == 0.0 and row["ap50"] == 1.0


def test_matches_do_not_cross_images():
    row = evaluate.score([("a", [(PERSON, A)]), ("b", [])], [[], [(PERSON, 0.9, A)]], T)[PERSON]
    assert row["precision"] == 0.0 and row["recall"] == 0.0


def test_cap_taken_for_helmet_is_counted():
    samples = [("a", [(NO_HELMET, A), (NO_HELMET, B)])]
    found = [[(HELMET, 0.6, A), (HELMET, 0.5, B), (NO_HELMET, 0.9, B)]]
    assert evaluate.bare_heads_called_helmet(samples, found, T) == (1, 2)


def dataset(tmp_path, label="1 0.5 0.5 0.2 0.2\n"):
    (tmp_path / "images" / "test").mkdir(parents=True)
    (tmp_path / "labels" / "test").mkdir(parents=True)
    for name in ("one", "two"):
        (tmp_path / "images" / "test" / f"{name}.jpg").write_bytes(b"x")
    (tmp_path / "labels" / "test" / "one.txt").write_text(label)
    (tmp_path / "data.yaml").write_text("path: .\ntest: images/test\nnames: [person, helmet, no_helmet, gloves]\n")
    return tmp_path / "data.yaml"


def test_yolo_dataset_is_read_and_unlabelled_images_are_reported(tmp_path):
    samples, unlabelled = evaluate.load_split(dataset(tmp_path, "1 0.5 0.5 0.2 0.2\n3 0.1 0.1 0.1 0.1\n"), "test")
    assert len(samples) == 2 and unlabelled == 1
    assert [role for role, _ in samples[0][1]] == [HELMET]  # classes the app does not use are skipped
    assert samples[0][1][0][1] == pytest.approx((0.4, 0.4, 0.6, 0.6))


@pytest.mark.parametrize("label", ["9 0.5 0.5 0.2 0.2", "1 50 50 20 20", "1 0.5 0.5"])
def test_broken_labels_stop_the_run(tmp_path, label):
    with pytest.raises(ValueError):
        evaluate.load_split(dataset(tmp_path, label), "test")
