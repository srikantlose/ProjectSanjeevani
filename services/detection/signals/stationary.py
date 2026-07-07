"""Stationary-vehicle signal — highway mode's primary signal (plan.md §7.4)."""

from __future__ import annotations

import math

from shapely.geometry import Point, Polygon

from services.detection.signals.base import Signal, SignalResult
from services.detection.tracker_ctx import FrameContext

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}
SPEED_THRESHOLD = 3.0  # px/s
MIN_DURATION_S = 8.0
RAMP_FULL_DURATION_S = 20.0
INITIAL_SCORE = 0.5
MAX_SCORE = 0.9


class StationarySignal(Signal):
    name = "stationary"

    def __init__(self, live_lane_polygon: list[tuple[float, float]] | None = None):
        self._polygon = Polygon(live_lane_polygon) if live_lane_polygon else None
        self._stationary_since: dict[int, float | None] = {}

    def _in_lane(self, centroid: tuple[float, float]) -> bool:
        if self._polygon is None:
            return True  # no ROI configured -> treat the whole frame as the live lane
        return self._polygon.contains(Point(centroid))

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        ts = frame_ctx.timestamp_s
        result = SignalResult()

        for track in frame_ctx.tracks.values():
            if track.cls not in VEHICLE_CLASSES:
                continue
            if not self._in_lane(track.centroid):
                self._stationary_since[track.track_id] = None
                continue

            speed = math.hypot(*track.velocity)
            if speed >= SPEED_THRESHOLD:
                self._stationary_since[track.track_id] = None
                continue
            if self._stationary_since.get(track.track_id) is None:
                self._stationary_since[track.track_id] = ts

            duration = ts - self._stationary_since[track.track_id]
            if duration < MIN_DURATION_S:
                continue

            ramp = min(1.0, (duration - MIN_DURATION_S) / (RAMP_FULL_DURATION_S - MIN_DURATION_S))
            score = INITIAL_SCORE + ramp * (MAX_SCORE - INITIAL_SCORE)
            result.score = max(result.score, score)
            result.reasons.append(f"stationary: track {track.track_id} at rest for {duration:.1f}s")
            result.fired_track_ids.append(track.track_id)

        return result
