"""Common interface every signal module implements (plan.md §7.4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from services.detection.tracker_ctx import FrameContext


@dataclass
class SignalResult:
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    fired_track_ids: list[int] = field(default_factory=list)


class Signal:
    name: str = "base"

    def update(self, frame_ctx: FrameContext) -> SignalResult:
        """Called once per processed frame. Must return a SignalResult."""
        raise NotImplementedError

    def set_current_frame_image(self, image) -> None:
        """No-op hook; the engine calls this on every signal every frame before
        `update()`. Only PoseConfirmedRiderDownSignal actually uses the image."""
