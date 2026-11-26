"""Background loop: newest frame -> detection -> annotated JPEG for the dashboard."""
import logging
import threading
import time
from datetime import datetime

import cv2

import os
from dataclasses import replace

import numpy as np

from . import config, privacy
from .alerts import describe
from .detector import HELMET, PERSON, VEST
from .pose import BONES, POINT_CONF
from .tamper import ViewGuard
from .video import VideoSource
from .violations import ViolationEngine

log = logging.getLogger("pipeline")

GREEN, AMBER, RED, WHITE = (80, 200, 60), (40, 170, 250), (40, 40, 230), (255, 255, 255)
GREY = (150, 150, 150)


def draw_box(frame, box, color, label, thickness=2):
    x1, y1, x2, y2 = (int(v) for v in box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    y = max(y1, th + 6)
    cv2.rectangle(frame, (x1, y - th - 6), (x1 + tw + 6, y), color, -1)
    cv2.putText(frame, label, (x1 + 3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)


def draw_skeleton(frame, points, color):
    for a, b in BONES:
        if points[a][2] >= POINT_CONF and points[b][2] >= POINT_CONF:
            cv2.line(frame, (int(points[a][0]), int(points[a][1])), (int(points[b][0]), int(points[b][1])),
                     color, 2, cv2.LINE_AA)
    for x, y, confidence in points:
        if confidence >= POINT_CONF:
            cv2.circle(frame, (int(x), int(y)), 3, WHITE, -1, cv2.LINE_AA)


class Pipeline:
    def __init__(self, name, index, source, detector, alerts, voice):
        """One camera. `detector`, `alerts` and `voice` are shared by all cameras."""
        self.name, self.index, self.source = name, index, source
        self.demo = config.DEMO_MODE
        self.running = True  # False after "To'xtatish": the camera is released until "Boshlash"
        self.video = VideoSource(self._source(), config.FRAME_WIDTH)
        self.detector = detector
        self.engine = ViolationEngine(config.DEBOUNCE_S, config.COOLDOWN_S, config.REQUIRE_VEST, config.HELMET_RULE, config.CONF, config.RESOLVE_S, config.REJOIN_S, config.SKELETON)
        self.alerts = alerts
        self.voice = voice
        self.state = {"status": "safe", "people": 0, "violators": 0}
        self.view = ViewGuard() if config.TAMPER_CHECK else None
        self.fps = 0.0
        self.jpeg = None
        self.jpeg_seq = 0
        self.frame_size = (0, 0)
        self._cam_disconnected_at = None
        self._cam_alert_sent = False
        self._cond = threading.Condition()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"pipeline-{index}")

    def summary(self):
        if not self.running:
            return {"status": "stopped", "people": 0, "violators": 0, "connected": False, "fps": 0, "running": False}
        connected = self.video.connected
        state = self.state if connected else {"status": "offline", "people": 0, "violators": 0}
        if connected and self.view and self.view.blocked:
            state = {**state, "status": "blocked"}
        return {**state, "connected": connected, "fps": round(self.fps, 1) if connected else 0, "running": True}

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

    def set_running(self, on: bool):
        """Stop the camera (the device is released, no detection, no alerts) or start it again."""
        if on == self.running:
            return
        if on:
            self.video = VideoSource(self._source(), config.FRAME_WIDTH)
            self.video.start()
            self.running = True
        else:
            self.running = False
            self.video.stop()
            self.engine.reset()
            self.state = {"status": "safe", "people": 0, "violators": 0}
            self.fps = 0.0
            self._cam_disconnected_at, self._cam_alert_sent = None, False  # stopping is not an outage
            with self._cond:
                self.jpeg = None
                self.jpeg_seq += 1
                self._cond.notify_all()
        log.info("%s: kamera %s", self.name, "ishga tushirildi" if on else "to'xtatildi")

    def _source(self):
        return config.DEMO_VIDEO if self.demo else self.source

    def set_demo(self, on: bool):
        """Switch between the live source and the offline demo video at runtime."""
        if on and not os.path.exists(config.DEMO_VIDEO):
            raise FileNotFoundError(config.DEMO_VIDEO)
        old, self.demo = self.video, on
        self.video = VideoSource(self._source(), config.FRAME_WIDTH)
        if self.running:  # a stopped camera stays stopped; "Boshlash" opens the new source
            self.video.start()
        old.stop()
        self.engine.reset()
        log.info("%s: demo rejimi %s (manba: %s)", self.name, "yoqildi" if on else "o'chirildi", self.video.label)

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
        if self.view:
            change = self.view.update(frame, now)
            if change == "blocked":
                log.error("%s: kamera ko'rinishi yo'qoldi (to'silgan yoki juda qorong'i)", self.name)
                self._notify(f"🚫 [{self.name}] kamerasi to'silgan yoki hech narsa ko'rinmayapti!")
            elif change == "restored":
                log.info("%s: kamera ko'rinishi tiklandi", self.name)
                self._notify(f"✅ [{self.name}] kamerasi yana ko'ryapti")
        detections = self.detector.detect(frame)
        clock = datetime.now().strftime("%H:%M")
        people, events = self.engine.update(detections, now, (w, h), clock)
        alarmed = [t for t in people if t.confirmed and t.in_zone]
        zone_alarm = bool(alarmed)
        clean = frame.copy() if any(e.record for e in events) else None  # before anything is drawn
        regions = None
        if config.BLUR_FACES and any(e.record for e in events):
            try:  # faces are searched before anything is drawn over them
                regions = privacy.face_regions(frame, [d.box for d in detections if d.role == PERSON])
            except Exception:
                log.exception("Yuzlarni topishda xato")
                regions = [(0, 0, w, h)]  # fail closed: blur everything
        self._draw_zones(frame, clock, {t.zone_name for t in alarmed})
        for d in detections:
            if d.role in (HELMET, VEST):
                x1, y1, x2, y2 = (int(v) for v in d.box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), GREEN, 1)
        for t in people:
            if t.keypoints:
                draw_skeleton(frame, t.keypoints, RED if t.confirmed else GREEN)
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
                self.alerts.handle(replace(e, camera=self.name, camera_index=self.index), frame, regions, clean, detections)
        if events:
            self.voice.warn(replace(max(events, key=lambda e: e.zone), camera=self.name), now)

    def _check_connection(self, now):
        if not self.running:  # stopped on purpose: no "camera lost" alert
            return
        video = self.video
        if not video.connected:
            if self._cam_disconnected_at is None:
                self._cam_disconnected_at = now
            elif now - self._cam_disconnected_at > 10.0 and not self._cam_alert_sent:
                self._cam_alert_sent = True
                log.error("%s: kamera uzildi (%s)", self.name, video.label)
                self._notify(f"🚨 OGOHLANTIRISH: [{self.name}] kamerasi bilan aloqa uzildi!\nManba: {video.label}")
        else:
            if self._cam_alert_sent:
                self._cam_alert_sent = False
                log.info("%s: kamera qayta ulandi (%s)", self.name, video.label)
                self._notify(f"✅ [{self.name}] kamerasi bilan aloqa qayta tiklandi: {video.label}")
            self._cam_disconnected_at = None

    def _notify(self, text):
        try:  # the time matters: after an outage the message may arrive much later
            self.alerts.notify(f"{text}\nVaqt: {datetime.now():%Y-%m-%d %H:%M:%S}")
        except Exception:  # must not stop the video loop
            log.exception("%s: kamera xabarini navbatga qo'shib bo'lmadi", self.name)

    def _run(self):
        last_seq, last_log, times = 0, time.monotonic(), []
        while not self._stop.is_set():
            if not self.running:
                self._stop.wait(0.1)
                continue
            video = self.video
            now = time.monotonic()
            self._check_connection(now)

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
                log.exception("%s: kadrni qayta ishlashda xato", self.name)
                continue
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            times = [t for t in times if now - t < 2.0] + [now]
            if len(times) > 1:
                self.fps = (len(times) - 1) / (times[-1] - times[0])
            if not self.running or video is not self.video:  # stopped while this frame was processed
                continue
            with self._cond:
                self.jpeg = buf.tobytes()
                self.jpeg_seq += 1
                self.frame_size = (frame.shape[1], frame.shape[0])
                self._cond.notify_all()
            if now - last_log > 10:
                last_log = now
                log.info("%s: FPS %.1f", self.name, self.fps)
