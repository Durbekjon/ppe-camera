"""Precision, recall and mAP50 of one or more models on a labelled test set.

Usage: .venv/bin/python -m tools.evaluate datasets/site/data.yaml [--split test] [--models a.pt b.pt] [--out report.md]
Without --models both bundled models are compared.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import cv2

from app import config, evaluate
from app.detector import HELMET, NO_HELMET, NO_VEST, PERSON, VEST, role_of

THRESHOLDS = {PERSON: config.CONF, NO_HELMET: config.CONF, NO_VEST: config.CONF,
              HELMET: config.GEAR_CONF, VEST: config.GEAR_CONF}


def predict(model_path, samples, imgsz):
    from ultralytics import YOLO

    model = YOLO(model_path)
    roles = {i: role_of(n) for i, n in model.names.items()}
    output = []
    for path, _ in samples:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Rasm o'qilmadi: {path}")
        h, w = image.shape[:2]
        if w > config.FRAME_WIDTH:  # the app downscales frames the same way
            image = cv2.resize(image, (config.FRAME_WIDTH, int(h * config.FRAME_WIDTH / w)))
        boxes = model.predict(image, imgsz=imgsz, conf=0.001, device="cpu", verbose=False)[0].boxes
        output.append([
            (roles[int(c)], float(s), tuple(float(v) for v in xyxyn))
            for c, s, xyxyn in zip(boxes.cls, boxes.conf, boxes.xyxyn) if roles[int(c)]
        ])
    return output


def percent(value):
    return "—" if value is None else f"{100 * value:.1f}%"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data", help="data.yaml (YOLO format)")
    parser.add_argument("--split", default="test")
    parser.add_argument("--models", nargs="+", default=[str(config.ROOT / "models" / n)
                                                        for n in ("ppe_yolov8s.pt", "ppe_yolov8n_alt.pt")])
    parser.add_argument("--imgsz", type=int, default=config.IMG_SIZE)
    parser.add_argument("--out", help="also write the report to this file")
    args = parser.parse_args()
    try:
        samples, unlabelled = evaluate.load_split(args.data, args.split)
        lines = [f"# Baholash natijasi ({date.today().isoformat()})", "",
                 f"To'plam: `{args.split}`, {len(samples)} ta rasm (belgi faylisiz: {unlabelled}); imgsz={args.imgsz}.",
                 f"Precision va recall ilova chegaralarida (CONF={config.CONF}, GEAR_CONF={config.GEAR_CONF}), IoU ≥ 0.5."]
        for model_path in args.models:
            predictions = predict(model_path, samples, args.imgsz)
            table = evaluate.score(samples, predictions, THRESHOLDS)
            aps = [row["ap50"] for row in table.values()]
            wrong, heads = evaluate.bare_heads_called_helmet(samples, predictions, THRESHOLDS)
            lines += ["", f"## {Path(model_path).name}", "", "| Sinf | Belgilar | Precision | Recall | AP50 |",
                      "|---|---|---|---|---|"]
            lines += [f"| {role} | {r['labels']} | {percent(r['precision'])} | {percent(r['recall'])} | {percent(r['ap50'])} |"
                      for role, r in table.items()]
            lines += ["", f"**mAP50** (belgilangan sinflar bo'yicha): {percent(sum(aps) / len(aps) if aps else None)}",
                      f"**Yalang bosh yoki kepka kaska deb olindi:** {wrong} / {heads}"
                      + (f" ({percent(wrong / heads)})" if heads else "")]
    except (ValueError, KeyError, OSError) as e:
        sys.exit(f"Xato: {e}")
    report = "\n".join(lines) + "\n"
    print(report)
    if args.out:
        Path(args.out).write_text(report)


if __name__ == "__main__":
    main()
