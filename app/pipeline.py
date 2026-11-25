"""Background loop: newest frame -> detection -> annotated JPEG for the dashboard."""
import logging
import threading
import time
from datetime import datetime

import cv2

import os

import numpy as np

from . import config, zones
from .alerts import AlertManager, describe
from .detector import HELMET, VEST, Detector
from .video import VideoSource
from .violations import ViolationEngine

log = logging.getLogger("pipeline")

GREEN, AMBER, RED, WHITE = (80, 200, 60), (40, 170, 250), (40, 40, 230), (255, 255, 255)
ZONE_FILE = config.DATA / "zones.json"
LEGACY_ZONE_FILE = config.DATA / "zone.json"
GREY = (150, 150, 150)


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
        self.engine = ViolationEngine(config.DEBOUNCE_S, config.COOLDOWN_S, config.REQUIRE_VEST, config.HELMET_RULE, config.CONF, config.RESOLVE_S, config.REJOIN_S)
        self.alerts = AlertManager()
        self.state = {"status": "safe", "people": 0, "violators": 0}
        self.engine.zones = zones.load(ZONE_FILE, LEGACY_ZONE_FILE)
        self.fps = 0.0
        self.voice = {"seq": 0, "missing": "helmet", "zone": False}  # latest spoken warning
        self._voice_at = 0.0
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

    def set_zones(self, items):
        """Replace all zones (raises ValueError for invalid input)."""
        parsed = zones.parse(items)
        zones.save(ZONE_FILE, parsed)
        self.engine.zones = parsed
        log.info("Zonalar saqlandi: %d ta", len(parsed))

    def _draw_zones(self, frame, clock, alarms):
        h, w = frame.shape[:2]
        for z in self.engine.zones:
            pts = np.array([(int(x * w), int(y * h)) for x, y in z.points], np.int32)
            color = RED if z.active(clock) else GREY
            if z.active(clock):
                alpha = 0.35 if z.name in alarms else 0.15
                overlay = frame.copy()
                cv2.fillPoly(overlay, [pts], color)
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)
            # OpenCV's built-in font is ASCII only.
            label = z.name.replace("\u2018", "'").replace("\u2019", "'").replace("\u02bb", "'")
            x, y = pts.min(axis=0)
            cv2.putText(frame, label.encode("ascii", "replace").decode(), (int(x) + 4, max(int(y) + 18, 76)),  # stay below the alarm banner
                       
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)

    def process(self, frame, now):
        """Detect, update violation state, annotate the frame in place and raise alerts."""
        h, w = frame.shape[:2]
        detections = self.detector.detect(frame)
        clock = datetime.now().strftime("%H:%M")
        people, events = self.engine.update(detections, now, (w, h), clock)
        alarmed = [t for t in people if t.confirmed and t.in_zone]
        zone_alarm = bool(alarmed)
        self._draw_zones(frame, clock, {t.zone_name for t in alarmed})
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
            title = "KIRISH TAQIQLANGAN" if any("entry" in t.missing for t in alarmed) else "XAVFLI ZONA"
            (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_DUPLEX, 1.4, 3)
            cv2.putText(frame, title, ((w - tw) // 2, 42), cv2.FONT_HERSHEY_DUPLEX, 1.4, WHITE, 3, cv2.LINE_AA)

        violators = sum(t.confirmed for t in people)
        self.state = {
            "status": "zone" if zone_alarm else "danger" if violators else "safe",
            "people": len(people),
            "violators": violators,
        }
        for e in events:
            if e.record:
                self.alerts.handle(e, frame)
        if events:
            self._warn(max(events, key=lambda e: e.zone), now)

    def _warn(self, event, now):
        """Publish a voice warning for the dashboard; a fresh zone warning is not overridden."""
        if self.voice["zone"] and not event.zone and now - self._voice_at < 1.0:
            return
        self._voice_at = now
        self.voice = {"seq": self.voice["seq"] + 1, "missing": "entry" if "entry" in event.missing else event.missing[0],
                      "zone": event.zone}

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
