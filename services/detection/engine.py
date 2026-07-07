"""Detection engine skeleton: video source -> detector -> track history, with an
optional debug overlay for visually verifying detection/tracking during development
(plan.md §7.1, E1-T4). Signal fusion, severity, and evidence writing are wired in
starting at E4 — this module currently only exercises E1's building blocks.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from services.detection.detector import Detector
from services.detection.tracker_ctx import FrameContext, TrackHistoryBuilder
from services.detection.video_source import VideoSource

VELOCITY_SCALE = 3.0  # visual scale factor so velocity vectors are visible in the overlay


def draw_debug_overlay(image: np.ndarray, ctx: FrameContext) -> np.ndarray:
    annotated = image.copy()
    for track in ctx.tracks.values():
        x1, y1, x2, y2 = (int(v) for v in track.bbox)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"id={track.track_id} {track.cls}"
        cv2.putText(
            annotated, label, (x1, max(0, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
        )

        cx, cy = track.centroid
        vx, vy = track.velocity
        start = (int(cx), int(cy))
        end = (int(cx + vx * VELOCITY_SCALE), int(cy + vy * VELOCITY_SCALE))
        cv2.arrowedLine(annotated, start, end, (0, 128, 255), 2, tipLength=0.3)
    return annotated


def run(
    video_path: str,
    target_fps: float = 10.0,
    speed_factor: float = 1.0,
    debug_overlay: bool = False,
    output_path: str | None = None,
    weights: str = "models/yolo11s.pt",
    max_frames: int | None = None,
) -> str | None:
    """Runs the E1 pipeline over `video_path`. Returns the debug overlay output
    path if `debug_overlay` is set, else None."""
    detector = Detector(weights=weights)
    history = TrackHistoryBuilder()
    src = VideoSource(video_path, target_fps=target_fps, speed_factor=speed_factor)

    writer = None
    out_path = None
    if debug_overlay:
        out_path = output_path or str(Path(video_path).with_name(Path(video_path).stem + "_debug.mp4"))
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    frame_count = 0
    for frame in src:
        detections = detector.track(frame.image)
        ctx = history.update(frame_index=frame.index, timestamp_s=frame.timestamp_s, detections=detections)

        if debug_overlay:
            annotated = draw_debug_overlay(frame.image, ctx)
            if writer is None:
                h, w = annotated.shape[:2]
                writer = cv2.VideoWriter(out_path, fourcc, target_fps, (w, h))
            writer.write(annotated)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break

    if writer is not None:
        writer.release()
        print(f"wrote debug overlay video: {out_path} ({frame_count} frames)")

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanjeevani detection engine (E1 skeleton)")
    parser.add_argument("video_path")
    parser.add_argument("--target-fps", type=float, default=10.0)
    parser.add_argument("--speed-factor", type=float, default=1.0)
    parser.add_argument("--debug-overlay", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--weights", default="models/yolo11s.pt")
    args = parser.parse_args()
    run(
        args.video_path,
        target_fps=args.target_fps,
        speed_factor=args.speed_factor,
        debug_overlay=args.debug_overlay,
        output_path=args.output,
        weights=args.weights,
    )


if __name__ == "__main__":
    main()
