"""Users, passwords and server-side sessions (standard library only).

Roles: "admin" can change things (zone, demo mode, Telegram test); "supervisor" can only watch.
"""
import hashlib
import hmac
import secrets
import time

from . import db

ADMIN, SUPERVISOR = "admin", "supervisor"
ROLES = (ADMIN, SUPERVISOR)
MIN_PASSWORD = 8
SESSION_S = 12 * 3600
MAX_FAILURES, LOCK_S = 5, 60  # per user name

_failures = {}  # username -> (count, time of last failure)


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def _token_key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()  # a leaked database holds no usable cookies


def set_user(username: str, password: str, role: str) -> None:
    """Create a user, or reset the password and role of an existing one (ends their sessions)."""
    username = username.strip().lower()
    if not username or role not in ROLES:
        raise ValueError("Login bo'sh yoki rol noto'g'ri")
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"Parol kamida {MIN_PASSWORD} ta belgi bo'lsin")
    salt = secrets.token_bytes(16)
    db.execute(
        "INSERT OR REPLACE INTO users (username, role, salt, hash) VALUES (?, ?, ?, ?)",
        (username, role, salt, _hash(password, salt)),
    )
    db.execute("DELETE FROM sessions WHERE username = ?", (username,))


def has_users() -> bool:
    return bool(db.query("SELECT 1 FROM users LIMIT 1"))


def is_locked(username: str) -> bool:
    count, last = _failures.get(username.strip().lower(), (0, 0))
    return count >= MAX_FAILURES and time.time() - last < LOCK_S


def login(username: str, password: str):
    """Return a new session token, or None if the name or password is wrong."""
    username = username.strip().lower()
    rows = db.query("SELECT salt, hash FROM users WHERE username = ?", (username,))
    # Hash even for unknown names so response time does not reveal which names exist.
    salt, expected = (rows[0]["salt"], rows[0]["hash"]) if rows else (b"x" * 16, b"")
    if not hmac.compare_digest(_hash(password, salt), expected):
        count, last = _failures.get(username, (0, 0))
        _failures[username] = ((count if time.time() - last < LOCK_S else 0) + 1, time.time())
        return None
    _failures.pop(username, None)
    token = secrets.token_urlsafe(32)
    db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
    db.execute("INSERT INTO sessions (token, username, expires) VALUES (?, ?, ?)",
               (_token_key(token), username, time.time() + SESSION_S))
    return token


def user_for(token):
    """Return {"username", "role"} for a valid session token, else None."""
    if not token:
        return None
    rows = db.query(
        "SELECT u.username, u.role FROM sessions s JOIN users u USING (username) WHERE s.token = ? AND s.expires > ?",
        (_token_key(token), time.time()),
    )
    return dict(rows[0]) if rows else None


def logout(token) -> None:
    if token:
        db.execute("DELETE FROM sessions WHERE token = ?", (_token_key(token),))
