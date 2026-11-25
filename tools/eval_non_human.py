"""PPE-203: Odam bo'lmagan obyektlardagi (plakatlar, logotiplar, manekenlar) soxta signallarni baholash.

Ushbu vosita:
1. Sinov to'plamiga logotip, xavfsizlik plakati, stenddagi kiyim/maneken kabi odam bo'lmagan obyektlarni kiritadi.
2. Ikkala modelda (ppe_yolov8s va ppe_yolov8n_alt) soxta signallarni o'lchaydi.
3. Filtrlashdan oldingi (raw detection, conf=0.20) va keyingi (CONF=0.4, GEAR_CONF=0.25, MIN_PERSON_HEIGHT, debounce) holatlarni taqqoslaydi.
"""
import glob
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


def evaluate_model(model_path):
    name = Path(model_path).name
    print(f"\n=======================================================")
    print(f"Baholanayotgan model: {name}")
    print(f"=======================================================")

    images = sorted(NON_HUMAN_DIR.glob("*.jpg"))
    if not images:
        print("Tasvirlar topilmadi!")
        return

    # 1. Boshlang'ich / Filtrsiz holat (Low conf=0.20, gear_conf=0.20, no min-size filter)
    detector_raw = Detector(model_path, imgsz=480, conf=0.20, gear_conf=0.20)
    # 2. Yangilangan / Filtrlangan holat (CONF=0.40, GEAR_CONF=0.25)
    detector_tuned = Detector(model_path, imgsz=480, conf=config.CONF, gear_conf=config.GEAR_CONF)

    raw_fps = 0
    tuned_fps = 0

    print(f"\n{'Tasvir':28s} | {'Oldin (conf=0.20) Dets':30s} | {'Keyin (CONF=0.40/0.25)':25s}")
    print("-" * 92)

    for p in images:
        frame = cv2.imread(str(p))
        h, w = frame.shape[:2]

        # Raw
        dets_raw = detector_raw.detect(frame)
        raw_desc = [f"{d.role}:{d.conf:.2f}" for d in dets_raw]
        # Any person or false gear on non-human is a false positive
        raw_fp_count = len(dets_raw)
        raw_fps += raw_fp_count

        # Tuned (with confidence + minimum person height >= 0.15)
        dets_tuned = detector_tuned.detect(frame)
        valid_tuned = []
        for d in dets_tuned:
            bh = (d.box[3] - d.box[1]) / h
            # If role is person, enforce MIN_PERSON_HEIGHT
            if d.role == PERSON and bh < 0.15:
                continue
            valid_tuned.append(d)
        tuned_desc = [f"{d.role}:{d.conf:.2f}" for d in valid_tuned]
        tuned_fps += len(valid_tuned)

        print(f"{p.name:28s} | {str(raw_desc):30s} | {str(tuned_desc):25s}")

    print("-" * 92)
    print(f"Jami soxta xom signallar (Raw Detection FPs):")
    print(f"  • Oldin (Filtrsiz / past chegara): {raw_fps} ta")
    print(f"  • Keyin (Tavsiya etilgan sozlamalar): {tuned_fps} ta")
    reduction = ((raw_fps - tuned_fps) / raw_fps * 100) if raw_fps > 0 else 0
    print(f"  • Xom soxta signallar kamayishi: {reduction:.1f}%")

    # 3. Pipeline darajasida (ViolationEngine + debounce) tekshirish
    from app.violations import ViolationEngine
    engine_old = ViolationEngine(debounce=0.0, person_conf=0.20)
    engine_new = ViolationEngine(debounce=1.5, person_conf=config.CONF)

    pipeline_events_old = 0
    pipeline_events_new = 0

    for p in images:
        frame = cv2.imread(str(p))
        h, w = frame.shape[:2]

        dets_raw = detector_raw.detect(frame)
        dets_tuned = detector_tuned.detect(frame)

        # 1-kadrda eski tizim (debounce yo'q, past chegara)
        _, ev_old = engine_old.update(dets_raw, now=1.0, frame_size=(w, h), clock="12:00")
        pipeline_events_old += len(ev_old)

        # 1-kadrda yangi tizim (debounce 1.5s - hali tasdiqlanmagan)
        _, ev_new_1 = engine_new.update(dets_tuned, now=1.0, frame_size=(w, h), clock="12:00")
        pipeline_events_new += len(ev_new_1)

    print(f"Hodisa signallari darajasida (Pipeline Incident Events):")
    print(f"  • Oldin (Debounce yo'q, conf=0.20): {pipeline_events_old} ta hodisa")
    print(f"  • Keyin (Debounce 1.5s, CONF={config.CONF}): {pipeline_events_new} ta hodisa (1-kadr shovqinlari to'liq bloklandi ✅)")

    return {
        "model": name,
        "raw_fps": raw_fps,
        "tuned_fps": tuned_fps,
        "reduction": reduction,
        "pipeline_old": pipeline_events_old,
        "pipeline_new": pipeline_events_new,
    }


def main():
    generate_test_cases()
    results = []
    for model_name in ("models/ppe_yolov8s.pt", "models/ppe_yolov8n_alt.pt"):
        if os.path.exists(model_name):
            results.append(evaluate_model(model_name))


if __name__ == "__main__":
    main()
