"""Turns per-frame detections into tracked people, debounced violations and alert events.

Pure logic (no OpenCV, no clock): the caller passes `now`, which keeps it easy to unit-test.
"""
from dataclasses import dataclass, field

from .detector import HELMET, NO_HELMET, PERSON, VEST
from .pose import body_samples
from .tracker import PersonTracker
from .zones import NO_ENTRY_RULE

ENTRY = "entry"  # "what is wrong" marker for a person inside a no-entry zone

CUT_OFF_MARGIN = 0.02  # a box ending this close to the bottom edge has its feet out of view
MIN_PERSON_HEIGHT = 0.15  # people shorter than this fraction of the frame are too small to judge
TRACK_MAX_AGE = 4.0  # seconds a track survives without being seen
OK_GRACE = 0.5  # seconds of "compliant" needed to clear a pending violation (absorbs detector flicker)
# A new ID may continue a lost person's violation if it appears close to where they were:
REJOIN_MAX_DX = 0.75  # horizontal distance between box centres, in old box widths
REJOIN_MAX_DY = 0.25  # vertical distance between box centres, in old box heights
REJOIN_HEIGHT_RATIO = 1.35  # box heights may differ by at most this factor


def point_in_polygon(x, y, poly):
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _center(box):
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _same_place(old, new):
    ow, oh, nh = old[2] - old[0], old[3] - old[1], new[3] - new[1]
    (ox, oy), (nx, ny) = _center(old), _center(new)
    return (
        abs(nx - ox) <= REJOIN_MAX_DX * ow
        and abs(ny - oy) <= REJOIN_MAX_DY * oh
        and max(oh, nh) <= REJOIN_HEIGHT_RATIO * min(oh, nh)
    )


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
    missing: tuple = ()  # what is wrong right now: subset of ("helmet", "vest", "entry")
    violating_since: float = None
    ok_since: float = None
    confirmed: bool = False  # violation has persisted past the debounce
    in_zone: bool = False
    zone_name: str = ""
    human: bool = True  # False until a skeleton has been seen (when skeletons are required)
    keypoints: tuple = None  # this frame's skeleton
    first_seen: float = 0.0
    first_box: tuple = ()
    episode: "Episode" = None


@dataclass
class Episode:
    """One continuing violation by one worker; it may outlive several track IDs."""

    owner: int  # track ID currently carrying it
    box: tuple
    last_seen: float
    ok_since: float = None
    zone_last_inside: dict = field(default_factory=dict)  # zone name -> time
    zone_recorded: dict = field(default_factory=dict)  # zone name -> time of last recorded entry
    last_alert: dict = field(default_factory=dict)  # level -> time of last voice warning


@dataclass
class Event:
    track_id: int
    missing: tuple
    zone: bool
    box: tuple
    record: bool = True  # False: voice reminder only, no new incident
    zone_name: str = ""
    camera: str = ""  # filled in by the camera's pipeline
    camera_index: int = 0


class ViolationEngine:
    def __init__(self, debounce=1.5, cooldown=15.0, require_vest=False, helmet_rule="missing", person_conf=0.4,
                 resolve=5.0, rejoin=10.0, require_skeleton=False):
        self.require_skeleton = require_skeleton
        self.resolve = resolve  # seconds of compliance that end a violation episode
        self.rejoin = rejoin  # longest disappearance after which a new ID can continue an episode
        self.person_conf = person_conf
        self.helmet_rule = helmet_rule
        self.debounce = debounce
        self.cooldown = cooldown
        self.require_vest = require_vest
        self.zones = []  # list of zones.Zone
        self.reset()

    def update(self, detections, now, frame_size, clock=None):
        """Return (visible tracks, new alert events) for one frame.

        `clock` is the wall time "HH:MM" used for zone working hours (None: every zone is active).
        """
        w, h = frame_size
        persons = [d for d in detections if d.role == PERSON and (d.box[3] - d.box[1]) >= MIN_PERSON_HEIGHT * h]
        visible = self._match(persons, now)
        # Forget episodes nobody can continue any more.
        keep = max(self.rejoin, TRACK_MAX_AGE) + self.debounce + 1
        self._episodes = [ep for ep in self._episodes if now - ep.last_seen <= keep]
        events = []
        by_box = {p.box: p.keypoints for p in persons}
        for t in visible:
            t.keypoints = by_box.get(t.box)
            if self.require_skeleton:
                # Once seen, the skeleton may drop out for a while: a real worker must not vanish.
                t.human = t.human or t.keypoints is not None
                if not t.human:  # a poster, a coat stand, a plant: not judged at all
                    t.missing, t.in_zone, t.confirmed, t.violating_since = (), False, False, None
                    continue
            t.missing = self._missing(t.box, detections)
            fx, fy = (t.box[0] + t.box[2]) / 2, min(t.box[3], h - 1)  # feet point, kept inside the frame
            if t.keypoints:  # any joint or bone inside the zone counts
                points = body_samples(t.keypoints)
            else:  # no skeleton: the feet point
                points = [(fx, fy)]
                if t.box[3] >= (1 - CUT_OFF_MARGIN) * h:  # feet not visible (e.g. close to the camera)
                    points.append(_center(t.box))
            inside = [
                z for z in self.zones
                if z.active(clock) and any(point_in_polygon(x / w, y / h, z.points) for x, y in points)
            ]
            inside.sort(key=lambda z: z.rule != NO_ENTRY_RULE)  # the stricter rule wins where zones overlap
            t.in_zone = bool(inside)
            t.zone_name = inside[0].name if inside else ""
            if inside and inside[0].rule == NO_ENTRY_RULE:
                t.missing += (ENTRY,)
            self._debounce(t, now)
        visible = [t for t in visible if t.human]
        visible_ids = {t.id for t in visible}
        for t in visible:
            event = self._follow_episode(t, now, visible_ids)
            if event:
                events.append(event)
        return visible, events

    def _follow_episode(self, t, now, visible_ids):
        """Attach the track to its violation episode and return an alert event if one is due."""
        ep = t.episode
        if ep and ep.owner != t.id:  # another ID took it over while this one was away
            ep = t.episode = None
        new = False
        if ep is None:
            if not t.confirmed:
                return None
            ep = self._rejoin(t, visible_ids)
            if ep is None:
                ep, new = Episode(t.id, t.box, now), True
                self._episodes.append(ep)
            ep.owner, t.episode = t.id, ep
        ep.box, ep.last_seen = t.box, now
        if t.violating_since is None:  # compliant: end the episode only if it lasts
            if ep.ok_since is None:
                ep.ok_since = now
            if now - ep.ok_since >= self.resolve:
                self._episodes.remove(ep)
                t.episode = None
            return None
        if t.missing:
            ep.ok_since = None
        if not t.confirmed:
            return None

        entered_zone = False
        if t.in_zone:
            last = ep.zone_last_inside.get(t.zone_name)
            was_away = last is None or now - last > self.resolve
            entered_zone = was_away and now - ep.zone_recorded.get(t.zone_name, -1e9) >= self.cooldown
            ep.zone_last_inside[t.zone_name] = now
        record = new or entered_zone
        level = "zone" if t.in_zone else "normal"
        if not record and now - ep.last_alert.get(level, -1e9) < self.cooldown:
            return None
        ep.last_alert[level] = now
        if t.in_zone:  # a zone alert also covers the ordinary one
            ep.last_alert["normal"] = now
            if record:
                ep.zone_recorded[t.zone_name] = now
        return Event(t.id, t.missing or ("helmet",), t.in_zone, t.box, record, t.zone_name)

    def _rejoin(self, t, visible_ids):
        """Find the episode of a recently lost worker that this new ID most likely continues."""
        candidates = [
            ep for ep in self._episodes
            if (ep.owner == t.id or ep.owner not in visible_ids)  # the tracker may revive an old ID
            and 0 <= t.first_seen - ep.last_seen <= self.rejoin
            and _same_place(ep.box, t.first_box)
        ]
        x = _center(t.first_box)[0]
        return min(candidates, key=lambda ep: abs(_center(ep.box)[0] - x), default=None)

    def reset(self):
        """Forget everyone, e.g. after the video source changes."""
        self.tracks = []
        self._episodes = []
        self._tracker = PersonTracker(self.person_conf)

    def _match(self, persons, now):
        known = {t.id: t for t in self.tracks if now - t.last_seen <= TRACK_MAX_AGE}
        visible = []
        for track_id, p in self._tracker.update(persons):
            t = known.get(track_id) or Track(track_id, p.box, now, first_seen=now, first_box=p.box,
                                               human=not self.require_skeleton)
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
