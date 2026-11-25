"""SQLite incident log."""
import sqlite3
import threading

from . import config

_lock = threading.Lock()
_conn = None


def init(path=None):
    global _conn
    config.DATA.mkdir(exist_ok=True)
    _conn = sqlite3.connect(path or config.DATA / "incidents.db", check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(
        """CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,          -- local time, 'YYYY-MM-DD HH:MM:SS'
            missing TEXT NOT NULL,     -- 'helmet', 'vest' or 'helmet,vest'
            zone INTEGER NOT NULL,     -- 1 if inside the danger zone
            track_id INTEGER,
            snapshot TEXT
        )"""
    )
    _conn.commit()


def add_incident(ts, missing, zone, track_id, snapshot):
    with _lock:
        cur = _conn.execute(
            "INSERT INTO incidents (ts, missing, zone, track_id, snapshot) VALUES (?, ?, ?, ?, ?)",
            (ts, ",".join(missing), int(zone), track_id, snapshot),
        )
        _conn.commit()
        return cur.lastrowid


def list_incidents(limit=30):
    with _lock:
        rows = _conn.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def last_id():
    with _lock:
        return _conn.execute("SELECT COALESCE(MAX(id), 0) FROM incidents").fetchone()[0]


def report(date):
    """Counts for one day ('YYYY-MM-DD'): total, in-zone, and per hour."""
    with _lock:
        rows = _conn.execute(
            "SELECT CAST(substr(ts, 12, 2) AS INTEGER) AS hour, COUNT(*) AS n, SUM(zone) AS z "
            "FROM incidents WHERE substr(ts, 1, 10) = ? GROUP BY hour",
            (date,),
        ).fetchall()
    by_hour = [0] * 24
    for r in rows:
        by_hour[r["hour"]] = r["n"]
    return {"date": date, "total": sum(by_hour), "zone": sum(r["z"] for r in rows), "by_hour": by_hour}
