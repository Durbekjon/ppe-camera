"""Set test data aside before a demo, without deleting it.

Incidents, their pictures and the unsent Telegram queue move to data/archive/<time>/; users, zones and
settings stay. Archived pictures still expire with the normal retention period (see alerts.expire_snapshots).
"""
import shutil
import sqlite3
from datetime import datetime

from . import alerts, dataset, db

DB_NAME = "incidents.db"


def picture_folders():
    """{name inside an archive: the live folder}."""
    return {"snapshots": alerts.SNAPSHOTS, "raw": dataset.RAW, "exports": dataset.EXPORTS}


def summary():
    """What an archive would move right now."""
    count = lambda sql: db.query(sql)[0][0]  # noqa: E731
    files = {name: sum(1 for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else 0
             for name, folder in picture_folders().items()}
    return {"incidents": count("SELECT COUNT(*) FROM incidents"), "unsent": count("SELECT COUNT(*) FROM outbox"),
            "users": count("SELECT COUNT(*) FROM users"), **files}


def _move_contents(source, target):
    if not source.is_dir():
        return
    target.mkdir(parents=True, exist_ok=True)
    for item in list(source.iterdir()):
        if (target / item.name).exists():
            raise FileExistsError(f"Ustiga yozilmaydi: {target / item.name}")
        shutil.move(str(item), str(target / item.name))


def create(now=None):
    """Move the current incidents and pictures into a new archive folder. Returns it, or None if empty."""
    before = summary()
    if not any(before[k] for k in ("incidents", "unsent", *picture_folders())):
        return None
    folder = dataset.ARCHIVE / (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True)  # fails rather than mixing with an existing archive
    # 1. a complete copy of the database, checked before anything is removed
    copy = sqlite3.connect(folder / DB_NAME)
    with db._lock:
        db._conn.backup(copy)
    copy.execute("DELETE FROM users")  # no second copy of password hashes or sessions
    copy.execute("DELETE FROM sessions")
    copy.commit()
    saved = copy.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    copy.execute("VACUUM")
    copy.close()
    if saved != before["incidents"]:
        raise RuntimeError("Arxiv nusxasi to'liq emas; hech narsa o'chirilmadi")
    # 2. pictures
    for name, live in picture_folders().items():
        _move_contents(live, folder / name)
    # 3. only now empty the live tables; numbering starts again from 1
    db.execute("DELETE FROM incidents")
    db.execute("DELETE FROM outbox")
    db.execute("DELETE FROM sqlite_sequence WHERE name IN ('incidents', 'outbox')")
    return folder


def restore(name):
    """Bring an archive back. Only into an empty incident list, so numbers cannot collide."""
    folder = dataset.ARCHIVE / name
    if folder.parent != dataset.ARCHIVE or not (folder / DB_NAME).is_file():
        raise ValueError(f"Bunday arxiv yo'q: {name}")
    if summary()["incidents"]:
        raise ValueError("Hozir hodisalar bor. Avval ularni arxivlang, keyin eskisini qaytaring")
    for kind, live in picture_folders().items():
        _move_contents(folder / kind, live)
    old = sqlite3.connect(folder / DB_NAME)
    old.row_factory = sqlite3.Row
    rows = old.execute("SELECT * FROM incidents ORDER BY id").fetchall()
    old.close()
    live_columns = {r["name"] for r in db.query("PRAGMA table_info(incidents)")}
    for row in rows:
        values = {k: row[k] for k in row.keys() if k in live_columns}
        for field, kind in (("snapshot", "snapshots"), ("raw", "raw")):
            if values.get(field) and not (picture_folders()[kind] / values[field]).is_file():
                values[field] = ""  # expired while archived
        db.execute(f"INSERT INTO incidents ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
                   tuple(values.values()))
    # unsent alerts are old news and are not queued again; the archive folder is kept, marked as restored
    folder.rename(folder.with_name(folder.name + "_qaytarilgan"))
    return len(rows)
