"""Print helmet / no-helmet / person confidences per test image for several models and input sizes."""
import glob, os, sys
import cv2
from ultralytics import YOLO
from app.detector import role_of

for path in sys.argv[1:]:
    m = YOLO(path)
    for sz in (480, 640):
        print(f"\n== {os.path.basename(path)} imgsz={sz}")
        for p in sorted(glob.glob("testdata/images/*.jpg")):
            img = cv2.imread(p)
            img = cv2.resize(img, (960, int(img.shape[0] * 960 / img.shape[1])))
            r = m.predict(img, imgsz=sz, conf=0.15, device="cpu", verbose=False)[0]
            by = {}
            for c, s in zip(r.boxes.cls, r.boxes.conf):
                role = role_of(m.names[int(c)])
                if role in ("person", "helmet", "no_helmet"):
                    by.setdefault(role, []).append(round(float(s), 2))
            print(f"  {os.path.basename(p):28s}", {k: sorted(v, reverse=True) for k, v in sorted(by.items())})
