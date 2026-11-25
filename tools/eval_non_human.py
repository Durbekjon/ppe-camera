"""PPE-203: odam bo'lmagan obyektlardagi soxta signallarni o'lchash.

Har bir rasm kamerada bir necha soniya turgandek beriladi (debounce o'tishi uchun) va ikki xil ishonch
chegarasida yozilgan hodisalar sanaladi. Ikkala holatda ham debounce bir xil.
Rasmlar kod bilan chizilgan sodda namunalar: real plakat yoki maneken sinovining o'rnini bosmaydi.

Foydalanish: .venv/bin/python -m tools.eval_non_human            (repodagi rasmlarni o'lchaydi)
             .venv/bin/python -m tools.eval_non_human --generate (rasmlarni qayta chizadi)
"""
import os
import sys
from pathlib import Path

import cv2
import numpy as np

from app import config
from app.detector import HELMET, NO_HELMET, NO_VEST, PERSON, VEST, Detector, role_of

NON_HUMAN_DIR = Path("testdata/non_human")


def generate_test_cases():
    """Odam bo'lmagan 4 xil sinov tasvirini yaratadi."""
    NON_HUMAN_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Xavfsizlik plakati (Safety poster with helmet graphic)
    img1 = np.full((600, 800, 3), 245, dtype=np.uint8)
    cv2.rectangle(img1, (0, 0), (800, 100), (0, 215, 255), -1)
    cv2.putText(img1, "DIQQAT: XAVFLI ZONA", (150, 65), cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 0, 0), 3)
    cv2.circle(img1, (400, 300), 120, (200, 100, 0), -1)
    cv2.ellipse(img1, (400, 310), (90, 70), 0, 180, 360, (0, 220, 255), -1)
    cv2.rectangle(img1, (300, 305), (500, 325), (0, 220, 255), -1)
    cv2.putText(img1, "KASKASIZ KIRISH TAQIQLANADI", (100, 500), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 0, 200), 2)
    cv2.imwrite(str(NON_HUMAN_DIR / "poster_safety_helmet.jpg"), img1)

    # 2. Mashina va uskuna logotipi / ogohlantirish belgisi
    img2 = np.full((600, 800, 3), 220, dtype=np.uint8)
    pts = np.array([[400, 120], [220, 420], [580, 420]], np.int32)
    cv2.fillPoly(img2, [pts], (0, 200, 255))
    cv2.polylines(img2, [pts], True, (0, 0, 0), 10)
    cv2.rectangle(img2, (385, 200), (415, 320), (0, 0, 0), -1)
    cv2.circle(img2, (400, 370), 16, (0, 0, 0), -1)
    cv2.putText(img2, "KOMATSU INDUSTRIAL CORP", (120, 500), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(img2, "HEAVY MACHINERY KEEP OUT", (160, 550), cv2.FONT_HERSHEY_DUPLEX, 0.9, (50, 50, 50), 2)
    cv2.imwrite(str(NON_HUMAN_DIR / "logo_warning_sign.jpg"), img2)

    # 3. Shtativ / ilgichdagi maxsus kiyim va kaska (Mannequin/stand)
    img3 = np.full((600, 800, 3), 180, dtype=np.uint8)
    for y in range(0, 600, 40):
        cv2.line(img3, (0, y), (800, y), (160, 160, 160), 1)
    cv2.line(img3, (400, 300), (400, 580), (40, 40, 40), 12)
    cv2.line(img3, (400, 580), (300, 600), (40, 40, 40), 8)
    cv2.line(img3, (400, 580), (500, 600), (40, 40, 40), 8)
    vest_pts = np.array([[320, 220], [480, 220], [520, 420], [280, 420]], np.int32)
    cv2.fillPoly(img3, [vest_pts], (0, 230, 200))
    cv2.rectangle(img3, (310, 300), (490, 330), (220, 220, 220), -1)
    cv2.rectangle(img3, (300, 360), (500, 390), (220, 220, 220), -1)
    cv2.ellipse(img3, (400, 210), (70, 50), 0, 180, 360, (0, 255, 255), -1)
    cv2.rectangle(img3, (320, 205), (480, 220), (0, 255, 255), -1)
    cv2.imwrite(str(NON_HUMAN_DIR / "jacket_stand_dummy.jpg"), img3)

    # 4. Plakatdagi odam silueti va banner
    img4 = np.full((600, 800, 3), 250, dtype=np.uint8)
    cv2.putText(img4, "MEHNAT MUHOFAZASI", (180, 80), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 180), 2)
    cv2.circle(img4, (400, 200), 45, (80, 80, 80), -1)
    cv2.ellipse(img4, (400, 350), (100, 120), 0, 0, 360, (80, 80, 80), -1)
    cv2.rectangle(img4, (330, 400), (470, 550), (80, 80, 80), -1)
    cv2.putText(img4, "XAVFSIZLIK QOIDALARIGA AMAL QILING", (90, 570), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 0, 0), 2)
    cv2.imwrite(str(NON_HUMAN_DIR / "poster_silhouette.jpg"), img4)


SECONDS, FPS = 3.0, 30
SETTINGS = (("past chegara", 0.20, 0.20), ("joriy chegara", config.CONF, config.GEAR_CONF))


def incidents_over_time(detections, frame_size, conf, seconds=SECONDS, fps=FPS):
    """Incidents the app would record if the same detections stayed in view for `seconds`."""
    from app.violations import ViolationEngine

    engine = ViolationEngine(debounce=config.DEBOUNCE_S, person_conf=conf)
    total = 0
    for i in range(int(seconds * fps)):
        _, events = engine.update(detections, i / fps, frame_size)
        total += sum(e.record for e in events)
    return total


def evaluate_model(model_path):
    """Return {setting name: {"detections": n, "incidents": n, "images": {name: (labels, incidents)}}}."""
    images = sorted(NON_HUMAN_DIR.glob("*.jpg"))
    if not images:
        raise FileNotFoundError(f"Rasm topilmadi: {NON_HUMAN_DIR}")
    results = {}
    for label, conf, gear_conf in SETTINGS:
        detector = Detector(model_path, imgsz=config.IMG_SIZE, conf=conf, gear_conf=gear_conf)
        row = {"conf": conf, "gear_conf": gear_conf, "detections": 0, "incidents": 0, "images": {}}
        for path in images:
            frame = cv2.imread(str(path))
            found = detector.detect(frame)
            count = incidents_over_time(found, (frame.shape[1], frame.shape[0]), conf)
            row["detections"] += len(found)
            row["incidents"] += count
            row["images"][path.name] = ([f"{d.role}:{d.conf:.2f}" for d in found], count)
        results[label] = row
    return results


def main():
    if "--generate" in sys.argv[1:]:
        generate_test_cases()
    for model_path in ("models/ppe_yolov8s.pt", "models/ppe_yolov8n_alt.pt"):
        if not os.path.exists(model_path):
            continue
        print(f"\n== {Path(model_path).name} (har rasm {SECONDS:.0f} s, {FPS} FPS, debounce {config.DEBOUNCE_S} s)")
        for label, row in evaluate_model(model_path).items():
            print(f"-- {label}: CONF={row['conf']}, GEAR_CONF={row['gear_conf']}")
            for name, (found, count) in row["images"].items():
                print(f"   {name:28s} hodisa={count}  {found}")
            print(f"   JAMI: topilgan obyekt={row['detections']}, yozilgan hodisa={row['incidents']}")


if __name__ == "__main__":
    main()
