"""Privacy for stored images: face blurring and deleting old snapshots.

Rule for every image of people that is written to disk or sent anywhere (including raw frames that a
future feature may keep): blur it with `anonymize` and let `delete_old_snapshots` expire it.
"""
import logging
import threading
import time
from datetime import datetime, timedelta

import cv2

from . import config

log = logging.getLogger("privacy")

FACE_MODEL = config.ROOT / "models" / "face_yunet_2023mar.onnx"
FACE_CONF = 0.5
# Where the head is assumed to be when no face was found on a person (fractions of the person box).
HEAD_HEIGHT, HEAD_WIDTH = 0.25, 0.8

_detector = None
_lock = threading.Lock()  # every camera uses the same face model


def find_faces(image):
    """Face boxes (x1, y1, x2, y2) found by YuNet."""
    global _detector
    with _lock:
        if _detector is None:
            _detector = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", (320, 320), FACE_CONF)
        _detector.setInputSize((image.shape[1], image.shape[0]))
        _, faces = _detector.detect(image)
    return [] if faces is None else [(f[0], f[1], f[0] + f[2], f[1] + f[3]) for f in faces]


def face_regions(image, person_boxes=()):
    """Areas to blur in a clean (not yet annotated) frame.

    Detected faces, plus the head area of every person on whom no face was found: the face model
    misses turned or poorly lit faces, and blurring too much is safer than too little.
    """
    faces = find_faces(image)
    regions = []
    for x1, y1, x2, y2 in faces:
        mx, my = 0.15 * (x2 - x1), 0.2 * (y2 - y1)
        regions.append((x1 - mx, y1 - my, x2 + mx, y2 + my))
    for x1, y1, x2, y2 in person_boxes:
        head_bottom = y1 + HEAD_HEIGHT * (y2 - y1)
        has_face = any(x1 <= (a + c) / 2 <= x2 and y1 <= (b + d) / 2 <= y1 + 0.5 * (y2 - y1) for a, b, c, d in faces)
        if not has_face:
            side = (1 - HEAD_WIDTH) / 2 * (x2 - x1)
            regions.append((x1 + side, y1, x2 - side, head_bottom))
    return regions


def pixelate(image, regions):
    """Return a copy with each region reduced to a few coarse blocks."""
    out = image.copy()
    h, w = out.shape[:2]
    for x1, y1, x2, y2 in regions:
        x1, y1, x2, y2 = max(0, int(x1)), max(0, int(y1)), min(w, int(x2 + 1)), min(h, int(y2 + 1))
        if x2 <= x1 or y2 <= y1:
            continue
        patch = out[y1:y2, x1:x2]
        blocks = (min(7, x2 - x1), min(7, y2 - y1))
        small = cv2.resize(patch, blocks, interpolation=cv2.INTER_AREA)
        out[y1:y2, x1:x2] = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
    return out


def anonymize(image, regions=None):
    """Blur `regions` (found in the image itself if None). Never returns an unprocessed image on failure."""
    if not config.BLUR_FACES:
        return image
    try:
        return pixelate(image, face_regions(image) if regions is None else regions)
    except Exception:
        log.exception("Yuzni xiralashtirib bo'lmadi; surat to'liq xiralashtirildi")
        h, w = image.shape[:2]
        return cv2.resize(cv2.resize(image, (24, 18), interpolation=cv2.INTER_AREA), (w, h))


def taken_at(path):
    """When a snapshot was taken: from its 'YYYYmmdd_HHMMSS_id.jpg' name, else the file time."""
    try:
        return datetime.strptime(path.name[:15], "%Y%m%d_%H%M%S")
    except ValueError:
        return datetime.fromtimestamp(path.stat().st_mtime)


def delete_old_snapshots(folder, days, now=None):
    """Delete .jpg files older than `days` (0 keeps everything). Return the deleted file names."""
    if days <= 0:
        return []
    limit = (now or datetime.now()) - timedelta(days=days)
    deleted = []
    for path in folder.glob("*.jpg"):
        try:
            if taken_at(path) < limit:
                path.unlink()
                deleted.append(path.name)
        except OSError:
            log.exception("Eski suratni o'chirib bo'lmadi: %s", path.name)
    if deleted:
        log.info("Saqlash muddati o'tgan %d ta surat o'chirildi", len(deleted))
    return deleted
