import re

from services.detection.config import FusionParams, OverrideRule
from services.detection.fusion import FusionEngine
from services.detection.signals.base import SignalResult
from services.detection.tracker_ctx import FrameContext, TrackState

INCIDENT_ID_RE = re.compile(r"^inc_\d{14}_\d{3}$")


def _track(track_id, x, y):
    return TrackState(
        track_id=track_id,
        cls="car",
        bbox=(x - 10, y - 10, x + 10, y + 10),
        centroid=(x, y),
        velocity=(0.0, 0.0),
        bbox_aspect=1.0,
        age_frames=1,
    )


def _ctx(ts, tracks):
    return FrameContext(frame_index=0, timestamp_s=ts, tracks={t.track_id: t for t in tracks})


def _params(**overrides):
    defaults = dict(
        weights={"collision": 0.35, "rider_down": 0.30, "crowd": 0.20, "flow": 0.15},
        candidate_threshold=0.5,
        override_rules=[
            OverrideRule(signal="collision", min_score=0.9),
            OverrideRule(signal="rider_down", min_score=0.85),
        ],
        cooldown_seconds=60.0,
        cooldown_grid=(4, 4),
    )
    defaults.update(overrides)
    return FusionParams(**defaults)


def _engine(**param_overrides):
    engine = FusionEngine(_params(**param_overrides), camera_id="cam1", mode="city")
    engine.configure_frame_size(1000, 1000)
    return engine


def test_weighted_sum_fires_without_any_override():
    engine = _engine()
    ctx = _ctx(10.0, [_track(1, 500, 500)])
    results = {
        "collision": SignalResult(score=0.7, reasons=["collision: x"], fired_track_ids=[1]),
        "rider_down": SignalResult(score=0.6, reasons=["rider_down: y"], fired_track_ids=[1]),
        "crowd": SignalResult(score=0.6, reasons=["crowd: z"], fired_track_ids=[1]),
        "flow": SignalResult(score=0.0, reasons=[], fired_track_ids=[]),
    }
    # weighted = 0.7*.35 + 0.6*.30 + 0.6*.20 = 0.245+0.18+0.12 = 0.545 >= 0.5, no individual score meets its override
    candidate = engine.update(ctx, results)

    assert candidate is not None
    assert INCIDENT_ID_RE.match(candidate.incident_id)
    assert candidate.camera_id == "cam1"
    assert candidate.mode == "city"
    assert candidate.signals == {"collision": 0.7, "rider_down": 0.6, "crowd": 0.6, "flow": 0.0}
    assert candidate.reasons == ["collision: x", "rider_down: y", "crowd: z"]
    assert candidate.fired_track_ids == [1]


def test_override_fires_below_weighted_threshold():
    engine = _engine()
    ctx = _ctx(10.0, [_track(1, 500, 500)])
    results = {
        "collision": SignalResult(score=0.0),
        "rider_down": SignalResult(score=0.85, reasons=["rider_down: fall"], fired_track_ids=[1]),
        "crowd": SignalResult(score=0.0),
        "flow": SignalResult(score=0.0),
    }
    # weighted = 0.85*.30 = 0.255 < 0.5, but rider_down meets its override (>=0.85)
    candidate = engine.update(ctx, results)

    assert candidate is not None
    assert candidate.signals["rider_down"] == 0.85


def test_below_threshold_and_no_override_returns_none():
    engine = _engine()
    ctx = _ctx(10.0, [_track(1, 500, 500)])
    results = {
        "collision": SignalResult(score=0.1),
        "rider_down": SignalResult(score=0.1),
        "crowd": SignalResult(score=0.1),
        "flow": SignalResult(score=0.1),
    }
    assert engine.update(ctx, results) is None


def test_cooldown_suppresses_same_cell_then_expires():
    engine = _engine(cooldown_seconds=60.0)
    track = _track(1, 500, 500)
    results = {
        "collision": SignalResult(score=0.0),
        "rider_down": SignalResult(score=0.85, reasons=["fall"], fired_track_ids=[1]),
        "crowd": SignalResult(score=0.0),
        "flow": SignalResult(score=0.0),
    }

    first = engine.update(_ctx(10.0, [track]), results)
    assert first is not None

    suppressed = engine.update(_ctx(40.0, [track]), results)  # +30s, still within 60s cooldown
    assert suppressed is None

    allowed = engine.update(_ctx(71.0, [track]), results)  # +61s from first fire, cooldown expired
    assert allowed is not None


def test_different_cell_not_suppressed_by_cooldown():
    engine = _engine(cooldown_seconds=60.0)
    results = {
        "collision": SignalResult(score=0.0),
        "rider_down": SignalResult(score=0.85, reasons=["fall"], fired_track_ids=[1]),
        "crowd": SignalResult(score=0.0),
        "flow": SignalResult(score=0.0),
    }

    first = engine.update(_ctx(10.0, [_track(1, 100, 100)]), results)
    assert first is not None

    # far-away cell, well within cooldown window time-wise, but a different grid cell
    second = engine.update(_ctx(15.0, [_track(1, 900, 900)]), results)
    assert second is not None
