"""Danger zones: validation, working hours, storage and migration from the single-zone file."""
import json
import os
import re
from dataclasses import asdict, dataclass

HELMET_RULE, NO_ENTRY_RULE = "helmet", "no_entry"
RULES = (HELMET_RULE, NO_ENTRY_RULE)
MAX_ZONES, MAX_NAME = 10, 30
_TIME = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


@dataclass
class Zone:
    name: str
    points: list  # [(x, y), ...] in 0..1 frame coordinates
    rule: str = HELMET_RULE  # "helmet": no gear is dangerous here; "no_entry": nobody may enter
    start: str = ""  # working hours "HH:MM"; both empty = always
    end: str = ""

    def active(self, clock) -> bool:
        """Is the zone in force at "HH:MM"? Hours may run over midnight; the end is exclusive."""
        if not self.start or clock is None:
            return True
        if self.start < self.end:
            return self.start <= clock < self.end
        return clock >= self.start or clock < self.end


def _snap(v):
    # Corners within 4% of the frame border snap to it, so a zone drawn "to the edge"
    # also contains people whose feet are cut off by the frame.
    return 0.0 if v < 0.04 else 1.0 if v > 0.96 else float(v)


def parse(items):
    """Turn dictionaries into Zones; raise ValueError with a message for the user."""
    if len(items) > MAX_ZONES:
        raise ValueError(f"Ko'pi bilan {MAX_ZONES} ta zona")
    zones, names = [], set()
    for item in items:
        name = str(item.get("name", "")).strip()
        if not name or len(name) > MAX_NAME:
            raise ValueError(f"Zona nomi 1–{MAX_NAME} belgi bo'lsin")
        if name.lower() in names:
            raise ValueError(f"Zona nomi takrorlangan: {name}")
        names.add(name.lower())
        rule = item.get("rule", HELMET_RULE)
        if rule not in RULES:
            raise ValueError("Zona qoidasi noto'g'ri")
        points = item.get("points") or []
        if len(points) < 3:
            raise ValueError("Zona uchun kamida 3 ta nuqta kerak")
        if not all(len(p) == 2 and all(0 <= v <= 1 for v in p) for p in points):
            raise ValueError("Zona nuqtalari kadr ichida bo'lsin")
        start, end = item.get("start") or "", item.get("end") or ""
        if start or end:
            if not (_TIME.fullmatch(start) and _TIME.fullmatch(end)) or start == end:
                raise ValueError("Ish vaqti: ikkala vaqt ham HH:MM bo'lsin va farq qilsin (bo'sh = doim)")
        zones.append(Zone(name, [(_snap(x), _snap(y)) for x, y in points], rule, start, end))
    return zones


def save(path, zones):
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps([asdict(z) for z in zones], ensure_ascii=False, indent=1))
    os.replace(tmp, path)  # never leave a half-written file


def load(path, legacy_path):
    """Read zones; on first run convert the old single-zone file (which is left untouched)."""
    if path.exists():
        return parse(json.loads(path.read_text()))
    if legacy_path.exists():
        points = json.loads(legacy_path.read_text())
        if len(points) >= 3:
            zones = parse([{"name": "Zona 1", "points": points}])
            save(path, zones)
            return zones
    return []
