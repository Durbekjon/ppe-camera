import json
import sqlite3

import pytest

from app import db, zones
from app.violations import ViolationEngine
from app.zones import NO_ENTRY_RULE, Zone
from tests.test_violations import HAT, BARE, P, SIZE, SQUARE, run

LEFT = [(0.0, 0.6), (0.3, 0.6), (0.3, 1.0), (0.0, 1.0)]


def engine_with(*items):
    engine = ViolationEngine()
    engine.zones = list(items)
    return engine


def test_no_entry_zone_flags_a_fully_equipped_person_once():
    events = run(engine_with(Zone("Kran", SQUARE, NO_ENTRY_RULE)), [[P, HAT]] * 300)
    recorded = [e for _, e in events if e.record]
    assert len(recorded) == 1 and recorded[0].missing == ("entry",)
    assert recorded[0].zone and recorded[0].zone_name == "Kran"


def test_helmet_zone_allows_an_equipped_person():
    assert run(engine_with(Zone("Sex", SQUARE)), [[P, HAT]] * 100) == []


def test_helmetless_in_no_entry_zone_reports_both():
    events = run(engine_with(Zone("Kran", SQUARE, NO_ENTRY_RULE)), [[P, BARE]] * 30)
    assert events[0][1].missing == ("helmet", "entry")


def test_overlap_uses_the_stricter_rule():
    events = run(engine_with(Zone("Sex", SQUARE), Zone("Kran", SQUARE, NO_ENTRY_RULE)), [[P, HAT]] * 30)
    assert events[0][1].zone_name == "Kran"


def test_moving_to_another_zone_is_recorded():
    engine = engine_with(Zone("A", SQUARE), Zone("B", SQUARE))
    engine.zones = [Zone("A", SQUARE)]
    first = run(engine, [[P, BARE]] * 30)
    engine.zones = [Zone("B", SQUARE)]
    second = run(engine, [[P, BARE]] * 30, start=3.0)
    assert [e.zone_name for _, e in first + second if e.record] == ["A", "B"]


def test_zone_outside_working_hours_is_ignored():
    engine = engine_with(Zone("Kran", SQUARE, NO_ENTRY_RULE, "08:00", "18:00"))
    for i in range(30):
        assert engine.update([P, HAT], i * 0.1, SIZE, "19:00")[1] == []
    events = [e for i in range(30) for e in engine.update([P, HAT], 3 + i * 0.1, SIZE, "09:00")[1]]
    assert len(events) == 1


@pytest.mark.parametrize("start, end, clock, active", [
    ("", "", "03:00", True),
    ("08:00", "18:00", "08:00", True),
    ("08:00", "18:00", "18:00", False),
    ("22:00", "06:00", "23:30", True),
    ("22:00", "06:00", "05:59", True),
    ("22:00", "06:00", "12:00", False),
])
def test_working_hours(start, end, clock, active):
    assert Zone("A", LEFT, start=start, end=end).active(clock) is active


@pytest.mark.parametrize("change", [
    {"name": " "}, {"rule": "x"}, {"points": [(0, 0), (1, 1)]}, {"points": [(0, 0), (2, 0), (1, 1)]},
    {"start": "08:00"}, {"start": "25:00", "end": "26:00"}, {"start": "08:00", "end": "08:00"},
])
def test_invalid_zones_are_rejected(change):
    with pytest.raises(ValueError):
        zones.parse([{"name": "A", "points": LEFT, **change}])


def test_duplicate_names_are_rejected():
    with pytest.raises(ValueError):
        zones.parse([{"name": "A", "points": LEFT}, {"name": "a", "points": SQUARE}])


def test_old_zone_file_is_converted_and_kept(tmp_path):
    old, new = tmp_path / "zone.json", tmp_path / "zones.json"
    old.write_text(json.dumps(SQUARE))
    loaded = zones.load_all(new, old, "Kirish")
    assert [(z.name, z.rule, z.points) for z in loaded["Kirish"]] == [("Zona 1", "helmet", SQUARE)]
    assert new.exists() and json.loads(old.read_text()) == [list(p) for p in SQUARE]
    zones.save_all(new, {"Kirish": []})  # deleting every zone must not bring the old one back
    assert zones.load_all(new, old, "Kirish") == {"Kirish": []}


def test_single_camera_zone_list_moves_to_the_first_camera_with_a_backup(tmp_path):
    new = tmp_path / "zones.json"
    original = json.dumps([{"name": "Kran", "points": SQUARE, "rule": NO_ENTRY_RULE}])
    new.write_text(original)
    loaded = zones.load_all(new, tmp_path / "none.json", "Kirish")
    assert list(loaded) == ["Kirish"] and loaded["Kirish"][0].rule == NO_ENTRY_RULE
    assert (tmp_path / "zones.json.single.bak").read_text() == original
    assert zones.load_all(new, tmp_path / "none.json", "Boshqa") == loaded  # converted only once


def test_old_database_keeps_its_incidents(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE incidents (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
                "missing TEXT NOT NULL, zone INTEGER NOT NULL, track_id INTEGER, snapshot TEXT)")
    con.execute("INSERT INTO incidents (ts, missing, zone) VALUES ('2026-11-25 10:00:00', 'helmet', 1)")
    con.commit()
    con.close()
    db.init(path)
    db.init(path)  # running the migration twice is harmless
    row = db.list_incidents()[0]
    assert row["missing"] == "helmet" and row["zone_name"] == ""
