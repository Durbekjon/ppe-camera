"""Background loop: newest frame -> detection -> annotated JPEG for the dashboard."""
import logging
import threading
import time

import cv2

import json
import os

import numpy as np

from . import config
from .alerts import AlertManager, describe
from .detector import HELMET, VEST, Detector
from .video import VideoSource
from .violations import ViolationEngine

log = logging.getLogger("pipeline")

GREEN, AMBER, RED, WHITE = (80, 200, 60), (40, 170, 250), (40, 40, 230), (255, 255, 255)
ZONE_FILE = config.DATA / "zone.json"


def draw_box(frame, box, color, label, thickness=2):
    x1, y1, x2, y2 = (int(v) for v in box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y = max(y1, th + 6)
    cv2.rectangle(frame, (x1, y - th - 6), (x1 + tw + 6, y), color, -1)
    cv2.putText(frame, label, (x1 + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


class Pipeline:
    def __init__(self):
        self.demo = config.DEMO_MODE
        self.video = VideoSource(self._source(), config.FRAME_WIDTH)
        self.detector = Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF)
        self.engine = ViolationEngine(config.DEBOUNCE_S, config.COOLDOWN_S, config.REQUIRE_VEST, config.HELMET_RULE, config.CONF)
        self.alerts = AlertManager()
        self.state = {"status": "safe", "people": 0, "violators": 0}
        if ZONE_FILE.exists():
            self.engine.zone = [tuple(p) for p in json.loads(ZONE_FILE.read_text())]
        self.fps = 0.0
        self.jpeg = None
        self.jpeg_seq = 0
        self.frame_size = (0, 0)
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="pipeline")

    def start(self):
        self.video.start()
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        self._thread.join(timeout=3)
        self.video.stop()

    @property
    def stopped(self):
        return self._stop.is_set()

    def wait_jpeg(self, last_seq, timeout=1.0):
        """Block until a JPEG newer than last_seq exists; return (seq, jpeg bytes or None)."""
        with self._cond:
            self._cond.wait_for(lambda: self.jpeg_seq != last_seq or self.stopped, timeout)
            return self.jpeg_seq, self.jpeg

    def _source(self):
        return config.DEMO_VIDEO if self.demo else config.VIDEO_SOURCE

    def set_demo(self, on: bool):
        """Switch between the live source and the offline demo video at runtime."""
        if on and not os.path.exists(config.DEMO_VIDEO):
            raise FileNotFoundError(config.DEMO_VIDEO)
        old, self.demo = self.video, on
        self.video = VideoSource(self._source(), config.FRAME_WIDTH)
        self.video.start()
        old.stop()
        self.engine.reset()
        log.info("Demo rejimi: %s (manba: %s)", "yoqildi" if on else "o'chirildi", self.video.label)

    def set_zone(self, points):
        # Corners clicked within 4% of the frame border snap to the border, so a zone drawn
        # "to the edge" also contains people whose feet are cut off by the frame.
        def snap(v):
            return 0.0 if v < 0.04 else 1.0 if v > 0.96 else float(v)

        self.engine.zone = [(snap(x), snap(y)) for x, y in points]
        ZONE_FILE.parent.mkdir(exist_ok=True)
        ZONE_FILE.write_text(json.dumps(self.engine.zone))
        log.info("Xavfli zona %s", f"saqlandi ({len(points)} nuqta)" if points else "o'chirildi")

    def process(self, frame, now):
        """Detect, update violation state, annotate the frame in place and raise alerts."""
        h, w = frame.shape[:2]
        detections = self.detector.detect(frame)
        people, events = self.engine.update(detections, now, (w, h))
        zone_alarm = any(t.confirmed and t.in_zone for t in people)

        if len(self.engine.zone) >= 3:
            pts = np.array([(int(x * w), int(y * h)) for x, y in self.engine.zone], np.int32)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], RED)
            cv2.addWeighted(overlay, 0.35 if zone_alarm else 0.15, frame, 0.65 if zone_alarm else 0.85, 0, frame)
            cv2.polylines(frame, [pts], True, RED, 2, cv2.LINE_AA)
        for d in detections:
            if d.role in (HELMET, VEST):
                x1, y1, x2, y2 = (int(v) for v in d.box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), GREEN, 1)
        for t in people:
            if not t.missing and t.violating_since is None:
                draw_box(frame, t.box, GREEN, f"#{t.id} xavfsiz")
            else:
                color = RED if t.confirmed else AMBER
                draw_box(frame, t.box, color, f"#{t.id} {describe(t.missing) or '...'}", 3 if t.confirmed else 2)
        if zone_alarm:
            cv2.rectangle(frame, (0, 0), (w, 56), RED, -1)
            (tw, _), _ = cv2.getTextSize("XAVFLI ZONA", cv2.FONT_HERSHEY_DUPLEX, 1.4, 3)
            cv2.putText(frame, "XAVFLI ZONA", ((w - tw) // 2, 42), cv2.FONT_HERSHEY_DUPLEX, 1.4, WHITE, 3, cv2.LINE_AA)

        violators = sum(t.confirmed for t in people)
        self.state = {
            "status": "zone" if zone_alarm else "danger" if violators else "safe",
            "people": len(people),
            "violators": violators,
        }
        for e in events:
            self.alerts.handle(e, frame)

    def _run(self):
        last_seq, last_log, times = 0, time.monotonic(), []
        while not self._stop.is_set():
            video = self.video
            seq, frame = video.read()
            if frame is None or seq == last_seq or video is not self.video:
                time.sleep(0.005)
                continue
            last_seq = seq
            frame = frame.copy()
            now = time.monotonic()
            try:
                self.process(frame, now)
            except Exception:
                log.exception("Kadrni qayta ishlashda xato")
                continue
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            times = [t for t in times if now - t < 2.0] + [now]
            if len(times) > 1:
                self.fps = (len(times) - 1) / (times[-1] - times[0])
            with self._cond:
                self.jpeg = buf.tobytes()
                self.jpeg_seq += 1
                self.frame_size = (frame.shape[1], frame.shape[0])
                self._cond.notify_all()
            if now - last_log > 10:
                last_log = now
                log.info("FPS: %.1f", self.fps)
