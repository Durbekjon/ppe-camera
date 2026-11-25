"""Run candidate models on test images: print detections, time CPU inference, save annotated copies."""
import glob, os, sys, time
import cv2
from ultralytics import YOLO

out = "testdata/out"; os.makedirs(out, exist_ok=True)
imgs = sorted(glob.glob("testdata/images/*.jpg"))
for tag in sys.argv[1:]:
    m = YOLO(f"models/{tag}/best.pt")
    print(f"\n=== {tag} classes: {m.names}")
    for sz in (640, 480, 416):
        frame = cv2.imread(imgs[0])
        m.predict(frame, imgsz=sz, device="cpu", verbose=False)
        t = time.perf_counter()
        for _ in range(20):
            m.predict(frame, imgsz=sz, device="cpu", verbose=False)
        print(f"imgsz {sz}: {(time.perf_counter()-t)/20*1000:.1f} ms/frame on CPU")
    for p in imgs:
        r = m.predict(cv2.imread(p), imgsz=640, conf=0.3, device="cpu", verbose=False)[0]
        dets = sorted((m.names[int(c)], round(float(s), 2)) for c, s in zip(r.boxes.cls, r.boxes.conf))
        print(os.path.basename(p), dets)
        cv2.imwrite(f"{out}/{tag}_{os.path.basename(p)}", r.plot())
