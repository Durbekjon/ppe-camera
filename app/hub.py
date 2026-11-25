"""All cameras together: what they share (model, alerts, zone file, voice warnings)."""
import logging
import threading

from . import config, zones
from .alerts import AlertManager
from .cameras import parse_cameras
from .detector import Detector
from .pipeline import Pipeline

log = logging.getLogger("hub")

ZONE_FILE = config.DATA / "zones.json"
LEGACY_ZONE_FILE = config.DATA / "zone.json"
SEVERITY = ("zone", "danger", "offline", "safe")  # worst first


class SharedDetector:
    """One model for all cameras; the model is not thread safe, so they take turns."""

    def __init__(self, detector):
        self._detector, self._lock = detector, threading.Lock()

    def detect(self, frame):
        with self._lock:
            return self._detector.detect(frame)


class Voice:
    """The latest spoken warning from any camera."""

    def __init__(self):
        self.latest = {"seq": 0, "missing": "helmet", "zone": False, "camera": ""}
        self._at, self._lock = 0.0, threading.Lock()

    def warn(self, event, now):
        with self._lock:
            # A fresh zone warning is not overridden by an ordinary one.
            if self.latest["zone"] and not event.zone and now - self._at < 1.0:
                return
            self._at = now
            self.latest = {
                "seq": self.latest["seq"] + 1,
                "missing": "entry" if "entry" in event.missing else event.missing[0],
                "zone": event.zone,
                "camera": event.camera,
            }


class Hub:
    def __init__(self, cameras=None):
        cameras = cameras or parse_cameras(config.CAMERAS, config.VIDEO_SOURCE)
        names = [name for name, _ in cameras]
        self._zone_lock = threading.Lock()
        self._zones = zones.load_all(ZONE_FILE, LEGACY_ZONE_FILE, names[0])
        orphaned = [n for n in self._zones if n not in names]
        if orphaned:
            log.warning("Sozlamada yo'q kameralarning zonalari saqlanib turibdi: %s", ", ".join(orphaned))
        detector = SharedDetector(Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF))
        self.alerts = AlertManager()
        self.voice = Voice()
        self.cameras = {}
        for index, (name, source) in enumerate(cameras, 1):
            pipeline = Pipeline(name, index, source, detector, self.alerts, self.voice)
            pipeline.engine.zones = self._zones.get(name, [])
            self.cameras[name] = pipeline

    def get(self, name=""):
        """The named camera, or the first one for an empty name. Raises KeyError."""
        return self.cameras[name] if name else next(iter(self.cameras.values()))

    def start(self):
        for p in self.cameras.values():
            p.start()

    def stop(self):
        for p in self.cameras.values():
            p.stop()

    def set_zones(self, name, items):
        """Replace one camera's zones (raises ValueError for invalid input)."""
        pipeline, parsed = self.get(name), zones.parse(items)
        with self._zone_lock:
            updated = {**self._zones, pipeline.name: parsed}
            zones.save_all(ZONE_FILE, updated)
            self._zones = updated
            pipeline.engine.zones = parsed
        log.info("%s: zonalar saqlandi: %d ta", pipeline.name, len(parsed))

    def summary(self):
        """Short status per camera, and the most serious one for the page header."""
        items = [{"name": p.name, **p.summary()} for p in self.cameras.values()]
        worst = min(items, key=lambda c: SEVERITY.index(c["status"]))
        return items, {"status": worst["status"], "camera": worst["name"]}
