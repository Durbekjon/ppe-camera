"""Detection metrics on a labelled YOLO-format dataset, per role (person, helmet, bare head, ...).

Models name and number their classes differently, so both the model's and the dataset's class names are
mapped onto the app's roles with `detector.role_of`.
"""
from pathlib import Path

import numpy as np
import yaml

from .detector import HELMET, NO_HELMET, role_of

IOU_MATCH = 0.5
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp"}


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def load_split(data_yaml, split):
    """Return ([(image path, [(role, normalised xyxy), ...])], number of images without a label file)."""
    data_yaml = Path(data_yaml)
    config = yaml.safe_load(data_yaml.read_text())
    names = config["names"]
    names = dict(enumerate(names)) if isinstance(names, list) else {int(k): v for k, v in names.items()}
    roles = {i: role_of(str(n)) for i, n in names.items()}
    if not any(roles.values()):
        raise ValueError(f"data.yaml dagi sinf nomlari tanilmadi: {list(names.values())}")
    if split not in config:
        raise ValueError(f"data.yaml da '{split}' bo'limi yo'q")
    root = Path(config.get("path", "."))
    root = root if root.is_absolute() else data_yaml.parent / root
    folder = root / config[split]
    images = sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_TYPES)
    if not images:
        raise ValueError(f"Rasm topilmadi: {folder}")
    samples, unlabelled = [], 0
    for image in images:
        parts = list(image.parts)
        if "images" not in parts:
            raise ValueError("Rasmlar 'images' papkasida, belgilar yonidagi 'labels' papkasida bo'lsin")
        parts[len(parts) - 1 - parts[::-1].index("images")] = "labels"
        label = Path(*parts).with_suffix(".txt")
        truth = []
        if not label.is_file():
            unlabelled += 1  # counted as an image with nothing in it
        else:
            for number, line in enumerate(label.read_text().splitlines(), 1):
                if not line.strip():
                    continue
                values = line.split()
                if len(values) != 5 or int(values[0]) not in roles:
                    raise ValueError(f"Noto'g'ri belgi: {label} ({number}-qator)")
                cx, cy, w, h = map(float, values[1:])
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
                    raise ValueError(f"Koordinata 0..1 oralig'ida emas: {label} ({number}-qator)")
                if roles[int(values[0])]:
                    truth.append((roles[int(values[0])], (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)))
        samples.append((image, truth))
    if unlabelled == len(images):
        raise ValueError("Birorta ham belgi fayli topilmadi")
    return samples, unlabelled


def match(truth, predictions):
    """Greedy matching in confidence order. Return [(confidence, is correct)] for one image and role."""
    used, results = set(), []
    for conf, box in sorted(predictions, key=lambda p: -p[0]):
        best, best_iou = None, IOU_MATCH
        for i, t in enumerate(truth):
            overlap = iou(box, t)
            if i not in used and overlap >= best_iou:
                best, best_iou = i, overlap
        if best is not None:
            used.add(best)
        results.append((conf, best is not None))
    return results


def average_precision(results, total_truth):
    """Area under the precision/recall curve (all-point interpolation)."""
    if not total_truth:
        return None
    if not results:
        return 0.0
    correct = np.array([ok for _, ok in sorted(results, key=lambda r: -r[0])])
    tp = np.cumsum(correct)
    precision = tp / np.arange(1, len(correct) + 1)
    recall = tp / total_truth
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    return float(np.sum(np.diff(np.concatenate(([0.0], recall))) * precision))


def score(samples, predictions, thresholds):
    """`predictions[i]` is [(role, confidence, normalised box)] for samples[i], at a very low threshold.

    Precision and recall use the app's own thresholds (what it would really report); AP50 uses all predictions.
    Roles absent from the labels are left out.
    """
    roles = sorted({role for _, truth in samples for role, _ in truth})
    table = {}
    for role in roles:
        results, total = [], 0
        for (_, truth), found in zip(samples, predictions):
            boxes = [b for r, b in truth if r == role]
            total += len(boxes)
            results += match(boxes, [(c, b) for r, c, b in found if r == role])
        used = [ok for conf, ok in results if conf >= thresholds.get(role, 0.4)]
        # Matching in confidence order means dropping low scores does not change the matches above them.
        tp = sum(used)
        table[role] = {
            "labels": total,
            "precision": tp / len(used) if used else None,
            "recall": tp / total,
            "ap50": average_precision(results, total),
        }
    return table


def bare_heads_called_helmet(samples, predictions, thresholds):
    """(count, total): labelled bare heads (caps included) where the model reports a helmet and no bare head wins."""
    wrong = total = 0
    for (_, truth), found in zip(samples, predictions):
        for role, head in truth:
            if role != NO_HELMET:
                continue
            total += 1
            best = {HELMET: 0.0, NO_HELMET: 0.0}
            for r, conf, box in found:
                if r in best and conf >= thresholds.get(r, 0.4) and iou(box, head) >= IOU_MATCH:
                    best[r] = max(best[r], conf)
            wrong += best[HELMET] > 0 and best[HELMET] >= best[NO_HELMET]  # same tie rule as the app
    return wrong, total
