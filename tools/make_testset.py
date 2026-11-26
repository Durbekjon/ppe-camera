"""Cut a short video into a small labelled-test-set folder for tools/label.py and tools/evaluate.py.

Usage: .venv/bin/python -m tools.make_testset video.mp4 [--name demo-room] [--every 1.0]
       .venv/bin/python -m tools.make_testset 0 [--seconds 120]   # record straight from webcam 0

Writes datasets/<name>/images/test/*.jpg, an empty labels/test/ and data.yaml. datasets/ is ignored by git:
the pictures show people, so record only people who agreed and never commit or share them.
Frames that barely differ from the previous kept one are skipped, so a still scene does not count many times.
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np

from app import config

CLASSES = ["person", "helmet", "no_helmet"]
MIN_CHANGE = 6.0  # mean grey-level difference (0-255) on a small copy


def extract(video, out_dir, every_s=1.0, width=None):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise SystemExit(f"Video ochilmadi: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    step = max(1, round(fps * every_s))
    width = width or config.FRAME_WIDTH
    out_dir.mkdir(parents=True, exist_ok=True)
    kept, last, index = 0, None, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % step == 0:
            frame, small = _keep(frame, width, last)
            if small is not None:
                cv2.imwrite(str(out_dir / f"{Path(video).stem}_{index:06d}.jpg"), frame)
                kept, last = kept + 1, small
        index += 1
    return kept


def _keep(frame, width, last):
    """Resize the frame; return (frame, small) if it differs enough from `last`, else (frame, None)."""
    h, w = frame.shape[:2]
    if w > width:
        frame = cv2.resize(frame, (width, int(h * width / w)))
    small = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    if last is None or float(np.abs(small - last).mean()) >= MIN_CHANGE:
        return frame, small
    return frame, None


def capture(camera, out_dir, seconds=120, every_s=1.0, width=None):
    """Record straight from a webcam: one frame every `every_s` seconds, for `seconds` or until q."""
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        raise SystemExit(f"Kamera ochilmadi: {camera} (macOS: Terminal'ga kamera ruxsatini bering)")
    width = width or config.FRAME_WIDTH
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    kept, last, start, next_at = 0, None, None, None
    last_ok = time.monotonic()
    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            # macOS webcams return empty reads while warming up: give the camera a few seconds.
            if time.monotonic() - last_ok > 8:
                print("Kameradan kadr kelmadi. Boshqa dastur (masalan ./run.sh) kamerani band qilmaganini "
                      "va Terminal'ga kamera ruxsati berilganini tekshiring.")
                break
            time.sleep(0.05)
            continue
        last_ok = now = time.monotonic()
        if start is None:  # count down from the first real frame, not from opening the camera
            start, next_at = now, now + 3  # 3 s to get ready
        if now >= start + 3 + seconds:
            break
        if now >= next_at:
            next_at = now + every_s
            frame, small = _keep(frame, width, last)
            if small is not None:
                cv2.imwrite(str(out_dir / f"cam_{stamp}_{kept:04d}.jpg"), frame)
                kept, last = kept + 1, small
        view = frame.copy()
        left = max(0, int(start + 3 + seconds - now))
        msg = "Tayyorlaning..." if now < start + 3 else f"Yozilmoqda: {kept} kadr, {left} s qoldi (q - to'xtatish)"
        cv2.putText(view, msg, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow("make_testset", view)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
    return kept


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("video", help="video file, or a camera number (0 = built-in webcam)")
    p.add_argument("--name", default="demo-room")
    p.add_argument("--every", type=float, default=1.0, help="seconds between frames")
    p.add_argument("--seconds", type=int, default=120, help="camera only: how long to record")
    a = p.parse_args()
    root = config.ROOT / "datasets" / a.name
    if a.video.isdigit():
        n = capture(int(a.video), root / "images" / "test", a.seconds, a.every)
    else:
        if not Path(a.video).exists():
            raise SystemExit(f"Fayl topilmadi: {a.video}\n"
                             "Webkameradan to'g'ridan-to'g'ri yozish uchun: .venv/bin/python -m tools.make_testset 0")
        n = extract(a.video, root / "images" / "test", a.every)
    (root / "labels" / "test").mkdir(parents=True, exist_ok=True)
    (root / "data.yaml").write_text("path: .\ntest: images/test\nnames: [" + ", ".join(CLASSES) + "]\n")
    print(f"{n} ta kadr: {root / 'images' / 'test'}")
    print(f"Endi belgilang: .venv/bin/python -m tools.label {root}")
    print(f"Keyin o'lchang: .venv/bin/python -m tools.evaluate {root / 'data.yaml'}")


if __name__ == "__main__":
    main()
