"""Direct-impact collision signal (plan.md §7.4).

Two-stage detection:
  1. Two tracks overlap or come into near-contact, and at least one shows a
     sudden velocity change (impact signature) -> score 0.6, "pending" state.
  2. Within a following window, if either involved track is then observed
     stationary for >= STATIONARY_DURATION_S -> score escalates to 0.95.

Note on timing: plan.md §7.4 describes confirmation as happening "within 3s"
of the initial event. Velocity is smoothed over a 5-frame window (tracker_ctx),
so a real deceleration-to-zero takes a few frames to read as fully stationary —
that lag plus the 3s stationary-duration requirement itself can exceed a hard
3s confirmation deadline. PENDING_EXPIRY_S is therefore set longer than the
literal "3s" to make confirmation reliably achievable; STATIONARY_DURATION_S
(the actual physical requirement) stays at the spec's 3s.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

from services.detection.signals.base import Signal, SignalResult
from services.detection.tracker_ctx import FrameContext, TrackState

VELOCITY_DROP_THRESHOLD = 15.0  # px/frame
VELOCITY_WINDOW_S = 0.5
STATIONARY_SPEED_THRESHOLD = 3.0  # px/s
STATIONARY_DURATION_S = 3.0
PENDING_EXPIRY_S = 15.0  # see module docstring
INITIAL_SCORE = 0.6
CONFIRMED_SCORE = 0.95


def _bbox_half_diagonal(bbox: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = bbox
    return math.hypot(x2 - x1, y2 - y1) / 2


def _centroid_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _bboxes_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


@dataclass
class _VelocitySample:
    timestamp_s: float
    magnitude: float


@dataclass
class _PendingCollision:
    event_ts: float
    track_ids: tuple[int, int]


class CollisionSignal(Signal):
    name = "collision"

    def __init__(
        self,
        velocity_drop_threshold: float = VELOCITY_DROP_THRESHOLD,
        velocity_window_s: float = VELOCITY_WINDOW_S,
        stationary_speed_threshold: float = STATIONARY_SPEED_THRESHOLD,
        stationary_duration_s: float = STATIONARY_DURATION_S,
        pending_expiry_s: float = PENDING_EXPIRY_S,
        initial_score: float = INITIAL_SCORE,
        confirmed_score: float = CONFIRMED_SCORE,
    ):
        self.velocity_drop_threshold = velocity_drop_threshold
        self.velocity_window_s = velocity_window_s
        self.stationary_speed_threshold = stationary_speed_threshold
        self.stationary_duration_s = stationary_duration_s
        self.pending_expiry_s = pending_expiry_s
        self.initial_score = initial_score
        self.confirmed_score = confirmed_score

        self._velocity_history: dict[int, deque] = {}
        self._stationary_since: dict[int, float | None] = {}
        self._pending: list[_PendingCollision] = []

    def _record_velocity(self, track: TrackState, ts: float) -> None:
        mag = math.hypot(*track.velocity)
        hist = self._velocity_history.setdefault(track.track_id, deque(maxlen=50))
        hist.append(_VelocitySample(ts, mag))

    def _velocity_delta(self, track_id: int, ts: float) -> float:
        hist = self._velocity_history.get(track_id)
        if not hist or len(hist) < 2:
            return 0.0
        target_ts = ts - self.velocity_window_s
        past = min(hist, key=lambda s: abs(s.timestamp_s - target_ts))
        current = hist[-1]
        return abs(current.magnitude - past.magnitude)

    def _update_stationary(self, track: TrackState, ts: float) -> None:
        speed = math.hypot(*track.velocity)
        if speed < self.stationary_speed_threshold:
            if self._stationary_since.get(track.track_id) is None:
                self._stationary_since[track.track_id] = ts
        else:
            self._stationary_since[track.track_id] = None

    def _stationary_duration(self, track_id: int, ts: float) -> float:
        start = self._stationary_since.get(track_id)
        return 0.0 if start is None else ts - start

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        ts = frame_ctx.timestamp_s
        tracks = frame_ctx.tracks

        for track in tracks.values():
            self._record_velocity(track, ts)
            self._update_stationary(track, ts)

        result = SignalResult()

        still_pending = []
        for pending in self._pending:
            if ts - pending.event_ts > self.pending_expiry_s:
                continue
            confirmed = any(
                self._stationary_duration(tid, ts) >= self.stationary_duration_s for tid in pending.track_ids
            )
            if confirmed:
                result.score = max(result.score, self.confirmed_score)
                result.reasons.append(f"collision: tracks {pending.track_ids} stationary-confirmed after impact")
                result.fired_track_ids.extend(pending.track_ids)
            else:
                still_pending.append(pending)
                result.score = max(result.score, self.initial_score)
                result.reasons.append(f"collision: tracks {pending.track_ids} overlap+velocity-drop (awaiting confirmation)")
                result.fired_track_ids.extend(pending.track_ids)
        self._pending = still_pending

        pending_pairs = {p.track_ids for p in self._pending}
        track_list = list(tracks.values())
        for i in range(len(track_list)):
            for j in range(i + 1, len(track_list)):
                a, b = track_list[i], track_list[j]
                pair_key = tuple(sorted((a.track_id, b.track_id)))
                if pair_key in pending_pairs:
                    continue
                overlap = _bboxes_overlap(a.bbox, b.bbox)
                near_contact = _centroid_distance(a.centroid, b.centroid) < (
                    _bbox_half_diagonal(a.bbox) + _bbox_half_diagonal(b.bbox)
                )
                if not (overlap or near_contact):
                    continue
                dv_a = self._velocity_delta(a.track_id, ts)
                dv_b = self._velocity_delta(b.track_id, ts)
                if dv_a > self.velocity_drop_threshold or dv_b > self.velocity_drop_threshold:
                    self._pending.append(_PendingCollision(event_ts=ts, track_ids=pair_key))
                    result.score = max(result.score, self.initial_score)
                    result.reasons.append(
                        f"collision: tracks {pair_key} overlap/near-contact + velocity change {max(dv_a, dv_b):.1f}px/frame"
                    )
                    result.fired_track_ids.extend(pair_key)

        return result
