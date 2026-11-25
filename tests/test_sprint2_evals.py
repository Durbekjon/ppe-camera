import os
from pathlib import Path

import pytest

from app.detector import PERSON, Detection
from tools.eval_non_human import NON_HUMAN_DIR, incidents_over_time
from tools.eval_vest import evaluate as evaluate_vest


def test_eval_vest_metrics_on_base_model():
    model_path = "models/ppe_yolov8s.pt"
    if not os.path.exists(model_path):
        pytest.skip(f"{model_path} topilmadi")

    res = evaluate_vest(model_path)
    assert res["tp"] == 2
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1"] == 1.0


def test_non_human_measurement_runs_long_enough_to_record_incidents():
    # A detection wrongly called "person" that stays in view must show up, otherwise "0 incidents" means nothing.
    person = [Detection(PERSON, 0.9, (200.0, 100.0, 400.0, 500.0))]
    assert incidents_over_time(person, (800, 600), 0.4) == 1
    assert incidents_over_time(person, (800, 600), 0.4, seconds=1.0) == 0  # shorter than the debounce
    assert incidents_over_time([], (800, 600), 0.4) == 0


def test_non_human_images_are_committed():
    names = {p.name for p in NON_HUMAN_DIR.glob("*.jpg")}
    assert names == {"poster_safety_helmet.jpg", "logo_warning_sign.jpg", "jacket_stand_dummy.jpg",
                     "poster_silhouette.jpg"}
