"""Traffic-flow collapse signal (plan.md §7.4) — a supporting signal, never fires alone."""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field

from services.detection.signals.base import Signal, SignalResult
from services.detection.tracker_ctx import FrameContext

BIN_DURATION_S = 10.0
ROLLING_WINDOW_BINS = 30  # ~5 minutes of 10s bins
COLLAPSE_RATIO = 0.3
MIN_CONSECUTIVE_LOW_BINS = 2
FIRE_SCORE = 0.4

Point = tuple[float, float]


def _ccw(a: Point, b: Point, c: Point) -> float:
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    d1, d2 = _ccw(p3, p4, p1), _ccw(p3, p4, p2)
    d3, d4 = _ccw(p1, p2, p3), _ccw(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


@dataclass
class _ApproachState:
    p1: Point
    p2: Point
    bin_history: deque = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW_BINS))
    current_bin_index: int = -1
    current_bin_count: int = 0
    low_streak: int = 0


class FlowSignal(Signal):
    name = "flow"

    def __init__(self, count_lines: dict[str, tuple[Point, Point]]):
        self._approaches = {name: _ApproachState(p1=p1, p2=p2) for name, (p1, p2) in count_lines.items()}
        self._last_centroid: dict[int, Point] = {}

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        ts = frame_ctx.timestamp_s
        result = SignalResult()

        for track_id, track in frame_ctx.tracks.items():
            prev = self._last_centroid.get(track_id)
            curr = track.centroid
            if prev is not None:
                for state in self._approaches.values():
                    if _segments_intersect(prev, curr, state.p1, state.p2):
                        state.current_bin_count += 1
            self._last_centroid[track_id] = curr

        bin_index = int(ts // BIN_DURATION_S)
        for name, state in self._approaches.items():
            if state.current_bin_index == -1:
                state.current_bin_index = bin_index
            while state.current_bin_index < bin_index:
                state.bin_history.append(state.current_bin_count)
                self._evaluate_closed_bin(name, state, result)
                state.current_bin_count = 0
                state.current_bin_index += 1

        return result

    def _evaluate_closed_bin(self, name: str, state: _ApproachState, result: SignalResult) -> None:
        if len(state.bin_history) < 2:
            return
        closed_count = state.bin_history[-1]
        baseline = list(state.bin_history)[:-1]
        median = statistics.median(baseline)
        if median <= 0:
            return
        if closed_count < median * COLLAPSE_RATIO:
            state.low_streak += 1
        else:
            state.low_streak = 0

        if state.low_streak >= MIN_CONSECUTIVE_LOW_BINS:
            result.score = max(result.score, FIRE_SCORE)
            result.reasons.append(
                f"flow: approach '{name}' throughput collapsed ({closed_count} vs median {median:.1f})"
            )
