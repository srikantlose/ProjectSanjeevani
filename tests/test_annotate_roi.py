"""AnnotationState is the pure-logic core of scripts/annotate_roi.py (E8-T0);
tested directly since the interactive OpenCV event loop needs a real display."""

import pytest
import yaml

from scripts.annotate_roi import AnnotationState


def test_road_and_live_lane_polygons_round_trip():
    state = AnnotationState()

    state.start_road()
    for p in [(10, 10), (100, 10), (100, 100), (10, 100)]:
        state.add_vertex(p)
    state.finish_shape()

    state.start_live_lane()
    for p in [(20, 20), (80, 20), (80, 80)]:
        state.add_vertex(p)
    state.finish_shape()

    assert state.rois["road"] == [(10, 10), (100, 10), (100, 100), (10, 100)]
    assert state.rois["live_lane"] == [(20, 20), (80, 20), (80, 80)]


def test_exclusion_zone_auto_naming():
    state = AnnotationState()

    name1 = state.start_exclusion_zone()
    for p in [(0, 0), (10, 0), (10, 10)]:
        state.add_vertex(p)
    state.finish_shape()

    name2 = state.start_exclusion_zone()
    for p in [(50, 50), (60, 50), (60, 60)]:
        state.add_vertex(p)
    state.finish_shape()

    assert name1 == "excl_1"
    assert name2 == "excl_2"
    assert [z["name"] for z in state.exclusion_zones] == ["excl_1", "excl_2"]
    assert state.exclusion_zones[0]["polygon"] == [(0, 0), (10, 0), (10, 10)]


def test_count_line_requires_exactly_two_points_and_can_be_renamed():
    state = AnnotationState()

    auto_name = state.start_count_line()
    state.add_vertex((5, 5))
    state.add_vertex((5, 50))

    with pytest.raises(ValueError):
        state.add_vertex((5, 100))  # a 3rd point on a line is rejected

    state.finish_shape(rename_to="entry_line")

    assert auto_name == "line_1"
    assert "entry_line" in state.count_lines
    assert state.count_lines["entry_line"] == {"p1": (5, 5), "p2": (5, 50)}


def test_undo_removes_last_vertex_only():
    state = AnnotationState()
    state.start_road()
    state.add_vertex((1, 1))
    state.add_vertex((2, 2))
    state.undo_vertex()
    state.add_vertex((3, 3))
    state.add_vertex((4, 4))
    state.finish_shape()

    assert state.rois["road"] == [(1, 1), (3, 3), (4, 4)]


def test_finish_shape_rejects_undersized_polygon():
    state = AnnotationState()
    state.start_road()
    state.add_vertex((1, 1))
    state.add_vertex((2, 2))
    with pytest.raises(ValueError):
        state.finish_shape()


def test_save_deep_merges_into_existing_camera_yaml_preserving_unrelated_keys(tmp_path):
    camera_yaml = tmp_path / "test_camera.yaml"
    camera_yaml.write_text(
        yaml.safe_dump(
            {
                "camera_id": "test_cam",
                "mode": "city",
                "source_video": "tests/fixtures/vtest.avi",
                "location": {"lat": 12.97, "lon": 77.60, "label": "Test"},
                "overrides": {"processing": {"speed_factor": 2.0}},
            }
        )
    )

    state = AnnotationState()
    state.start_road()
    for p in [(0, 0), (100, 0), (100, 100), (0, 100)]:
        state.add_vertex(p)
    state.finish_shape()

    name = state.start_count_line()
    state.add_vertex((10, 50))
    state.add_vertex((90, 50))
    state.finish_shape(rename_to=name)

    state.save(camera_yaml)

    saved = yaml.safe_load(camera_yaml.read_text())
    assert saved["camera_id"] == "test_cam"
    assert saved["mode"] == "city"
    assert saved["overrides"] == {"processing": {"speed_factor": 2.0}}
    assert saved["rois"]["road"] == [[0, 0], [100, 0], [100, 100], [0, 100]]
    assert saved["count_lines"]["line_1"] == {"p1": [10, 50], "p2": [90, 50]}


def test_saved_camera_yaml_loads_cleanly_via_load_engine_config(tmp_path):
    from services.detection.config import load_engine_config

    camera_yaml = tmp_path / "junction_cam.yaml"
    camera_yaml.write_text(
        yaml.safe_dump(
            {
                "camera_id": "junction_cam",
                "mode": "city",
                "source_video": "tests/fixtures/vtest.avi",
                "location": {"lat": 12.9730, "lon": 77.6194, "label": "Trinity Circle"},
            }
        )
    )

    state = AnnotationState()
    clicked_road = [(15.0, 15.0), (300.0, 15.0), (300.0, 400.0), (15.0, 400.0)]
    state.start_road()
    for p in clicked_road:
        state.add_vertex(p)
    state.finish_shape()

    state.start_live_lane()
    for p in [(50.0, 50.0), (250.0, 50.0), (250.0, 350.0)]:
        state.add_vertex(p)
    state.finish_shape()

    excl_name = state.start_exclusion_zone()
    for p in [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0)]:
        state.add_vertex(p)
    state.finish_shape()

    state.save(camera_yaml)

    config = load_engine_config(camera_yaml)

    assert config.camera.camera_id == "junction_cam"
    assert config.camera.rois["road"] == [tuple(p) for p in clicked_road]
    assert config.camera.rois["live_lane"] == [(50.0, 50.0), (250.0, 50.0), (250.0, 350.0)]
    assert config.camera.exclusion_zones[0].name == excl_name
    assert config.camera.exclusion_zones[0].polygon == [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0)]
