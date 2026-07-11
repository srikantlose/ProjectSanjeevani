import numpy as np

from services.detection.detector import Detector
from services.detection.signals.rider_down import (
    PoseConfirmedRiderDownSignal,
    RiderDownSignal,
    _default_pose_checker,
)
from services.detection.video_source import VideoSource
from tests.conftest import SyntheticTrack

FPS = 5.0  # 0.2s per frame


def _moving_then_stopped_positions(n_pre, n_post, start_x=0.0, step=20.0):
    positions = [start_x + i * step for i in range(n_pre)]
    stop_x = positions[-1] if positions else start_x
    positions += [stop_x] * n_post
    return positions


def _standing_bbox(x, y):
    return (x - 8, y - 20, x + 8, y + 20)  # width 16, height 40 -> aspect 0.4


def _lying_bbox(x, y):
    return (x - 32, y - 10, x + 32, y + 10)  # width 64, height 20 -> aspect 3.2


def _motorcycle_bbox(x, y):
    return (x - 20, y - 15, x + 20, y + 15)  # width 40, height 30 -> aspect 1.33


def test_rider_down_fires_after_sustained_fall_near_decelerating_bike(frame_context_builder):
    n_pre, n_post = 10, 20
    xs = _moving_then_stopped_positions(n_pre, n_post)
    y = 100.0

    frames = []
    for i, x in enumerate(xs):
        moto = SyntheticTrack(1, "motorcycle", _motorcycle_bbox(x, y))
        if i < n_pre:
            person = SyntheticTrack(2, "person", _standing_bbox(x, y))
        else:
            person = SyntheticTrack(2, "person", _lying_bbox(x, y))
        frames.append([moto, person])

    contexts = frame_context_builder(frames, fps=FPS)
    signal = RiderDownSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) >= 0.85


def test_brief_crouch_does_not_fire(frame_context_builder):
    n_pre, n_crouch, n_after = 10, 3, 20  # crouch lasts 0.6s at fps=5 -- well under the 2s sustain requirement
    xs = _moving_then_stopped_positions(n_pre, n_crouch + n_after)
    y = 100.0

    frames = []
    for i, x in enumerate(xs):
        moto = SyntheticTrack(1, "motorcycle", _motorcycle_bbox(x, y))
        if n_pre <= i < n_pre + n_crouch:
            person = SyntheticTrack(2, "person", _lying_bbox(x, y))
        else:
            person = SyntheticTrack(2, "person", _standing_bbox(x, y))
        frames.append([moto, person])

    contexts = frame_context_builder(frames, fps=FPS)
    signal = RiderDownSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0


def _fall_frames():
    n_pre, n_post = 10, 20
    xs = _moving_then_stopped_positions(n_pre, n_post)
    y = 100.0
    frames = []
    for i, x in enumerate(xs):
        moto = SyntheticTrack(1, "motorcycle", _motorcycle_bbox(x, y))
        if i < n_pre:
            person = SyntheticTrack(2, "person", _standing_bbox(x, y))
        else:
            person = SyntheticTrack(2, "person", _lying_bbox(x, y))
        frames.append([moto, person])
    return frames


def test_pose_confirmation_boosts_score_when_checker_confirms_lying(frame_context_builder):
    contexts = frame_context_builder(_fall_frames(), fps=FPS)
    signal = PoseConfirmedRiderDownSignal(pose_checker=lambda crop: True, check_every_n_frames=1)
    dummy_image = np.zeros((600, 900, 3), dtype=np.uint8)

    scores, reasons = [], []
    for ctx in contexts:
        signal.set_current_frame_image(dummy_image)
        result = signal.update(ctx)
        scores.append(result.score)
        reasons.extend(result.reasons)

    assert max(scores) >= 0.95
    assert any("pose_confirmed_lying" in r for r in reasons)


def test_pose_confirmation_stays_at_primary_score_when_checker_denies(frame_context_builder):
    contexts = frame_context_builder(_fall_frames(), fps=FPS)
    signal = PoseConfirmedRiderDownSignal(pose_checker=lambda crop: False, check_every_n_frames=1)
    dummy_image = np.zeros((600, 900, 3), dtype=np.uint8)

    scores = []
    for ctx in contexts:
        signal.set_current_frame_image(dummy_image)
        scores.append(signal.update(ctx).score)

    assert max(scores) == 0.85


def test_default_pose_checker_smoke_on_real_upright_person(vtest_video):
    detector = Detector()
    src = VideoSource(vtest_video, target_fps=10, speed_factor=20.0)
    frame = next(iter(src))
    detections = detector.track(frame.image)
    person_dets = [d for d in detections if d.cls == "person"]
    assert person_dets, "expected at least one person detection in the first vtest frame"

    x1, y1, x2, y2 = person_dets[0].bbox
    x1, y1 = max(0, int(x1) - 10), max(0, int(y1) - 10)
    x2, y2 = int(x2) + 10, int(y2) + 10
    crop = frame.image[y1:y2, x1:x2]

    checker = _default_pose_checker()
    assert checker(crop) is False  # upright pedestrian -- must not raise, must not read as lying
