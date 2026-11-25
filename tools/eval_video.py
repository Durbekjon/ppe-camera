"""Run detector + violation logic over a video file (no server) and print alerts and raw processing speed.

Usage: python -m tools.eval_video path/to/video.mp4 [--save-dir DIR]
"""
import sys, time
import cv2
from app import config
from app.detector import Detector
from app.pose import SkeletonDetector
from app.violations import ViolationEngine

path = sys.argv[1]
save = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--save-dir" else None
cap = cv2.VideoCapture(path)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
det = Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF)
if config.SKELETON:
    det = SkeletonDetector(det, config.POSE_MODEL_PATH, config.POSE_IMG_SIZE)
eng = ViolationEngine(config.DEBOUNCE_S, config.COOLDOWN_S, config.REQUIRE_VEST, config.HELMET_RULE, config.CONF, config.RESOLVE_S, config.REJOIN_S, config.SKELETON)
n, spent, events, reminders = 0, 0.0, 0, 0
ids = set()
while True:
    ok, frame = cap.read()
    if not ok:
        break
    h, w = frame.shape[:2]
    if w > config.FRAME_WIDTH:
        frame = cv2.resize(frame, (config.FRAME_WIDTH, int(h * config.FRAME_WIDTH / w)))
    t = time.perf_counter()
    dets = det.detect(frame)
    people, evs = eng.update(dets, n / fps, (frame.shape[1], frame.shape[0]))
    spent += time.perf_counter() - t
    ids.update(p.id for p in people)
    for e in evs:
        if not e.record:
            reminders += 1
            continue
        events += 1
        print(f"t={n / fps:6.1f}s  ALERT person #{e.track_id} missing={e.missing} zone={e.zone}")
        if save:
            x1, y1, x2, y2 = (int(v) for v in e.box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 40, 230), 3)
            cv2.imwrite(f"{save}/alert_{n / fps:06.1f}_{e.track_id}.jpg", frame)
    n += 1
print(f"{n} frames, {events} incidents, {reminders} voice reminders, {len(ids)} person IDs, detection+logic {spent / n * 1000:.1f} ms/frame ({n / spent:.0f} FPS max) at imgsz {config.IMG_SIZE}")
