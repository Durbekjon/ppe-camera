"""YOLO wrapper that maps the model's class names onto the few roles this app cares about."""
import logging
import os
from dataclasses import dataclass

from ultralytics import YOLO

log = logging.getLogger("detector")

PERSON, HELMET, NO_HELMET, VEST, NO_VEST = "person", "helmet", "no_helmet", "vest", "no_vest"


def role_of(name: str):
    """Map a class name such as 'NO-Hardhat' or 'Hard_hat' to a role, or None if irrelevant."""
    n = name.lower().replace("_", "").replace("-", "").replace(" ", "")
    negative = n.startswith("no")
    if "helmet" in n or "hardhat" in n:
        return NO_HELMET if negative else HELMET
    if "vest" in n:
        return NO_VEST if negative else VEST
    if n in ("person", "worker"):
        return PERSON
    return None


@dataclass
class Detection:
    role: str
    conf: float
    box: tuple  # x1, y1, x2, y2 in frame pixels


class Detector:
    def __init__(self, model_path: str, imgsz: int, conf: float, gear_conf: float):
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        # Worn gear is accepted at a lower confidence than people or "no helmet": a missed
        # helmet causes a false alarm, so helmets get the benefit of the doubt.
        self.min_conf = {PERSON: conf, NO_HELMET: conf, NO_VEST: conf, HELMET: gear_conf, VEST: gear_conf}
        self.roles = {i: role_of(n) for i, n in self.model.names.items()}
        self.class_ids = [i for i, r in self.roles.items() if r]
        found = set(self.roles.values()) - {None}
        missing = {PERSON, HELMET, NO_HELMET} - found
        if missing:
            raise ValueError(f"Model {model_path} lacks required classes: {missing}")
        log.info("Model yuklandi: %s (sinflar: %s)", os.path.basename(model_path), ", ".join(sorted(found)))

    def detect(self, frame):
        result = self.model.predict(
            frame, imgsz=self.imgsz, conf=min(self.min_conf.values()), classes=self.class_ids, device="cpu", verbose=False
        )[0]
        boxes = result.boxes
        return [
            Detection(self.roles[int(c)], float(s), tuple(float(v) for v in xyxy))
            for c, s, xyxy in zip(boxes.cls, boxes.conf, boxes.xyxy)
            if float(s) >= self.min_conf[self.roles[int(c)]]
        ]
