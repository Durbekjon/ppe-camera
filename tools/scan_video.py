"""Sample a long video (default 2 frames/s) and write per-sample counts to CSV, to find good demo segments.

Usage: python -m tools.scan_video video.mp4 out.csv [samples_per_second]
Columns: seconds, people (big enough to judge), with_helmet, without_helmet, helmets, bare_heads
"""
import sys
import cv2
from app import config
from app.detector import HELMET, NO_HELMET, PERSON, Detector
from app.violations import MIN_PERSON_HEIGHT, ViolationEngine

path, out = sys.argv[1], sys.argv[2]
rate = float(sys.argv[3]) if len(sys.argv) > 3 else 2
cap = cv2.VideoCapture(path)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
step = max(1, round(fps / rate))
det = Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF)
eng = ViolationEngine()
n = 0
with open(out, "w") as f:
    f.write("seconds,people,with_helmet,without_helmet,helmets,bare_heads\n")
    while cap.grab():
        if n % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            h = frame.shape[0]
            dets = det.detect(frame)
            people = [d for d in dets if d.role == PERSON and d.box[3] - d.box[1] >= MIN_PERSON_HEIGHT * h]
            without = sum(1 for p in people if eng._missing(p.box, dets))
            f.write(f"{n / fps:.1f},{len(people)},{len(people) - without},{without},"
                    f"{sum(d.role == HELMET for d in dets)},{sum(d.role == NO_HELMET for d in dets)}\n")
        n += 1
print("done", n, "frames")
