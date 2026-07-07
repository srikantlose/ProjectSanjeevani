"""Builds per-frame FrameContext with smoothed per-track history (plan.md §7.4)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from services.detection.detector import Detection


@dataclass
class TrackState:
    track_id: int
    cls: str
    bbox: tuple[float, float, float, float]
    centroid: tuple[float, float]
    velocity: tuple[float, float]  # px/frame, smoothed over the last `smoothing_window` frames
    bbox_aspect: float  # width / height
    age_frames: int


@dataclass
class FrameContext:
    frame_index: int
    timestamp_s: float
    tracks: dict[int, TrackState] = field(default_factory=dict)


class TrackHistoryBuilder:
    """Maintains rolling per-track centroid history across frames and derives
    smoothed velocity and bbox aspect ratio for each active track."""

    def __init__(self, smoothing_window: int = 5):
        self.smoothing_window = smoothing_window
        self._centroid_history: dict[int, deque] = {}
        self._age: dict[int, int] = {}

    def update(self, frame_index: int, timestamp_s: float, detections: list[Detection]) -> FrameContext:
        tracks: dict[int, TrackState] = {}
        for d in detections:
            if d.track_id is None:
                continue

            x1, y1, x2, y2 = d.bbox
            centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
            width, height = x2 - x1, y2 - y1
            aspect = width / height if height > 0 else 0.0

            history = self._centroid_history.setdefault(d.track_id, deque(maxlen=self.smoothing_window))
            history.append(centroid)
            self._age[d.track_id] = self._age.get(d.track_id, 0) + 1

            if len(history) >= 2:
                n = len(history) - 1
                velocity = (
                    (history[-1][0] - history[0][0]) / n,
                    (history[-1][1] - history[0][1]) / n,
                )
            else:
                velocity = (0.0, 0.0)

            tracks[d.track_id] = TrackState(
                track_id=d.track_id,
                cls=d.cls,
                bbox=d.bbox,
                centroid=centroid,
                velocity=velocity,
                bbox_aspect=aspect,
                age_frames=self._age[d.track_id],
            )
        return FrameContext(frame_index=frame_index, timestamp_s=timestamp_s, tracks=tracks)
