from services.detection.signals.stationary import StationarySignal
from tests.conftest import SyntheticTrack

FPS = 2.0  # 0.5s per synthetic frame, keeps frame counts low for multi-second scenarios

LIVE_LANE = [(0, 0), (1000, 0), (1000, 200), (0, 200)]


def _stationary_frames(n_frames):
    return [[SyntheticTrack(1, "car", (500, 50, 540, 90))] for _ in range(n_frames)]


def test_stationary_vehicle_fires_after_20s(frame_context_builder):
    # 45 frames @ 2fps = 22.5s of continuous rest -> well past the 20s full-ramp point.
    contexts = frame_context_builder(_stationary_frames(45), fps=FPS)
    signal = StationarySignal(live_lane_polygon=LIVE_LANE)

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) >= 0.9


def test_stop_and_go_does_not_fire(frame_context_builder):
    frames = []
    # stationary for 4s (8 frames @ 2fps)
    frames += [[SyntheticTrack(1, "car", (500, 50, 540, 90))] for _ in range(8)]
    # large jump -> resets the stationary streak
    frames += [[SyntheticTrack(1, "car", (800, 50, 840, 90))]]
    # stationary again for 5.5s (11 frames @ 2fps) — still under the 8s threshold
    frames += [[SyntheticTrack(1, "car", (800, 50, 840, 90))] for _ in range(11)]

    contexts = frame_context_builder(frames, fps=FPS)
    signal = StationarySignal(live_lane_polygon=LIVE_LANE)

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0


def test_stationary_outside_live_lane_does_not_fire(frame_context_builder):
    # Same 22.5s of rest as the firing test, but positioned outside the live_lane polygon.
    frames = [[SyntheticTrack(1, "car", (1500, 50, 1540, 90))] for _ in range(45)]
    contexts = frame_context_builder(frames, fps=FPS)
    signal = StationarySignal(live_lane_polygon=LIVE_LANE)

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0
