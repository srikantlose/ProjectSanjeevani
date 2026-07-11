"""Severity assessment — deterministic rule table, not learned (plan.md §7.5).

Kept deterministic (rather than a model) so the dashboard's WhyPanel can show
exactly which rule fired and why, in plain language.
"""

from __future__ import annotations

from services.detection.signals.base import SignalResult
from services.detection.tracker_ctx import FrameContext

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}

_LEVELS = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def assess(results: dict[str, SignalResult], ctx: FrameContext) -> tuple[str, list[str]]:
    level = 0
    reasons: list[str] = []

    def bump(new_level: str, reason: str) -> None:
        nonlocal level
        level = max(level, _LEVELS[new_level])
        reasons.append(reason)

    collision = results.get("collision")
    collision_ids = collision.fired_track_ids if collision else []
    involved_vehicle_ids = {
        tid for tid in collision_ids if tid in ctx.tracks and ctx.tracks[tid].cls in VEHICLE_CLASSES
    }
    pedestrian_hit = any(tid in ctx.tracks and ctx.tracks[tid].cls == "person" for tid in collision_ids)

    rider_down = results.get("rider_down")
    if rider_down is not None and rider_down.score >= 0.85:
        bump("HIGH", f"severity HIGH: rider down ({rider_down.score:.2f})")

    if pedestrian_hit:
        bump("HIGH", "severity HIGH: pedestrian hit")

    if len(involved_vehicle_ids) >= 3:
        bump("HIGH", f"severity HIGH: multi-vehicle collision ({len(involved_vehicle_ids)} vehicles)")
    elif len(involved_vehicle_ids) == 2:
        flow = results.get("flow")
        if flow is not None and flow.score > 0:
            bump("MEDIUM", "severity MEDIUM: two-vehicle collision with flow impact")

    stationary = results.get("stationary")
    if stationary is not None and stationary.score >= 0.85:
        collision_score = collision.score if collision else 0.0
        if collision_score >= 0.6:
            bump("HIGH", "severity HIGH: stalled vehicle with collision indicators")
        else:
            bump("MEDIUM", "severity MEDIUM: stalled vehicle in live lane")

    if level == 0:
        return "LOW", ["severity LOW: no high/medium rule matched"]
    return ("MEDIUM" if level == 1 else "HIGH"), reasons
