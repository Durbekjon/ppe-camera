"""Export of incidents marked as false alarms."""
import json
import shutil
from datetime import datetime

from . import config, db

RAW = config.DATA / "raw"  # clean (blurred, undrawn) frames, one per incident
EXPORTS = config.DATA / "exports"
ARCHIVE = config.DATA / "archive"  # test data set aside before a demo, see archive.py


def export_false_alarms():
    """Return (folder or None, exported count, count without a stored frame)."""
    rows = db.query("SELECT * FROM incidents WHERE false_alarm = 1 ORDER BY id")
    found = [r for r in rows if r["raw"] and (RAW / r["raw"]).is_file()]
    if not found:
        return None, 0, len(rows)
    folder = EXPORTS / datetime.now().strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    labels = []
    for r in found:
        shutil.copyfile(RAW / r["raw"], folder / r["raw"])
        # "detections" is what the model claimed; it is a starting point for labelling, not ground truth.
        labels.append({"image": r["raw"], "incident": r["id"], "camera": r["camera"], "time": r["ts"], "reported": r["missing"].split(","),
                       "detections": json.loads(r["detections"] or "[]")})
    (folder / "labels.json").write_text(json.dumps(labels, indent=1))
    return folder, len(found), len(rows) - len(found)
