"""E8-T2: demo camera + scenario configs. source_video in both camera YAMLs is
a placeholder (tests/fixtures/vtest.avi) pending real footage from E8-T1 -- see
docs/data_checklist.md and PROGRESS.md. These tests confirm the configs are
wired correctly (load cleanly, run end-to-end, ROIs actually render in the
debug overlay) independent of what the real footage will eventually be.
"""

from pathlib import Path

import cv2
import numpy as np
import yaml

from services.detection.config import load_engine_config
from services.detection.engine import run

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"
JUNCTION_CAM_YAML = str(CONFIGS_DIR / "cameras" / "junction_cam.yaml")
HIGHWAY_CAM_YAML = str(CONFIGS_DIR / "cameras" / "highway_cam.yaml")


def test_junction_cam_loads_with_trinity_circle_location():
    cfg = load_engine_config(JUNCTION_CAM_YAML)
    assert cfg.camera.camera_id == "junction_cam"
    assert cfg.camera.mode == "city"
    assert cfg.camera.location.lat == 12.9730
    assert cfg.camera.location.lon == 77.6194
    assert "road" in cfg.camera.rois


def test_highway_cam_loads_with_hebbal_location():
    cfg = load_engine_config(HIGHWAY_CAM_YAML)
    assert cfg.camera.camera_id == "highway_cam"
    assert cfg.camera.mode == "highway"
    assert cfg.camera.location.lat == 13.0358
    assert cfg.camera.location.lon == 77.5970
    assert "live_lane" in cfg.camera.rois


def test_scenario_yamls_reference_valid_camera_configs():
    for scenario_name, expected_type in [("scenario1.yaml", "city_crowd_only"), ("scenario2.yaml", "highway_stationary")]:
        with open(CONFIGS_DIR / "scenarios" / scenario_name) as f:
            scenario = yaml.safe_load(f)

        assert scenario["scenario_id"] == scenario_name.removesuffix(".yaml")
        assert scenario["expected"]["type"] == expected_type
        assert "gt_event_time_s" in scenario["expected"]

        camera_yaml = CONFIGS_DIR.parent / scenario["camera_config"]
        cfg = load_engine_config(camera_yaml)
        assert cfg.camera.mode in ("city", "highway")


def _debug_overlay_shows_roi(camera_yaml: str, tmp_path: Path) -> bool:
    tmp_path.mkdir(parents=True, exist_ok=True)
    out_path = tmp_path / "debug_out.mp4"
    run(
        camera_yaml,
        headless=True,
        debug_overlay=True,
        speed_factor=30.0,
        max_frames=5,
        debug_overlay_output=str(out_path),
        evidence_out_root=str(tmp_path / "clips"),
    )

    cap = cv2.VideoCapture(str(out_path))
    assert cap.isOpened()
    found_roi_pixel = False
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if np.all(frame == [255, 255, 0], axis=-1).any():
            found_roi_pixel = True
            break
    cap.release()
    return found_roi_pixel


def test_junction_cam_debug_overlay_shows_road_roi(tmp_path):
    assert _debug_overlay_shows_roi(JUNCTION_CAM_YAML, tmp_path / "junction")


def test_highway_cam_debug_overlay_shows_live_lane_roi(tmp_path):
    assert _debug_overlay_shows_roi(HIGHWAY_CAM_YAML, tmp_path / "highway")
