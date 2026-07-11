"""Config system: loads a camera YAML + its mode YAML into a resolved EngineConfig (plan.md §7.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_MODES_DIR = Path(__file__).resolve().parent.parent.parent / "configs" / "modes"
_REQUIRED_CAMERA_FIELDS = ("camera_id", "mode", "source_video", "location")

Point = tuple[float, float]


@dataclass
class DetectorParams:
    weights: str = "models/yolo11s.pt"
    imgsz: int = 960
    conf: float = 0.30
    iou: float = 0.5
    classes: list[str] = field(
        default_factory=lambda: ["person", "bicycle", "car", "motorcycle", "bus", "truck"]
    )
    device: str = "auto"


@dataclass
class ProcessingParams:
    target_fps: float = 10.0
    speed_factor: float = 1.0


@dataclass
class OverrideRule:
    signal: str
    min_score: float


@dataclass
class FusionParams:
    weights: dict[str, float]
    candidate_threshold: float
    override_rules: list[OverrideRule]
    cooldown_seconds: float
    cooldown_grid: tuple[int, int]


@dataclass
class CameraLocation:
    lat: float
    lon: float
    label: str


@dataclass
class ExclusionZone:
    name: str
    polygon: list[Point]


@dataclass
class CameraConfig:
    camera_id: str
    mode: str
    source_video: str
    location: CameraLocation
    rois: dict[str, list[Point]] = field(default_factory=dict)
    exclusion_zones: list[ExclusionZone] = field(default_factory=list)
    count_lines: dict[str, tuple[Point, Point]] = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)


@dataclass
class EngineConfig:
    camera: CameraConfig
    detector: DetectorParams
    processing: ProcessingParams
    fusion: FusionParams
    signals: dict[str, dict]


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_engine_config(camera_yaml_path: str | Path) -> EngineConfig:
    camera_yaml_path = Path(camera_yaml_path)
    with open(camera_yaml_path) as f:
        camera_raw = yaml.safe_load(f) or {}

    for required in _REQUIRED_CAMERA_FIELDS:
        if required not in camera_raw:
            raise ValueError(f"camera config {camera_yaml_path} missing required field: {required}")

    mode = camera_raw["mode"]
    mode_path = _MODES_DIR / f"{mode}.yaml"
    if not mode_path.exists():
        raise ValueError(f"unknown mode '{mode}': no such file {mode_path}")
    with open(mode_path) as f:
        mode_raw = yaml.safe_load(f) or {}

    overrides = camera_raw.get("overrides") or {}
    merged = _deep_merge(mode_raw, overrides)

    location_raw = camera_raw["location"]
    location = CameraLocation(lat=location_raw["lat"], lon=location_raw["lon"], label=location_raw["label"])

    rois_raw = camera_raw.get("rois") or {}
    rois = {name: [tuple(p) for p in polygon] for name, polygon in rois_raw.items()}

    exclusion_zones = [
        ExclusionZone(name=z["name"], polygon=[tuple(p) for p in z["polygon"]])
        for z in camera_raw.get("exclusion_zones", [])
    ]

    count_lines_raw = camera_raw.get("count_lines") or {}
    count_lines = {name: (tuple(cl["p1"]), tuple(cl["p2"])) for name, cl in count_lines_raw.items()}

    camera = CameraConfig(
        camera_id=camera_raw["camera_id"],
        mode=mode,
        source_video=camera_raw["source_video"],
        location=location,
        rois=rois,
        exclusion_zones=exclusion_zones,
        count_lines=count_lines,
        overrides=overrides,
    )

    detector = DetectorParams(**merged.get("detector", {}))
    processing = ProcessingParams(**merged.get("processing", {}))

    fusion_raw = merged["fusion"]
    fusion = FusionParams(
        weights=fusion_raw["weights"],
        candidate_threshold=fusion_raw["candidate_threshold"],
        override_rules=[OverrideRule(**r) for r in fusion_raw.get("override_rules", [])],
        cooldown_seconds=fusion_raw["cooldown_seconds"],
        cooldown_grid=tuple(fusion_raw["cooldown_grid"]),
    )

    signals = merged.get("signals", {})

    return EngineConfig(camera=camera, detector=detector, processing=processing, fusion=fusion, signals=signals)
