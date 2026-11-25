import logging
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app import config, main
from app.redact import redact, safe_url
from app.video import VideoSource


@pytest.mark.parametrize("url", [
    "rtsp://admin:SECRET@10.0.0.5:554/stream",
    "rtsp://admin:SE@CRET@10.0.0.5/stream",
    "http://10.0.0.5:8080/video?user=admin&password=SECRET",
])
def test_camera_password_is_hidden(url):
    for text in (safe_url(url), VideoSource(url).label, redact(f"failed to open '{url}' twice")):
        assert "SECRET" not in text and "CRET" not in text and "10.0.0.5" in text


def test_log_output_and_tracebacks_are_redacted():
    token = "123456789:" + "A" * 35
    try:
        raise ConnectionError(f"https://api.telegram.org/bot{token}/sendMessage")
    except ConnectionError:
        record = logging.LogRecord("x", logging.ERROR, "f", 1, "token %s", (token,), sys.exc_info())
    text = logging.Formatter().format(record)
    assert token not in text and "***" in text


@pytest.mark.parametrize("url", [
    "rtsp://admin:SECRET@127.0.0.1:9/stream",
    "http://127.0.0.1:9/video?password=SECRET",
])
def test_opencv_does_not_print_the_password(url):
    # A child process, because OpenCV writes to the terminal directly, bypassing Python.
    code = ("import sys, time; from app.video import VideoSource\n"
            "v = VideoSource(sys.argv[1]); v.start(); time.sleep(1.5); v.stop()")
    done = subprocess.run([sys.executable, "-c", code, url], cwd=config.ROOT, capture_output=True, text=True, timeout=60)
    output = done.stdout + done.stderr
    assert done.returncode == 0 and "SECRET" not in output, output


@pytest.mark.parametrize("base, host, expected", [
    ("http://x", "192.168.1.7", 403),
    ("https://x", "192.168.1.7", 200),
    ("http://x", "127.0.0.1", 200),
])
def test_network_clients_need_https(base, host, expected):
    client = TestClient(main.app, base_url=base, client=(host, 5000))
    assert client.get("/login").status_code == expected


def test_x_forwarded_proto_does_not_bypass_https():
    client = TestClient(main.app, base_url="http://x", client=("192.168.1.7", 5000))
    # An attacker must not bypass HTTPS enforcement simply by spoofing X-Forwarded-Proto
    r = client.get("/login", headers={"X-Forwarded-Proto": "https"})
    assert r.status_code == 403
    assert r.json() == {"detail": "Tarmoq orqali faqat HTTPS bilan kiring"}

    r = client.post("/api/login", json={"username": "admin", "password": "password"},
                    headers={"X-Forwarded-Proto": "https"})
    assert r.status_code == 403
    assert r.json() == {"detail": "Tarmoq orqali faqat HTTPS bilan kiring"}
