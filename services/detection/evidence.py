"""Ring-buffer evidence capture: pre/post clip + annotated snapshot per incident (plan.md §7.6)."""

from __future__ import annotations

import shutil
import subprocess
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from services.detection.fusion import IncidentCandidate
from services.detection.tracker_ctx import FrameContext
from services.detection.video_source import Frame


@dataclass
class _ActiveCapture:
    candidate: IncidentCandidate
    pre_frames: list[Frame]
    incident_dir: Path
    snapshot_path: Path
    post_target: int
    post_frames: list[Frame] = field(default_factory=list)


class EvidenceBuffer:
    def __init__(
        self,
        target_fps: float,
        pre_seconds: float = 10.0,
        post_seconds: float = 5.0,
        out_root: str | Path = "data/clips",
    ):
        self.target_fps = target_fps
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.out_root = Path(out_root)
        self._ring: deque[Frame] = deque(maxlen=max(1, int(target_fps * pre_seconds)))
        self._active: list[_ActiveCapture] = []

    def push(self, frame: Frame) -> None:
        self._ring.append(frame)

    def start_capture(self, candidate: IncidentCandidate, ctx: FrameContext) -> None:
        incident_dir = self.out_root / candidate.incident_id
        incident_dir.mkdir(parents=True, exist_ok=True)

        snapshot_path = incident_dir / "snapshot.jpg"
        trigger_frame = self._ring[-1] if self._ring else None
        if trigger_frame is not None:
            annotated = self._render_snapshot(trigger_frame, ctx, candidate)
            cv2.imwrite(str(snapshot_path), annotated)

        post_target = max(1, int(self.target_fps * self.post_seconds))
        self._active.append(
            _ActiveCapture(
                candidate=candidate,
                pre_frames=list(self._ring),
                incident_dir=incident_dir,
                snapshot_path=snapshot_path,
                post_target=post_target,
            )
        )

    def _render_snapshot(self, frame: Frame, ctx: FrameContext, candidate: IncidentCandidate) -> np.ndarray:
        from services.detection.engine import draw_debug_overlay  # deferred: avoids a circular import

        annotated = draw_debug_overlay(frame.image, ctx)
        y = annotated.shape[0] - 10 - 18 * len(candidate.reasons)
        for reason in candidate.reasons:
            cv2.putText(annotated, reason, (10, max(15, y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
            y += 18
        return annotated

    def tick(self, frame: Frame) -> list[tuple[IncidentCandidate, str, str]]:
        completed = []
        still_active = []
        for capture in self._active:
            capture.post_frames.append(frame)
            if len(capture.post_frames) >= capture.post_target:
                completed.append(self._finalize(capture))
            else:
                still_active.append(capture)
        self._active = still_active
        return completed

    def flush(self) -> list[tuple[IncidentCandidate, str, str]]:
        """Finalizes any in-progress captures (e.g. at end-of-video) with whatever post-frames exist."""
        completed = [self._finalize(capture) for capture in self._active]
        self._active = []
        return completed

    def _finalize(self, capture: _ActiveCapture) -> tuple[IncidentCandidate, str, str]:
        clip_path = self._write_clip(capture)
        return capture.candidate, str(clip_path), str(capture.snapshot_path)

    def _write_clip(self, capture: _ActiveCapture) -> Path:
        raw_path = capture.incident_dir / "raw.mp4"
        evidence_path = capture.incident_dir / "evidence.mp4"

        all_frames = capture.pre_frames + capture.post_frames
        if not all_frames:
            evidence_path.touch()
            return evidence_path

        h, w = all_frames[0].image.shape[:2]
        writer = cv2.VideoWriter(str(raw_path), cv2.VideoWriter_fourcc(*"mp4v"), self.target_fps, (w, h))
        for f in all_frames:
            writer.write(f.image)
        writer.release()

        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            subprocess.run(
                [
                    ffmpeg_path, "-y", "-i", str(raw_path),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(evidence_path),
                ],
                check=True,
                capture_output=True,
            )
            raw_path.unlink(missing_ok=True)
        else:
            print(
                f"WARNING: ffmpeg not found on PATH -- evidence clip for {capture.candidate.incident_id} "
                "is mp4v-encoded, not H.264; browser playback may fail. Install ffmpeg "
                "(winget install Gyan.FFmpeg)."
            )
            raw_path.rename(evidence_path)

        return evidence_path
