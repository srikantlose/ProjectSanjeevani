from services.detection.signals.rider_down import RiderDownSignal
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
