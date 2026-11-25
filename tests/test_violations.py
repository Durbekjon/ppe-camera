from app.detector import HELMET, NO_HELMET, PERSON, VEST, Detection, role_of
from app.zones import Zone
from app.violations import ViolationEngine, point_in_polygon

SIZE = (1000, 1000)
P = Detection(PERSON, 0.9, (400, 200, 600, 800))
HEAD = (450, 200, 550, 300)
HAT = Detection(HELMET, 0.8, HEAD)
BARE = Detection(NO_HELMET, 0.8, HEAD)
VESTD = Detection(VEST, 0.8, (420, 350, 580, 550))
SQUARE = [(0.3, 0.6), (0.7, 0.6), (0.7, 1.0), (0.3, 1.0)]


def run(engine, frames, start=0.0, dt=0.1):
    """Feed (detections) frames at 10 FPS; return list of (time, event)."""
    out = []
    for i, dets in enumerate(frames):
        now = start + i * dt
        _, events = engine.update(dets, now, SIZE)
        out += [(round(now, 1), e) for e in events]
    return out


def test_role_mapping():
    assert role_of("Hard_hat") == HELMET and role_of("Hardhat") == HELMET
    assert role_of("No-Helmet") == NO_HELMET and role_of("NO-Hardhat") == NO_HELMET
    assert role_of("Worker") == PERSON and role_of("Person") == PERSON
    assert role_of("NO-Safety Vest") == "no_vest" and role_of("Safety Vest") == VEST
    assert role_of("Boots") is None and role_of("No-Glove") is None


def test_helmet_on_means_no_alert():
    assert run(ViolationEngine(), [[P, HAT]] * 100) == []


def test_alert_only_after_debounce():
    events = run(ViolationEngine(debounce=1.5), [[P, BARE]] * 30)
    assert [t for t, _ in events] == [1.5]
    assert events[0][1].missing == ("helmet",) and not events[0][1].zone


def test_no_helmet_detection_at_all_counts_as_violation():
    assert len(run(ViolationEngine(), [[P]] * 30)) == 1


def test_explicit_rule_needs_a_bare_head_detection():
    assert run(ViolationEngine(helmet_rule="explicit"), [[P]] * 30) == []
    assert len(run(ViolationEngine(helmet_rule="explicit"), [[P, BARE]] * 30)) == 1


def test_short_violation_is_ignored():
    frames = [[P, BARE]] * 10 + [[P, HAT]] * 30  # 1.0 s without helmet, then compliant
    assert run(ViolationEngine(debounce=1.5), frames) == []


def test_detector_flicker_does_not_reset_debounce():
    frames = ([[P, BARE]] * 5 + [[P, HAT]] * 2) * 5  # 0.2 s "helmet" blips
    assert len(run(ViolationEngine(debounce=1.5), frames)) == 1


def test_cooldown_limits_repeat_alerts():
    events = run(ViolationEngine(debounce=1.5, cooldown=15), [[P, BARE]] * 400)  # 40 s
    assert [t for t, _ in events] == [1.5, 16.5, 31.5]


def test_brief_track_loss_keeps_identity_and_cooldown():
    frames = [[P, BARE]] * 30 + [[]] * 10 + [[P, BARE]] * 60  # person vanishes for 1 s
    assert len(run(ViolationEngine(), frames)) == 1


def test_two_people_alert_independently():
    p2 = Detection(PERSON, 0.9, (700, 200, 900, 800))
    hat2 = Detection(HELMET, 0.8, (750, 200, 850, 300))
    events = run(ViolationEngine(), [[P, BARE, p2, hat2]] * 30)
    assert len(events) == 1 and events[0][1].box == P.box


def test_tiny_people_are_ignored():
    small = Detection(PERSON, 0.9, (400, 200, 430, 290))
    assert run(ViolationEngine(), [[small]] * 30) == []


def test_vest_required_only_when_enabled():
    assert run(ViolationEngine(), [[P, HAT]] * 30) == []
    events = run(ViolationEngine(require_vest=True), [[P, HAT]] * 30)
    assert events[0][1].missing == ("vest",)
    assert run(ViolationEngine(require_vest=True), [[P, HAT, VESTD]] * 30) == []


def test_point_in_polygon():
    assert point_in_polygon(0.5, 0.8, SQUARE)
    assert not point_in_polygon(0.1, 0.8, SQUARE) and not point_in_polygon(0.5, 0.5, SQUARE)


def test_zone_escalates():
    engine = ViolationEngine()
    engine.zones = [Zone("A", SQUARE)]  # feet of P are at (0.5, 0.8) -> inside
    events = run(engine, [[P, BARE]] * 30)
    assert len(events) == 1 and events[0][1].zone


def test_entering_zone_during_cooldown_escalates_once():
    engine = ViolationEngine()
    events = run(engine, [[P, BARE]] * 30)
    assert not events[0][1].zone
    engine.zones = [Zone("A", SQUARE)]
    events = run(engine, [[P, BARE]] * 100, start=3.0)
    assert len(events) == 1 and events[0][1].zone


def test_helmet_in_zone_is_fine():
    engine = ViolationEngine()
    engine.zones = [Zone("A", SQUARE)]
    assert run(engine, [[P, HAT]] * 30) == []


def test_person_cut_off_by_frame_bottom_is_in_edge_zone():
    engine = ViolationEngine()
    engine.zones = [Zone("A", SQUARE)]  # reaches y = 1.0
    cut = Detection(PERSON, 0.9, (400, 300, 600, 1000))
    events = run(engine, [[cut]] * 30)
    assert events[0][1].zone


def test_moving_person_keeps_one_id():
    engine, ids = ViolationEngine(), set()
    for i in range(30):
        walker = Detection(PERSON, 0.9, (100 + 20 * i, 200, 300 + 20 * i, 800))
        people, _ = engine.update([walker], i * 0.1, SIZE)
        ids.update(t.id for t in people)
    assert len(ids) == 1


def test_low_confidence_person_is_still_tracked():
    weak = Detection(PERSON, 0.45, P.box)
    assert len(run(ViolationEngine(), [[weak]] * 30)) == 1


def recorded(events):
    return [(t, e) for t, e in events if e.record]


def test_five_minutes_without_helmet_is_one_incident_with_voice_reminders():
    events = run(ViolationEngine(), [[P, BARE]] * 3000)
    assert len(recorded(events)) == 1
    assert len(events) == 20  # first warning plus a reminder every 15 s


def moved(dx):
    box = (400 + dx, 200, 600 + dx, 800)
    return [Detection(PERSON, 0.9, box), Detection(NO_HELMET, 0.8, (450 + dx, 200, 550 + dx, 300))]


def test_revived_id_after_a_gap_continues_the_incident():
    frames = [moved(0)] * 30 + [[]] * 60 + [moved(60)] * 40  # hidden for 6 s, same ID comes back
    assert len(recorded(run(ViolationEngine(), frames))) == 1


def test_new_id_near_the_same_spot_continues_the_incident():
    engine = ViolationEngine(rejoin=20)
    frames = [moved(0)] * 30 + [[]] * 150 + [moved(60)] * 40  # long enough for the tracker to forget the ID
    events = run(engine, frames)
    assert len(recorded(events)) == 1
    assert engine.tracks[0].id != events[0][1].track_id  # it really did get a new ID


def test_return_after_rejoin_window_is_a_new_incident():
    frames = [moved(0)] * 30 + [[]] * 150 + [moved(0)] * 40  # away 15 s
    assert len(recorded(run(ViolationEngine(rejoin=10), frames))) == 2


def test_worker_appearing_elsewhere_is_a_new_incident():
    frames = [moved(-300)] * 30 + [[]] * 60 + [moved(300)] * 40
    assert len(recorded(run(ViolationEngine(), frames))) == 2


def test_two_visible_workers_are_never_merged():
    both = moved(-100) + moved(100)  # close together
    frames = [moved(-100)] * 30 + [both] * 40
    assert len(recorded(run(ViolationEngine(), frames))) == 2


def test_short_false_helmet_reading_does_not_create_a_second_incident():
    frames = [[P, BARE]] * 30 + [[P, HAT]] * 20 + [[P, BARE]] * 40  # "helmet" for 2 s
    assert len(recorded(run(ViolationEngine(), frames))) == 1


def test_removing_helmet_again_is_a_new_incident():
    frames = [[P, BARE]] * 30 + [[P, HAT]] * 80 + [[P, BARE]] * 40  # wore it for 8 s
    assert len(recorded(run(ViolationEngine(), frames))) == 2


def test_staying_in_zone_is_recorded_once_and_reentry_again():
    engine = ViolationEngine()
    engine.zones = [Zone("A", SQUARE)]
    assert len(recorded(run(engine, [[P, BARE]] * 400))) == 1
    engine.zones = []  # outside for 20 s
    assert recorded(run(engine, [[P, BARE]] * 200, start=40.0)) == []
    engine.zones = [Zone("A", SQUARE)]
    again = recorded(run(engine, [[P, BARE]] * 20, start=60.0))
    assert len(again) == 1 and again[0][1].zone and again[0][0] == 60.0


def test_close_up_person_with_hidden_feet_uses_box_centre():
    engine = ViolationEngine()
    engine.zones = [Zone("A", [(0.3, 0.2), (0.7, 0.2), (0.7, 0.75), (0.3, 0.75)])]  # does not reach the bottom edge
    close_up = Detection(PERSON, 0.9, (100, 10, 900, 998))
    assert run(engine, [[close_up]] * 30)[0][1].zone


def test_visible_feet_outside_zone_ignore_box_centre():
    engine = ViolationEngine()
    engine.zones = [Zone("A", [(0.3, 0.2), (0.7, 0.2), (0.7, 0.75), (0.3, 0.75)])]
    assert not run(engine, [[P]] * 30)[0][1].zone  # centre is inside, feet (y=0.8) are not
