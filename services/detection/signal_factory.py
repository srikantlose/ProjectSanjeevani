"""Builds the enabled signal modules for an EngineConfig (plan.md §7.3)."""

from __future__ import annotations

from services.detection.config import EngineConfig
from services.detection.signals.base import Signal
from services.detection.signals.collision import CollisionSignal
from services.detection.signals.crowd import CrowdSignal
from services.detection.signals.flow import FlowSignal
from services.detection.signals.rider_down import PoseConfirmedRiderDownSignal, RiderDownSignal
from services.detection.signals.stationary import StationarySignal

_KNOWN_SIGNALS = {"collision", "rider_down", "crowd", "flow", "stationary"}


def build_signals(cfg: EngineConfig) -> list[Signal]:
    signals: list[Signal] = []

    for name, raw_params in cfg.signals.items():
        if name not in _KNOWN_SIGNALS:
            raise ValueError(f"unknown signal config key: {name}")
        params = dict(raw_params)

        if name == "collision":
            signals.append(CollisionSignal(**params))
        elif name == "flow":
            signals.append(FlowSignal(count_lines=cfg.camera.count_lines, **params))
        elif name == "stationary":
            signals.append(StationarySignal(live_lane_polygon=cfg.camera.rois.get("live_lane"), **params))
        elif name == "crowd":
            exclusion_polygons = [z.polygon for z in cfg.camera.exclusion_zones]
            signals.append(
                CrowdSignal(road_polygon=cfg.camera.rois.get("road"), exclusion_zones=exclusion_polygons, **params)
            )
        elif name == "rider_down":
            pose_cfg = params.pop("pose", None)
            if pose_cfg and pose_cfg.get("enabled"):
                signals.append(
                    PoseConfirmedRiderDownSignal(
                        pose_weights=pose_cfg.get("weights", "models/yolo11s-pose.pt"),
                        check_every_n_frames=pose_cfg.get("check_every_n_frames", 3),
                        lying_angle_deg=pose_cfg.get("lying_angle_deg", 60.0),
                        confirmed_score=pose_cfg.get("confirmed_score", 0.95),
                        **params,
                    )
                )
            else:
                signals.append(RiderDownSignal(**params))

    return signals
