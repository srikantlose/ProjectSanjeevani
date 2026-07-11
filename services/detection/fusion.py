"""Signal fusion: combines per-frame signal scores into IncidentCandidate events (plan.md §7.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from services.detection.config import FusionParams
from services.detection.signals.base import SignalResult
from services.detection.tracker_ctx import FrameContext


@dataclass
class IncidentCandidate:
    incident_id: str
    camera_id: str
    mode: str
    detected_ts: float  # video-time seconds
    detected_at: str  # UTC ISO8601 with trailing Z
    signals: dict[str, float]
    reasons: list[str]
    fired_track_ids: list[int]
    trigger_cell: tuple[int, int]
    severity: str | None = None
    severity_reasons: list[str] = field(default_factory=list)
    evidence_clip_path: str | None = None
    evidence_snapshot_path: str | None = None


class FusionEngine:
    def __init__(self, params: FusionParams, camera_id: str, mode: str):
        self.params = params
        self.camera_id = camera_id
        self.mode = mode
        self._frame_w: int | None = None
        self._frame_h: int | None = None
        self._cooldowns: dict[tuple[int, int], float] = {}
        self._seq = 0

    def configure_frame_size(self, w: int, h: int) -> None:
        self._frame_w = w
        self._frame_h = h

    def _weighted_sum(self, results: dict[str, SignalResult]) -> float:
        total = 0.0
        for name, weight in self.params.weights.items():
            if name in results:
                total += weight * results[name].score
        return total

    def _override_fired(self, results: dict[str, SignalResult]) -> bool:
        for rule in self.params.override_rules:
            r = results.get(rule.signal)
            if r is not None and r.score >= rule.min_score:
                return True
        return False

    def _trigger_cell(self, ctx: FrameContext, fired_track_ids: list[int]) -> tuple[int, int]:
        gx, gy = self.params.cooldown_grid
        points = [ctx.tracks[tid].centroid for tid in fired_track_ids if tid in ctx.tracks]
        if points:
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
        else:
            x = (self._frame_w or 0) / 2
            y = (self._frame_h or 0) / 2
        w = self._frame_w or 1
        h = self._frame_h or 1
        cx = min(gx - 1, max(0, int(x / w * gx)))
        cy = min(gy - 1, max(0, int(y / h * gy)))
        return (cx, cy)

    def _mint_incident_id(self, now: datetime) -> str:
        self._seq += 1
        return f"inc_{now.strftime('%Y%m%d%H%M%S')}_{self._seq:03d}"

    def update(self, ctx: FrameContext, results: dict[str, SignalResult]) -> IncidentCandidate | None:
        weighted = self._weighted_sum(results)
        if weighted < self.params.candidate_threshold and not self._override_fired(results):
            return None

        fired_track_ids = sorted({tid for r in results.values() for tid in r.fired_track_ids})
        cell = self._trigger_cell(ctx, fired_track_ids)

        last_fired = self._cooldowns.get(cell)
        if last_fired is not None and ctx.timestamp_s - last_fired < self.params.cooldown_seconds:
            return None
        self._cooldowns[cell] = ctx.timestamp_s

        reasons = [r for result in results.values() for r in result.reasons]
        signals_scores = {name: result.score for name, result in results.items()}

        now = datetime.now(timezone.utc)
        detected_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

        return IncidentCandidate(
            incident_id=self._mint_incident_id(now),
            camera_id=self.camera_id,
            mode=self.mode,
            detected_ts=ctx.timestamp_s,
            detected_at=detected_at,
            signals=signals_scores,
            reasons=reasons,
            fired_track_ids=fired_track_ids,
            trigger_cell=cell,
        )
