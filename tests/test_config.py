import pytest
import yaml

from services.detection.config import load_engine_config
from services.detection.signal_factory import build_signals
from services.detection.signals.collision import CollisionSignal
from services.detection.signals.crowd import CrowdSignal
from services.detection.signals.flow import FlowSignal
from services.detection.signals.rider_down import PoseConfirmedRiderDownSignal
from services.detection.signals.stationary import StationarySignal


def _write_camera_yaml(tmp_path, **extra):
    camera = {
        "camera_id": "test_cam",
        "mode": "city",
        "source_video": "tests/fixtures/vtest.avi",
        "location": {"lat": 12.9730, "lon": 77.6194, "label": "Test Junction"},
        "rois": {"road": [[0, 0], [100, 0], [100, 100], [0, 100]]},
    }
    camera.update(extra)
    path = tmp_path / "test_cam.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(camera, f)
    return path


def test_load_engine_config_resolves_city_mode(tmp_path):
    cfg = load_engine_config(_write_camera_yaml(tmp_path))

    assert cfg.camera.camera_id == "test_cam"
    assert cfg.camera.mode == "city"
    assert cfg.camera.location.label == "Test Junction"
    assert cfg.detector.weights == "models/yolo11s.pt"
    assert cfg.processing.target_fps == 10
    assert cfg.fusion.weights["collision"] == 0.35
    assert cfg.signals["crowd"]["eps_px"] == 40.0


def test_camera_override_wins(tmp_path):
    cfg = load_engine_config(_write_camera_yaml(tmp_path, overrides={"signals": {"crowd": {"eps_px": 99.0}}}))

    assert cfg.signals["crowd"]["eps_px"] == 99.0
    # untouched sibling key from the mode default should survive the merge
    assert cfg.signals["crowd"]["min_samples"] == 4


def test_missing_required_field_raises(tmp_path):
    path = tmp_path / "bad_cam.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(
            {"mode": "city", "source_video": "x.mp4", "location": {"lat": 0, "lon": 0, "label": "x"}}, f
        )

    with pytest.raises(ValueError, match="camera_id"):
        load_engine_config(path)


def test_build_signals_city_mode(tmp_path):
    cfg = load_engine_config(_write_camera_yaml(tmp_path))
    signals = build_signals(cfg)

    assert len(signals) == 4
    assert {type(s) for s in signals} == {CollisionSignal, PoseConfirmedRiderDownSignal, CrowdSignal, FlowSignal}


def test_build_signals_highway_mode(tmp_path):
    camera = {
        "camera_id": "test_highway",
        "mode": "highway",
        "source_video": "tests/fixtures/vtest.avi",
        "location": {"lat": 13.0358, "lon": 77.5970, "label": "Test Highway"},
        "rois": {"live_lane": [[0, 0], [100, 0], [100, 100], [0, 100]]},
    }
    path = tmp_path / "test_highway.yaml"
    with open(path, "w") as f:
        yaml.safe_dump(camera, f)

    cfg = load_engine_config(path)
    signals = build_signals(cfg)

    assert len(signals) == 3
    assert {type(s) for s in signals} == {StationarySignal, CollisionSignal, FlowSignal}
