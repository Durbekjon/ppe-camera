import time
import numpy as np
from app.video import VideoSource, parse_source


def test_parse_source():
    assert parse_source("0") == 0
    assert parse_source("1") == 1
    assert parse_source("http://192.168.1.5:8080/video") == "http://192.168.1.5:8080/video"
    assert parse_source("data/test.mp4") == "data/test.mp4"


def test_label_masks_credentials():
    vs = VideoSource("rtsp://admin:secret123@192.168.1.100:554/stream")
    assert "secret123" not in vs.label
    assert "admin" not in vs.label
    assert vs.label == "rtsp://***@192.168.1.100:554/stream"


def test_video_source_file_playback():
    vs = VideoSource("testdata/stills.mp4", width=480)
    vs.start()
    try:
        # Wait up to 3s for first frame
        for _ in range(30):
            seq, frame = vs.read()
            if frame is not None and vs.connected:
                break
            time.sleep(0.1)
        assert vs.connected
        assert frame is not None
        assert frame.shape[1] <= 480
        assert seq > 0
    finally:
        vs.stop()
        assert not vs.connected


def test_video_source_reconnect_on_invalid_stream(monkeypatch):
    # Tests that invalid stream handles disconnection without crashing
    vs = VideoSource("http://127.0.0.1:9999/nonexistent")
    vs.start()
    try:
        time.sleep(0.5)
        assert not vs.connected
        seq, frame = vs.read()
        assert frame is None
    finally:
        vs.stop()
