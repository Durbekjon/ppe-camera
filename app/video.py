"""Threaded video capture that always exposes the newest frame and reconnects if the source drops."""
import logging
import os
import re
import threading
import time

import cv2

log = logging.getLogger("video")


def parse_source(source: str):
    return int(source) if source.isdigit() else source


class VideoSource:
    def __init__(self, source: str, width: int = 960):
        self.source = source
        self.width = width
        self.is_file = not source.isdigit() and "://" not in source
        # Name used in logs: no stream passwords, no long absolute paths.
        self.label = os.path.basename(source) if self.is_file else re.sub(r"//[^/@]*@", "//***@", source)
        self.connected = False
        self._frame = None
        self._seq = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="video")

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=3)

    def read(self):
        """Return (sequence number, newest frame). The frame is None until the first one arrives."""
        with self._lock:
            return self._seq, self._frame

    def _run(self):
        delay = 1.0
        while not self._stop.is_set():
            cap = cv2.VideoCapture(parse_source(self.source))
            if not cap.isOpened():
                cap.release()
                self.connected = False
                log.warning("Video manbasi ochilmadi (%s); %.0f s dan keyin qayta urinish", self.label, delay)
                self._stop.wait(delay)
                delay = min(delay * 2, 10)
                continue
            log.info("Video manbasi ulandi: %s", self.label)
            delay = 1.0
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_time = 1.0 / fps if self.is_file and 1 < fps < 121 else 0
            next_at = time.monotonic()
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    if self.is_file:  # loop the file
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = cap.read()
                    if not ok:
                        break
                h, w = frame.shape[:2]
                if w > self.width:
                    frame = cv2.resize(frame, (self.width, int(h * self.width / w)))
                with self._lock:
                    self._frame = frame
                    self._seq += 1
                self.connected = True
                if frame_time:  # play files at their native speed
                    next_at += frame_time
                    time.sleep(max(0, next_at - time.monotonic()))
            cap.release()
            if not self._stop.is_set():
                self.connected = False
                log.warning("Video uzildi; qayta ulanmoqda...")
                self._stop.wait(1)
