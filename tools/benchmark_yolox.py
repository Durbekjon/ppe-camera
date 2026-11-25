"""PPE-501 trial: speed of official YOLOX ONNX models (Apache-2.0 code) next to the current detector.

YOLOX COCO weights know "person" but have NO helmet classes, so this measures speed and how often YOLOX
finds the people the current model finds. It says nothing about helmet accuracy.

Usage: .venv/bin/python -m tools.benchmark_yolox VIDEO model1.onnx [model2.onnx ...] [--every 15]
"""
import argparse
import platform
import statistics
import time
from pathlib import Path

import cv2
import numpy as np

from app import config
from app.detector import PERSON, Detector
from app.evaluate import iou
from app.violations import MIN_PERSON_HEIGHT

SIZES = {"yolox_nano": 416, "yolox_tiny": 416, "yolox_s": 640}  # official export sizes


class YoloxPeople:
    def __init__(self, path):
        self.size = SIZES[Path(path).stem]
        self.net = cv2.dnn.readNetFromONNX(str(path))
        grids, strides = [], []
        for stride in (8, 16, 32):
            n = self.size // stride
            xs, ys = np.meshgrid(np.arange(n), np.arange(n))
            grids.append(np.stack((xs, ys), 2).reshape(-1, 2))
            strides.append(np.full((n * n, 1), stride))
        self.grid, self.stride = np.concatenate(grids), np.concatenate(strides)

    def detect(self, frame, conf):
        """Person boxes in frame pixels."""
        ratio = min(self.size / frame.shape[0], self.size / frame.shape[1])
        resized = cv2.resize(frame, (int(frame.shape[1] * ratio), int(frame.shape[0] * ratio)))
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        canvas[: resized.shape[0], : resized.shape[1]] = resized
        self.net.setInput(canvas.transpose(2, 0, 1)[None].astype(np.float32))  # BGR, 0..255
        out = self.net.forward()[0]
        scores = out[:, 4] * out[:, 5]  # objectness x "person" (COCO class 0)
        keep = scores >= conf
        centre = (out[keep, :2] + self.grid[keep]) * self.stride[keep]
        size = np.exp(out[keep, 2:4]) * self.stride[keep]
        boxes = np.concatenate((centre - size / 2, size), 1) / ratio  # x, y, w, h
        chosen = cv2.dnn.NMSBoxes(boxes.tolist(), scores[keep].tolist(), conf, 0.45)
        return [(x, y, x + w, y + h) for x, y, w, h in (boxes[i] for i in np.array(chosen).reshape(-1))]


def timed(function, frames):
    for frame in frames[:5]:
        function(frame)  # warm up
    results, times = [], []
    for frame in frames:
        start = time.perf_counter()
        results.append(function(frame))
        times.append((time.perf_counter() - start) * 1000)
    return results, statistics.median(times), float(np.percentile(times, 95))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video")
    parser.add_argument("models", nargs="+")
    parser.add_argument("--every", type=int, default=15)
    args = parser.parse_args()
    cap, frames, index = cv2.VideoCapture(args.video), [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % args.every == 0:
            h, w = frame.shape[:2]
            if w > config.FRAME_WIDTH:
                frame = cv2.resize(frame, (config.FRAME_WIDTH, int(h * config.FRAME_WIDTH / w)))
            frames.append(frame)
        index += 1
    if not frames:
        raise SystemExit(f"Kadr o'qilmadi: {args.video}")

    def tall(boxes, frame):
        return [b for b in boxes if b[3] - b[1] >= MIN_PERSON_HEIGHT * frame.shape[0]]

    current = Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF)
    found, median, p95 = timed(lambda f: [d.box for d in current.detect(f) if d.role == PERSON], frames)
    reference = [tall(b, f) for b, f in zip(found, frames)]
    total = sum(map(len, reference))
    print(f"{platform.machine()} {platform.system()}, OpenCV {cv2.__version__}, {len(frames)} kadr, CONF={config.CONF}")
    print(f"joriy {Path(config.MODEL_PATH).name} (imgsz={config.IMG_SIZE}): median {median:.1f} ms, p95 {p95:.1f} ms, odam {total}")
    for path in args.models:
        model = YoloxPeople(path)
        found, median, p95 = timed(lambda f: model.detect(f, config.CONF), frames)
        mine = [tall(b, f) for b, f in zip(found, frames)]
        matched = extra = 0
        for theirs, ours in zip(reference, mine):
            free = list(ours)
            for box in theirs:
                best = max(free, key=lambda b: iou(box, b), default=None)
                if best is not None and iou(box, best) >= 0.5:
                    matched += 1
                    free.remove(best)
            extra += len(free)
        share = f"{100 * matched / total:.0f}%" if total else "—"
        print(f"{Path(path).stem} ({model.size}): median {median:.1f} ms, p95 {p95:.1f} ms, odam {sum(map(len, mine))}; "
              f"joriy model topganlarning {matched}/{total} ({share}) tasi topildi, qo'shimcha {extra}")


if __name__ == "__main__":
    main()
