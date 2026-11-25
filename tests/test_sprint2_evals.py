import os
from pathlib import Path

import pytest

from tools.eval_non_human import NON_HUMAN_DIR, evaluate_model, generate_test_cases
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


def test_eval_non_human_generation_and_evaluation():
    model_path = "models/ppe_yolov8s.pt"
    if not os.path.exists(model_path):
        pytest.skip(f"{model_path} topilmadi")

    generate_test_cases()
    expected_files = [
        "poster_safety_helmet.jpg",
        "logo_warning_sign.jpg",
        "jacket_stand_dummy.jpg",
        "poster_silhouette.jpg",
    ]
    for fname in expected_files:
        assert (NON_HUMAN_DIR / fname).exists()

    res = evaluate_model(model_path)
    assert res is not None
    assert res["pipeline_new"] == 0  # Debounce prevents immediate incident events
