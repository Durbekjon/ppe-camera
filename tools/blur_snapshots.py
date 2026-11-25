"""Blur faces in snapshots saved before blurring existed. Changes the files in place (cannot be undone).

Usage: .venv/bin/python -m tools.blur_snapshots          (only counts)
       .venv/bin/python -m tools.blur_snapshots --apply
These old images have drawings on them and no person boxes, so only faces the model finds are blurred;
check the result, or delete the old snapshots instead.
"""
import sys

import cv2

from app import alerts, privacy

files = sorted(alerts.SNAPSHOTS.glob("*.jpg"))
apply = "--apply" in sys.argv[1:]
changed = unreadable = 0
for path in files:
    image = cv2.imread(str(path))
    if image is None:
        unreadable += 1
        continue
    regions = privacy.face_regions(image)
    if regions:
        changed += 1
        if apply:
            cv2.imwrite(str(path), privacy.pixelate(image, regions))
print(f"{len(files)} ta surat; {changed} tasida yuz topildi; o'qilmadi: {unreadable}.")
print("Xiralashtirildi." if apply else "Hech narsa o'zgartirilmadi. Qo'llash uchun: --apply")
