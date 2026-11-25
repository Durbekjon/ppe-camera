"""PPE-402: Evaluate safety vest detection precision and recall across test data.

Usage:
    .venv/bin/python tools/eval_vest.py [model_path]
"""
import glob
import os
import sys
import cv2

from app.detector import Detector, PERSON, VEST, NO_VEST


# Ground truth for standard reference images:
# (has_vest_count, no_vest_count)
GROUND_TRUTH = {
    "amsterdam_workers_cc0.jpg": {"vest": 2, "no_vest": 0},
    "bus.jpg": {"vest": 0, "no_vest": 2},
    "hardhat_worker_pd.jpg": {"vest": 0, "no_vest": 1},
    "metro_shaft_group.jpg": {"vest": 0, "no_vest": 4},
    "zidane.jpg": {"vest": 0, "no_vest": 1},
}


def evaluate(model_path, imgsz=480, conf=0.4, gear_conf=0.25):
    print(f"=== PPE-402: Jilet (Vest) Sinovi: {os.path.basename(model_path)} (imgsz={imgsz}, conf={conf}, gear_conf={gear_conf}) ===")
    d = Detector(model_path, imgsz, conf, gear_conf)

    tp, fp, fn, tn = 0, 0, 0, 0
    results = []

    for img_path in sorted(glob.glob("testdata/images/*.jpg")):
        name = os.path.basename(img_path)
        if name not in GROUND_TRUTH:
            continue
        gt = GROUND_TRUTH[name]
        img = cv2.imread(img_path)
        if img is None:
            continue

        dets = d.detect(img)
        vest_dets = [det for det in dets if det.role == VEST]
        no_vest_dets = [det for det in dets if det.role == NO_VEST]

        pred_vest = len(vest_dets)
        pred_no_vest = len(no_vest_dets)

        # TP: correctly detected vests
        true_vests = min(pred_vest, gt["vest"])
        # FP: detected vest when not present
        false_vests = max(0, pred_vest - gt["vest"])
        # FN: missed vests
        missed_vests = max(0, gt["vest"] - pred_vest)
        # TN: correctly identified non-vest / negative
        correct_neg = 1 if gt["vest"] == 0 and pred_vest == 0 else 0

        tp += true_vests
        fp += false_vests
        fn += missed_vests
        tn += correct_neg

        results.append({
            "name": name,
            "gt_vest": gt["vest"],
            "pred_vest": pred_vest,
            "pred_no_vest": pred_no_vest,
            "vest_confs": [round(det.conf, 2) for det in vest_dets],
            "no_vest_confs": [round(det.conf, 2) for det in no_vest_dets],
        })

    print(f"{'Tasvir':28s} {'Haqiqiy jilet':15s} {'Topilgan jilet':16s} {'Ishonch darajalari':25s}")
    print("-" * 88)
    for r in results:
        confs_str = f"vest:{r['vest_confs']} no_vest:{r['no_vest_confs']}"
        print(f"{r['name']:28s} {r['gt_vest']:<15d} {r['pred_vest']:<16d} {confs_str}")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print("-" * 88)
    print(f"📊 Xulosa Metrikalari:")
    print(f"  • True Positives (TP):  {tp}")
    print(f"  • False Positives (FP): {fp}")
    print(f"  • False Negatives (FN): {fn}")
    print(f"  • Precision:            {precision:.2%} ({precision:.3f})")
    print(f"  • Recall:               {recall:.2%} ({recall:.3f})")
    print(f"  • F1-Score:             {f1:.3f}")

    return {
        "model": os.path.basename(model_path),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "details": results,
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "models/ppe_yolov8s.pt"
    evaluate(path)
