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
    columns = {r["name"] for r in _conn.execute("PRAGMA table_info(incidents)")}
    for name, definition in (
        ("zone_name", "TEXT NOT NULL DEFAULT ''"),
        ("camera", "TEXT NOT NULL DEFAULT ''"),
        ("false_alarm", "INTEGER NOT NULL DEFAULT 0"),
        ("raw", "TEXT NOT NULL DEFAULT ''"),  # clean frame file name, for retraining
        ("detections", "TEXT NOT NULL DEFAULT ''"),  # JSON: what the model saw in that frame
        ("status", "TEXT NOT NULL DEFAULT 'yangi'"),  # 'yangi', 'ko''rildi', 'hal_qilindi'
    ):
        if name not in columns:
            _conn.execute(f"ALTER TABLE incidents ADD COLUMN {name} {definition}")  # keeps old rows
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, role TEXT NOT NULL, salt BLOB NOT NULL, hash BLOB NOT NULL)"
    )
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL)"
    )
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, urgent INTEGER NOT NULL, "
        "caption TEXT NOT NULL, photo TEXT NOT NULL, line TEXT NOT NULL, created REAL NOT NULL, "
        "next_try REAL NOT NULL, attempts INTEGER NOT NULL)"
    )
    _conn.commit()


def execute(sql, params=()):
    with _lock:
        _conn.execute(sql, params)
        _conn.commit()


def query(sql, params=()):
    with _lock:
        return _conn.execute(sql, params).fetchall()


def add_incident(ts, missing, zone, track_id, snapshot, zone_name="", raw="", detections="", camera=""):
    with _lock:
        cur = _conn.execute(
            "INSERT INTO incidents (ts, missing, zone, track_id, snapshot, zone_name, raw, detections, camera) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, ",".join(missing), int(zone), track_id, snapshot, zone_name, raw, detections, camera),
        )
        _conn.commit()
        return cur.lastrowid


STATUSES = ("yangi", "ko'rildi", "hal_qilindi")
STATUS_ALIASES = {
    "yangi": "yangi",
    "new": "yangi",
    "ko'rildi": "ko'rildi",
    "korildi": "ko'rildi",
    "reviewed": "ko'rildi",
    "hal_qilindi": "hal_qilindi",
    "resolved": "hal_qilindi",
}


def list_incidents(limit=30, status="", date="", missing="", zone="", camera="", zone_name=""):
    clauses, params = [], []
    if status:
        st = STATUS_ALIASES.get(status.lower().strip(), status)
        clauses.append("status = ?")
        params.append(st)
    if date:
        clauses.append("substr(ts, 1, 10) = ?")
        params.append(date)
    if missing:
        clauses.append("missing LIKE ?")
        params.append(f"%{missing}%")
    if zone != "":
        if str(zone).lower() in ("1", "true"):
            clauses.append("zone = 1")
        elif str(zone).lower() in ("0", "false"):
            clauses.append("zone = 0")
        else:
            clauses.append("zone_name = ?")
            params.append(zone)
    if zone_name:
        clauses.append("zone_name = ?")
        params.append(zone_name)
    if camera:
        clauses.append("camera = ?")
        params.append(camera)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = (
        f"SELECT id, ts, missing, zone, track_id, snapshot, zone_name, false_alarm, camera, status "
        f"FROM incidents {where} ORDER BY id DESC LIMIT ?"
    )
    params.append(limit)
    with _lock:
        rows = _conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def zone_names():
    """Zone names that appear in the incident log, including zones deleted since."""
    return [r["zone_name"] for r in query("SELECT DISTINCT zone_name FROM incidents WHERE zone_name <> '' ORDER BY zone_name")]


def set_status(incident_id, status):
    """Update incident status ('yangi', 'ko''rildi', 'hal_qilindi'). Returns False if invalid or not found."""
    status_clean = STATUS_ALIASES.get(str(status).lower().strip())
    if not status_clean:
        return False
    with _lock:
        cur = _conn.execute("UPDATE incidents SET status = ? WHERE id = ?", (status_clean, incident_id))
        _conn.commit()
        return cur.rowcount == 1


def set_false_alarm(incident_id, value):
    """Mark or unmark; return False if there is no such incident."""
    with _lock:
        cur = _conn.execute("UPDATE incidents SET false_alarm = ? WHERE id = ?", (int(value), incident_id))
        _conn.commit()
        return cur.rowcount == 1


def last_id():
    with _lock:
        return _conn.execute("SELECT COALESCE(MAX(id), 0) FROM incidents").fetchone()[0]


def report(date):
    """Counts for one day ('YYYY-MM-DD'): total, in-zone, and per hour."""
    with _lock:
        rows = _conn.execute(
            "SELECT CAST(substr(ts, 12, 2) AS INTEGER) AS hour, COUNT(*) AS n, SUM(zone) AS z "
            "FROM incidents WHERE substr(ts, 1, 10) = ? AND false_alarm = 0 GROUP BY hour",
            (date,),
        ).fetchall()
    by_hour = [0] * 24
    for r in rows:
        by_hour[r["hour"]] = r["n"]
    return {"date": date, "total": sum(by_hour), "zone": sum(r["z"] for r in rows), "by_hour": by_hour}
