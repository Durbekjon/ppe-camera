import cv2

from app import config
from app.detector import HELMET, PERSON, Detection, Detector
from app.pose import SkeletonDetector, attach, body_samples
from app.violations import ViolationEngine
from app.zones import NO_ENTRY_RULE, Zone

SIZE = (1000, 1000)
BOX = (400.0, 200.0, 600.0, 800.0)


def skeleton(**points):
    """17 untrusted points, with the given ones trusted, e.g. skeleton(p5=(450, 350))."""
    out = [(0.0, 0.0, 0.0)] * 17
    for name, (x, y) in points.items():
        out[int(name[1:])] = (float(x), float(y), 0.9)
    return tuple(out)


STANDING = skeleton(p0=(500, 250), p5=(450, 350), p6=(550, 350), p11=(470, 500), p12=(530, 500),
                    p15=(470, 780), p16=(530, 780))
# the right arm stretched far to the side: shoulder -> elbow -> wrist
REACHING = skeleton(p6=(550, 350), p8=(700, 350), p10=(850, 350), p5=(450, 350))


def person(points=None, box=BOX):
    return Detection(PERSON, 0.9, box, points)


def run(engine, detections, frames=30, start=0.0):
    events, people = [], []
    for i in range(frames):
        people, new = engine.update(detections, start + i * 0.1, SIZE)
        events += [e for e in new if e.record]
    return people, events


def test_something_without_a_skeleton_is_not_judged():
    people, events = run(ViolationEngine(require_skeleton=True), [person()])
    assert people == [] and events == []


def test_person_with_a_skeleton_is_judged():
    people, events = run(ViolationEngine(require_skeleton=True), [person(STANDING)])
    assert len(people) == 1 and len(events) == 1


def test_losing_the_skeleton_does_not_hide_a_worker():
    engine = ViolationEngine(require_skeleton=True)
    run(engine, [person(STANDING)], frames=5)
    people, events = run(engine, [person()], start=0.5)
    assert len(people) == 1 and len(events) == 1


def test_without_the_requirement_boxes_are_enough():
    assert len(run(ViolationEngine(), [person()])[1]) == 1


def zone_events(points, zone_points):
    engine = ViolationEngine(require_skeleton=True)
    engine.zones = [Zone("A", zone_points, NO_ENTRY_RULE)]
    return run(engine, [person(points), Detection(HELMET, 0.9, (450.0, 200.0, 550.0, 300.0))])[1]


def test_a_hand_inside_the_zone_counts_even_with_feet_outside():
    events = zone_events(REACHING, [(0.8, 0.3), (0.95, 0.3), (0.95, 0.4), (0.8, 0.4)])
    assert len(events) == 1 and events[0].missing == ("entry",) and events[0].zone


def test_a_bone_crossing_the_zone_counts_when_no_joint_is_inside():
    # a thin zone between elbow (x=700) and wrist (x=850)
    assert len(zone_events(REACHING, [(0.76, 0.3), (0.79, 0.3), (0.79, 0.4), (0.76, 0.4)])) == 1


def test_box_overlapping_the_zone_without_any_body_part_does_not_count():
    # inside the person box (lower left corner) but away from every joint and bone
    assert zone_events(STANDING, [(0.40, 0.6), (0.43, 0.6), (0.43, 0.7), (0.40, 0.7)]) == []


def test_untrusted_points_are_ignored():
    assert body_samples(skeleton()) == []


def test_one_skeleton_confirms_only_the_best_matching_person():
    near, far = person(box=BOX), person(box=(430.0, 200.0, 630.0, 800.0))
    out = attach([far, near], [(BOX, STANDING)])
    assert out[0].keypoints is None and out[1].keypoints == STANDING


def test_too_few_points_are_not_a_skeleton():
    assert attach([person()], [(BOX, skeleton(p0=(500, 250), p5=(450, 350)))])[0].keypoints is None


def test_real_models_confirm_the_worker_in_a_photo():
    detector = SkeletonDetector(Detector(config.MODEL_PATH, config.IMG_SIZE, config.CONF, config.GEAR_CONF),
                                config.POSE_MODEL_PATH, config.POSE_IMG_SIZE)
    found = detector.detect(cv2.imread(str(config.ROOT / "testdata/images/hardhat_worker_pd.jpg")))
    assert [d for d in found if d.role == PERSON and d.keypoints]
    drawing = detector.detect(cv2.imread(str(config.ROOT / "testdata/non_human/jacket_stand_dummy.jpg")))
    assert not [d for d in drawing if d.keypoints]
