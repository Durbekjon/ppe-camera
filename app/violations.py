"""Turns per-frame detections into tracked people, debounced violations and alert events.

Pure logic (no OpenCV, no clock): the caller passes `now`, which keeps it easy to unit-test.
"""
from dataclasses import dataclass, field

from .detector import HELMET, NO_HELMET, PERSON, VEST
from .tracker import PersonTracker

MIN_PERSON_HEIGHT = 0.15  # people shorter than this fraction of the frame are too small to judge
TRACK_MAX_AGE = 4.0  # seconds a track survives without being seen
OK_GRACE = 0.5  # seconds of "compliant" needed to clear a pending violation (absorbs detector flicker)


def point_in_polygon(x, y, poly):
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _center(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _best_conf(dets, role, region):
    """Highest confidence of a `role` detection whose centre falls inside `region`."""
    best = 0.0
    for d in dets:
        if d.role == role:
            cx, cy = _center(d.box)
            if region[0] <= cx <= region[2] and region[1] <= cy <= region[3]:
                best = max(best, d.conf)
    return best


@dataclass
class Track:
    id: int
    box: tuple
    last_seen: float
    missing: tuple = ()  # what is missing right now: subset of ("helmet", "vest")
    violating_since: float = None
    ok_since: float = None
    confirmed: bool = False  # violation has persisted past the debounce
    in_zone: bool = False
    last_alert: dict = field(default_factory=dict)  # level -> time of last alert


@dataclass
class Event:
    track_id: int
    missing: tuple
    zone: bool
    box: tuple


class ViolationEngine:
    def __init__(self, debounce=1.5, cooldown=15.0, require_vest=False, helmet_rule="missing", person_conf=0.4):
        self.person_conf = person_conf
        self.helmet_rule = helmet_rule
        self.debounce = debounce
        self.cooldown = cooldown
        self.require_vest = require_vest
        self.zone = []  # polygon as [(x, y), ...] in 0..1 frame coordinates
        self.reset()

    def update(self, detections, now, frame_size):
        """Return (visible tracks, new alert events) for one frame."""
        w, h = frame_size
        persons = [d for d in detections if d.role == PERSON and (d.box[3] - d.box[1]) >= MIN_PERSON_HEIGHT * h]
        visible = self._match(persons, now)
        events = []
        for t in visible:
            t.missing = self._missing(t.box, detections)
            fx, fy = (t.box[0] + t.box[2]) / 2, min(t.box[3], h - 1)  # feet point, kept inside the frame
            t.in_zone = len(self.zone) >= 3 and point_in_polygon(fx / w, fy / h, self.zone)
            self._debounce(t, now)
            if t.confirmed:
                level = "zone" if t.in_zone else "normal"
                if now - t.last_alert.get(level, -1e9) >= self.cooldown:
                    t.last_alert[level] = now
                    if level == "zone":  # a zone alert also covers the ordinary one
                        t.last_alert["normal"] = now
                    events.append(Event(t.id, t.missing or ("helmet",), t.in_zone, t.box))
        return visible, events

    def reset(self):
        """Forget everyone, e.g. after the video source changes."""
        self.tracks = []
        self._tracker = PersonTracker(self.person_conf)

    def _match(self, persons, now):
        known = {t.id: t for t in self.tracks if now - t.last_seen <= TRACK_MAX_AGE}
        visible = []
        for track_id, p in self._tracker.update(persons):
            t = known.get(track_id) or Track(track_id, p.box, now)
            t.box, t.last_seen = p.box, now
            known[track_id] = t
            visible.append(t)
        self.tracks = list(known.values())
        return visible

    def _missing(self, box, detections):
        x1, y1, x2, y2 = box
        head = (x1, y1 - 0.1 * (y2 - y1), x2, y1 + 0.4 * (y2 - y1))
        missing = []
        # An explicit "no helmet" detection beats a weaker helmet detection. With the default
        # "missing" rule, seeing no helmet at all on the head region is a violation too.
        helmet = _best_conf(detections, HELMET, head)
        bare = _best_conf(detections, NO_HELMET, head)
        if bare > helmet or (helmet == 0 and self.helmet_rule == "missing"):
            missing.append("helmet")
        if self.require_vest and _best_conf(detections, VEST, box) == 0:
            missing.append("vest")
        return tuple(missing)

    def _debounce(self, t, now):
        if t.missing:
            t.ok_since = None
            if t.violating_since is None:
                t.violating_since = now
            t.confirmed = now - t.violating_since >= self.debounce
        elif t.violating_since is not None:
            if t.ok_since is None:
                t.ok_since = now
            if now - t.ok_since >= OK_GRACE:
                t.violating_since, t.confirmed = None, False
