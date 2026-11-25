"""Keeps camera passwords and the Telegram token out of log output."""
import logging
import re
from urllib.parse import urlsplit

_URL = re.compile(r"\b(?:rtsps?|rtmp|https?)://[^\s\"'<>]+", re.IGNORECASE)
_BOT_TOKEN = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")


def safe_url(url: str) -> str:
    """Keep scheme, host, port and path; hide the user name, password and query string."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "***"
    host = parts.netloc.rpartition("@")[2]
    userinfo = "***@" if "@" in parts.netloc else ""
    query = "?***" if parts.query else ""
    return f"{parts.scheme}://{userinfo}{host}{parts.path}{query}"


def redact(text: str) -> str:
    # URLs first: a Telegram API URL carries the token in its path.
    return _BOT_TOKEN.sub("***", _URL.sub(lambda m: safe_url(m.group()), text))


def install() -> None:
    """Redact everything any logging formatter produces, including tracebacks."""
    original = logging.Formatter.format
    if getattr(original, "redacts", False):
        return

    def format(self, record):
        return redact(original(self, record))

    format.redacts = True
    logging.Formatter.format = format
