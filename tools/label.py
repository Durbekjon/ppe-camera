"""Draw boxes by hand on the frames of a test set made by tools/make_testset.py.

Usage: .venv/bin/python -m tools.label datasets/demo-room

Mouse: drag to draw a box of the current class.
Keys:  1 person · 2 helmet (worn) · 3 no_helmet (bare head or cap)
       Space/Enter: save and next · b: save and back · u: undo last box · c: clear frame · q: save and quit
Every visible person gets a person box; every head gets either helmet or no_helmet.
Label what you see, not what the model would say: the model's guesses are never shown.
"""
import sys
from pathlib import Path

import cv2

CLASSES = ["person", "helmet", "no_helmet"]
COLORS = [(230, 140, 40), (60, 190, 80), (60, 60, 230)]
WINDOW = "Belgilash"


def to_yolo(cls, box, w, h):
    x1, y1, x2, y2 = min(box[0], box[2]), min(box[1], box[3]), max(box[0], box[2]), max(box[1], box[3])
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    return f"{cls} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}"


def from_yolo(line, w, h):
    cls, cx, cy, bw, bh = line.split()
    cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
    return int(cls), (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)


def load(label, w, h):
    if not label.is_file():
        return []
    return [from_yolo(l, w, h) for l in label.read_text().splitlines() if l.strip()]


def save(label, boxes, w, h):
    label.parent.mkdir(parents=True, exist_ok=True)
    # tiny boxes from a mis-click are dropped
    lines = [to_yolo(c, b, w, h) for c, b in boxes if abs(b[2] - b[0]) >= 4 and abs(b[3] - b[1]) >= 4]
    label.write_text("".join(l + "\n" for l in lines))  # an empty file means "checked, nothing here"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1])
    images = sorted((root / "images" / "test").glob("*.jpg"))
    if not images:
        sys.exit(f"Kadr topilmadi: {root / 'images' / 'test'}")
    labels = root / "labels" / "test"
    state = {"cls": 0, "start": None, "now": None, "boxes": []}

    def on_mouse(event, x, y, flags, _):
        if event == cv2.EVENT_LBUTTONDOWN:
            state["start"] = state["now"] = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and state["start"]:
            state["now"] = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and state["start"]:
            (x1, y1), state["start"] = state["start"], None
            state["boxes"].append((state["cls"], (x1, y1, x, y)))

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)
    i = next((n for n, p in enumerate(images) if not (labels / (p.stem + ".txt")).exists()), 0)
    while 0 <= i < len(images):
        image = cv2.imread(str(images[i]))
        h, w = image.shape[:2]
        label = labels / (images[i].stem + ".txt")
        state["boxes"] = load(label, w, h)
        while True:
            view = image.copy()
            for c, (x1, y1, x2, y2) in state["boxes"]:
                cv2.rectangle(view, (int(x1), int(y1)), (int(x2), int(y2)), COLORS[c], 2)
                cv2.putText(view, CLASSES[c], (int(min(x1, x2)) + 3, int(min(y1, y2)) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[c], 2)
            if state["start"]:
                cv2.rectangle(view, state["start"], state["now"], COLORS[state["cls"]], 1)
            done = sum((labels / (p.stem + ".txt")).exists() for p in images)
            bar = f"{i + 1}/{len(images)}  belgilangan: {done}  sinf: {state['cls'] + 1} {CLASSES[state['cls']]}  [1-3 sinf, Space keyingi, b orqaga, u undo, q chiqish]"
            cv2.rectangle(view, (0, 0), (w, 24), (30, 30, 30), -1)
            cv2.putText(view, bar, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.imshow(WINDOW, view)
            key = cv2.waitKey(30) & 0xFF
            if key in (ord("1"), ord("2"), ord("3")):
                state["cls"] = key - ord("1")
            elif key == ord("u") and state["boxes"]:
                state["boxes"].pop()
            elif key == ord("c"):
                state["boxes"] = []
            elif key in (ord(" "), 13, ord("b"), ord("q")):
                save(label, state["boxes"], w, h)
                if key == ord("q"):
                    i = -1
                else:
                    i += -1 if key == ord("b") else 1
                break
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:  # window closed
                save(label, state["boxes"], w, h)
                i = -1
                break
    cv2.destroyAllWindows()
    done = sum((labels / (p.stem + ".txt")).exists() for p in images)
    print(f"Belgilangan: {done}/{len(images)}. O'lchash: .venv/bin/python -m tools.evaluate {root / 'data.yaml'}")


if __name__ == "__main__":
    main()
