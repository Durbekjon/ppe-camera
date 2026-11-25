"""Export incidents marked as false alarms (clean frames + what the model saw) for retraining.

Usage: .venv/bin/python -m tools.export_false_alarms
Writes to data/exports/<time>/. The images are blurred like all snapshots and expire with the same
retention period; if you copy them elsewhere, delete those copies yourself.
"""
from app import db, dataset

db.init()
folder, exported, skipped = dataset.export_false_alarms()
if folder is None:
    print(f"Eksport qilinadigan kadr yo'q (asl kadri yo'q belgilangan hodisalar: {skipped}).")
else:
    print(f"{exported} ta kadr eksport qilindi: {folder}")
    if skipped:
        print(f"{skipped} ta hodisaning asl kadri yo'q (eski yoki muddati o'tgan).")
