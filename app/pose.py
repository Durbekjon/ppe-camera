"""Human skeletons (17 body points) from a pose model.

They answer two questions the box detector cannot: is this really a person, and is any part of the body
inside a danger zone.
"""
from dataclasses import replace

from .detector import PERSON

POINT_CONF = 0.5  # a body point is trusted above this confidence
MIN_POINTS = 3  # fewer trusted points do not make a skeleton
MATCH_IOU = 0.3
POSE_CONF = 0.2
# COCO body points: 0 nose, 1-4 eyes and ears, 5-6 shoulders, 7-8 elbows, 9-10 wrists, 11-12 hips,
# 13-14 knees, 15-16 ankles. Fingers and toes are not part of the model.
BONES = ((0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12),
         (11, 12), (11, 13), (13, 15), (12, 14), (14, 16))


def _iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0


def attach(detections, skeletons):
    """Give each person detection its skeleton; one skeleton can confirm only one person.

    `skeletons` are (box, points) with points as 17 (x, y, confidence).
    """
    usable = [(box, pts) for box, pts in skeletons if sum(p[2] >= POINT_CONF for p in pts) >= MIN_POINTS]
    pairs = sorted(
        ((_iou(d.box, box), i, j) for i, d in enumerate(detections) if d.role == PERSON
         for j, (box, _) in enumerate(usable)),
        reverse=True,
    )
    chosen, taken = {}, set()
    for overlap, i, j in pairs:
        if overlap < MATCH_IOU:
            break
        if i not in chosen and j not in taken:
            chosen[i] = usable[j][1]
            taken.add(j)
    return [replace(d, keypoints=chosen[i]) if i in chosen else d for i, d in enumerate(detections)]


def body_samples(points, steps=12):
    """Trusted body points, plus points along every bone whose two ends are trusted."""
    samples = [(x, y) for x, y, c in points if c >= POINT_CONF]
    for a, b in BONES:
        (x1, y1, c1), (x2, y2, c2) = points[a], points[b]
        if c1 >= POINT_CONF and c2 >= POINT_CONF:
            samples += [(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps) for i in range(1, steps)]
    return samples


class SkeletonDetector:
    """The box detector with a skeleton added to every person it can match."""

    def __init__(self, detector, model_path, imgsz):
        from ultralytics import YOLO

        self._detector, self._imgsz = detector, imgsz
        self._pose = YOLO(model_path)

    def skeletons(self, frame):
        result = self._pose.predict(frame, imgsz=self._imgsz, conf=POSE_CONF, device="cpu", verbose=False)[0]
        if result.keypoints is None or not len(result.boxes):
            return []
        return [
            (tuple(float(v) for v in box), tuple(tuple(float(v) for v in p) for p in points))
            for box, points in zip(result.boxes.xyxy, result.keypoints.data)
        ]

    def detect(self, frame):
        detections = self._detector.detect(frame)
        if not any(d.role == PERSON for d in detections):
            return detections  # nothing to confirm: skip the second model
        return attach(detections, self.skeletons(frame))
