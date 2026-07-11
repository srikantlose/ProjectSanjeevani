from services.detection.severity import assess
from services.detection.signals.base import SignalResult
from services.detection.tracker_ctx import FrameContext, TrackState


def _track(track_id, cls):
    return TrackState(
        track_id=track_id, cls=cls, bbox=(0, 0, 10, 10), centroid=(5, 5), velocity=(0.0, 0.0),
        bbox_aspect=1.0, age_frames=1,
    )


def _ctx(*tracks):
    return FrameContext(frame_index=0, timestamp_s=0.0, tracks={t.track_id: t for t in tracks})


def test_rider_down_high():
    results = {"rider_down": SignalResult(score=0.9)}
    severity, reasons = assess(results, _ctx())
    assert severity == "HIGH"
    assert any("rider down" in r for r in reasons)


def test_pedestrian_hit_high():
    ctx = _ctx(_track(1, "person"), _track(2, "car"))
    results = {"collision": SignalResult(score=0.95, fired_track_ids=[1, 2])}
    severity, reasons = assess(results, ctx)
    assert severity == "HIGH"
    assert any("pedestrian hit" in r for r in reasons)


def test_three_plus_vehicles_high():
    ctx = _ctx(_track(1, "car"), _track(2, "car"), _track(3, "truck"))
    results = {"collision": SignalResult(score=0.95, fired_track_ids=[1, 2, 3])}
    severity, reasons = assess(results, ctx)
    assert severity == "HIGH"
    assert any("multi-vehicle" in r for r in reasons)


def test_two_vehicles_with_flow_impact_medium():
    ctx = _ctx(_track(1, "car"), _track(2, "car"))
    results = {
        "collision": SignalResult(score=0.95, fired_track_ids=[1, 2]),
        "flow": SignalResult(score=0.4),
    }
    severity, reasons = assess(results, ctx)
    assert severity == "MEDIUM"
    assert any("flow impact" in r for r in reasons)


def test_two_vehicles_without_flow_impact_is_low():
    ctx = _ctx(_track(1, "car"), _track(2, "car"))
    results = {
        "collision": SignalResult(score=0.95, fired_track_ids=[1, 2]),
        "flow": SignalResult(score=0.0),
    }
    severity, reasons = assess(results, ctx)
    assert severity == "LOW"


def test_stalled_vehicle_with_collision_indicators_high():
    results = {
        "stationary": SignalResult(score=0.9),
        "collision": SignalResult(score=0.65),
    }
    severity, reasons = assess(results, _ctx())
    assert severity == "HIGH"
    assert any("stalled vehicle with collision" in r for r in reasons)


def test_stalled_vehicle_alone_medium():
    results = {
        "stationary": SignalResult(score=0.9),
        "collision": SignalResult(score=0.2),
    }
    severity, reasons = assess(results, _ctx())
    assert severity == "MEDIUM"
    assert any("stalled vehicle in live lane" in r for r in reasons)


def test_nothing_matched_low_fallback():
    results = {
        "collision": SignalResult(score=0.1),
        "rider_down": SignalResult(score=0.2),
        "crowd": SignalResult(score=0.3),
        "flow": SignalResult(score=0.1),
    }
    severity, reasons = assess(results, _ctx())
    assert severity == "LOW"
    assert len(reasons) == 1
