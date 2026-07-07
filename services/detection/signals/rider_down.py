"""Rider-down detection — the project's second novel contribution (plan.md §7.4).

This module implements the primary heuristic only: sustained aspect-ratio flip
(standing -> lying) plus proximity to a two-wheeler that shows an impact
signature (sharp deceleration or a sharp bbox-aspect change of its own),
plus the person staying immobile. Pose-based confirmation (E3-T3) layers on
top of this in a subclass, boosting the score without changing this logic.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from services.detection.signals.base import Signal, SignalResult
from services.detection.tracker_ctx import FrameContext, TrackState

ASPECT_LYING_THRESHOLD = 1.3
SUSTAINED_DURATION_S = 2.0
PROXIMITY_MULTIPLIER = 1.5
VEHICLE_VELOCITY_DROP_THRESHOLD = 15.0  # px/frame
VEHICLE_ASPECT_CHANGE_THRESHOLD = 0.5  # fractional change counted as "sharp"
PERSON_SPEED_THRESHOLD = 3.0  # px/s
VELOCITY_WINDOW_S = 0.5
EVENT_CORRELATION_WINDOW_S = 3.0  # how close a vehicle's impact signature must be to the fall's onset
PRIMARY_SCORE = 0.85

VEHICLE_CLASSES = {"motorcycle", "bicycle"}


@dataclass
class _Sample:
    timestamp_s: float
    value: float


class RiderDownSignal(Signal):
    name = "rider_down"

    def __init__(self):
        self._lying_since: dict[int, float | None] = {}
        self._person_speed_ok_since: dict[int, float | None] = {}
        self._vehicle_velocity_history: dict[int, deque] = {}
        self._vehicle_aspect_history: dict[int, deque] = {}
        self._vehicle_last_event_ts: dict[int, float] = {}

    def _record_vehicle_history(self, track: TrackState, ts: float) -> None:
        vel_hist = self._vehicle_velocity_history.setdefault(track.track_id, deque(maxlen=50))
        vel_hist.append(_Sample(ts, math.hypot(*track.velocity)))
        aspect_hist = self._vehicle_aspect_history.setdefault(track.track_id, deque(maxlen=50))
        aspect_hist.append(_Sample(ts, track.bbox_aspect))

    def _vehicle_velocity_drop(self, track_id: int, ts: float) -> float:
        hist = self._vehicle_velocity_history.get(track_id)
        if not hist or len(hist) < 2:
            return 0.0
        target_ts = ts - VELOCITY_WINDOW_S
        past = min(hist, key=lambda s: abs(s.timestamp_s - target_ts))
        return abs(hist[-1].value - past.value)

    def _vehicle_aspect_change(self, track_id: int, ts: float) -> float:
        hist = self._vehicle_aspect_history.get(track_id)
        if not hist or len(hist) < 2:
            return 0.0
        target_ts = ts - VELOCITY_WINDOW_S
        past = min(hist, key=lambda s: abs(s.timestamp_s - target_ts))
        if past.value == 0:
            return 0.0
        return abs(hist[-1].value - past.value) / past.value

    def _score_for_person(self, person: TrackState, vehicle: TrackState, duration: float, event_ts: float) -> tuple[float, str]:
        return PRIMARY_SCORE, (
            f"rider_down: person {person.track_id} aspect {person.bbox_aspect:.2f} sustained {duration:.1f}s, "
            f"near vehicle {vehicle.track_id} impact signature at t={event_ts:.1f}s"
        )

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        ts = frame_ctx.timestamp_s
        result = SignalResult()
        tracks = frame_ctx.tracks

        vehicle_tracks = [t for t in tracks.values() if t.cls in VEHICLE_CLASSES]
        for v in vehicle_tracks:
            self._record_vehicle_history(v, ts)
            dv = self._vehicle_velocity_drop(v.track_id, ts)
            aspect_change = self._vehicle_aspect_change(v.track_id, ts)
            if dv > VEHICLE_VELOCITY_DROP_THRESHOLD or aspect_change > VEHICLE_ASPECT_CHANGE_THRESHOLD:
                self._vehicle_last_event_ts[v.track_id] = ts

        for t in tracks.values():
            if t.cls != "person":
                continue

            if t.bbox_aspect > ASPECT_LYING_THRESHOLD:
                if self._lying_since.get(t.track_id) is None:
                    self._lying_since[t.track_id] = ts
            else:
                self._lying_since[t.track_id] = None
                self._person_speed_ok_since[t.track_id] = None
                continue

            speed = math.hypot(*t.velocity)
            if speed < PERSON_SPEED_THRESHOLD:
                if self._person_speed_ok_since.get(t.track_id) is None:
                    self._person_speed_ok_since[t.track_id] = ts
            else:
                self._person_speed_ok_since[t.track_id] = None

            lying_start = self._lying_since.get(t.track_id)
            speed_ok_start = self._person_speed_ok_since.get(t.track_id)
            if lying_start is None or speed_ok_start is None:
                continue

            duration = ts - max(lying_start, speed_ok_start)
            if duration < SUSTAINED_DURATION_S:
                continue

            nearby_vehicle = None
            for v in vehicle_tracks:
                dist = math.hypot(t.centroid[0] - v.centroid[0], t.centroid[1] - v.centroid[1])
                v_diag = math.hypot(v.bbox[2] - v.bbox[0], v.bbox[3] - v.bbox[1])
                if dist <= PROXIMITY_MULTIPLIER * v_diag:
                    nearby_vehicle = v
                    break
            if nearby_vehicle is None:
                continue

            event_ts = self._vehicle_last_event_ts.get(nearby_vehicle.track_id)
            if event_ts is None or abs(event_ts - lying_start) > EVENT_CORRELATION_WINDOW_S:
                continue

            score, reason = self._score_for_person(t, nearby_vehicle, duration, event_ts)
            result.score = max(result.score, score)
            result.reasons.append(reason)
            result.fired_track_ids.extend([t.track_id, nearby_vehicle.track_id])

        return result
