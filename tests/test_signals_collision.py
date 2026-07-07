from services.detection.signals.collision import CollisionSignal
from tests.conftest import SyntheticTrack

FPS = 10.0


def _collision_frames():
    """Two vehicles approach head-on at high speed, meet/overlap around frame 10,
    then both come to rest and stay stopped for a long tail — a clear impact."""
    frames = []
    n_approach = 10
    n_hold = 90  # 9s of rest at 10fps — plenty of margin for the 3s stationary confirmation

    # A starts at x=0 moving +30 px/frame, stops at x=300 (bbox width 40).
    # B starts at x=700 moving -30 px/frame, stops at x=320 (bbox width 40) -> overlaps A.
    a_stop_x, b_stop_x = 300.0, 320.0
    for f in range(n_approach):
        ax = f * 30.0
        bx = 700.0 - f * 30.0
        frames.append(
            [
                SyntheticTrack(1, "car", (ax, 0, ax + 40, 20)),
                SyntheticTrack(2, "car", (bx, 0, bx + 40, 20)),
            ]
        )
    for _ in range(n_hold):
        frames.append(
            [
                SyntheticTrack(1, "car", (a_stop_x, 0, a_stop_x + 40, 20)),
                SyntheticTrack(2, "car", (b_stop_x, 0, b_stop_x + 40, 20)),
            ]
        )
    return frames


def _normal_passing_traffic_frames():
    """Two vehicles moving steadily in parallel lanes, never overlapping, never stopping."""
    frames = []
    for f in range(60):
        frames.append(
            [
                SyntheticTrack(1, "car", (f * 15.0, 0, f * 15.0 + 40, 20)),
                SyntheticTrack(2, "car", (f * 15.0, 100, f * 15.0 + 40, 120)),
            ]
        )
    return frames


def test_collision_confirms_after_impact_and_rest(frame_context_builder):
    contexts = frame_context_builder(_collision_frames(), fps=FPS)
    signal = CollisionSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) >= 0.9


def test_normal_passing_traffic_does_not_fire(frame_context_builder):
    contexts = frame_context_builder(_normal_passing_traffic_frames(), fps=FPS)
    signal = CollisionSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) < 0.5
