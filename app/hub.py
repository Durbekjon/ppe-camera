"""All cameras together: what they share (model, alerts, zone file, voice warnings)."""
import logging
import threading

from . import config, tts, zones
from .alerts import AlertManager, telegram_configured
from .telegram_bot import ButtonListener
from .cameras import parse_cameras
from .detector import Detector
from .pipeline import Pipeline
from .pose import SkeletonDetector

log = logging.getLogger("hub")

ZONE_FILE = config.DATA / "zones.json"
LEGACY_ZONE_FILE = config.DATA / "zone.json"
SEVERITY = ("zone", "danger", "blocked", "offline", "stopped", "safe")  # worst first
DEMO_SUFFIX = " (demo)"  # zones drawn in demo mode are stored as "<camera> (demo)"


def zone_key(pipeline):
    """Where a camera's zones are stored: live and demo video each have their own."""
    return pipeline.name + DEMO_SUFFIX if pipeline.demo else pipeline.name


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
            if config.LOCAL_AUDIO:
                key = "entry" if "entry" in event.missing else ("zone" if event.zone else event.missing[0])
                tts.play_local(key)


class Hub:
    def __init__(self, cameras=None):
        cameras = cameras or parse_cameras(config.CAMERAS, config.VIDEO_SOURCE)
        names = [name for name, _ in cameras]
        self._zone_lock = threading.Lock()
        self._zones = zones.load_all(ZONE_FILE, LEGACY_ZONE_FILE, names[0])
        orphaned = [n for n in self._zones if n.removesuffix(DEMO_SUFFIX) not in names]
        if orphaned:
            log.warning("Sozlamada yo'q kameralarning zonalari saqlanib turibdi: %s", ", ".join(orphaned))
        model = Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF)
        if config.SKELETON:
            model = SkeletonDetector(model, config.POSE_MODEL_PATH, config.POSE_IMG_SIZE)
        detector = SharedDetector(model)
        self.alerts = AlertManager()
        self.buttons = None  # set by start() when Telegram buttons are in use
        self.voice = Voice()
        self.cameras = {}
        for index, (name, source) in enumerate(cameras, 1):
            pipeline = Pipeline(name, index, source, detector, self.alerts, self.voice)
            pipeline.engine.zones = self._zones.get(zone_key(pipeline), [])
            self.cameras[name] = pipeline

    def get(self, name=""):
        """The named camera, or the first one for an empty name. Raises KeyError."""
        return self.cameras[name] if name else next(iter(self.cameras.values()))

    def start(self):
        for p in self.cameras.values():
            p.start()
        if config.TELEGRAM_BUTTONS and telegram_configured():
            self.buttons = ButtonListener()
            self.buttons.start()

    def stop(self):
        if self.buttons:
            self.buttons.stop()
        for p in self.cameras.values():
            p.stop()
        self.alerts.close()

    def set_zones(self, name, items):
        """Replace the zones of one camera in its current mode (raises ValueError for invalid input)."""
        pipeline, parsed = self.get(name), zones.parse(items)
        with self._zone_lock:
            updated = {**self._zones, zone_key(pipeline): parsed}
            zones.save_all(ZONE_FILE, updated)
            self._zones = updated
            pipeline.engine.zones = parsed
        log.info("%s: zonalar saqlandi (%s): %d ta", pipeline.name, "demo" if pipeline.demo else "real", len(parsed))

    def set_demo(self, name, on):
        """Switch a camera between live and demo video, with the zones drawn for that mode.

        The demo video shows a different scene, so a zone drawn on it must not guard the real camera.
        Raises FileNotFoundError when the demo video is missing.
        """
        pipeline = self.get(name)
        with self._zone_lock:
            pipeline.set_demo(on)
            pipeline.engine.zones = self._zones.get(zone_key(pipeline), [])
        return pipeline

    def summary(self):
        """Short status per camera, and the most serious one for the page header."""
        items = [{"name": p.name, **p.summary()} for p in self.cameras.values()]
        worst = min(items, key=lambda c: SEVERITY.index(c["status"]))
        return items, {"status": worst["status"], "camera": worst["name"]}
