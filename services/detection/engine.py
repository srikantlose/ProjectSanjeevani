"""Detection engine: the full per-frame pipeline (plan.md §7.1, §7.8).

video -> detector+tracker -> signals -> fusion -> severity -> evidence -> emitter
"""

from __future__ import annotations

import argparse

import cv2
import numpy as np

from services.detection.config import CameraConfig, load_engine_config
from services.detection.detector import Detector
from services.detection.emitter import Emitter
from services.detection.evidence import EvidenceBuffer
from services.detection.fusion import FusionEngine, IncidentCandidate
from services.detection.severity import assess as assess_severity
from services.detection.signal_factory import build_signals
from services.detection.tracker_ctx import FrameContext, TrackHistoryBuilder
from services.detection.video_source import VideoSource

VELOCITY_SCALE = 3.0  # visual scale factor so velocity vectors are visible in the debug overlay


def draw_debug_overlay(image: np.ndarray, ctx: FrameContext, camera: CameraConfig | None = None) -> np.ndarray:
    annotated = image.copy()

    if camera is not None:
        for name, polygon in camera.rois.items():
            pts = np.array([[int(x), int(y)] for x, y in polygon], dtype=np.int32)
            cv2.polylines(annotated, [pts], True, (255, 255, 0), 2)
            cv2.putText(annotated, name, tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
        for zone in camera.exclusion_zones:
            pts = np.array([[int(x), int(y)] for x, y in zone.polygon], dtype=np.int32)
            cv2.polylines(annotated, [pts], True, (0, 0, 255), 2)
            cv2.putText(annotated, zone.name, tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        for name, (p1, p2) in camera.count_lines.items():
            pt1, pt2 = (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1]))
            cv2.line(annotated, pt1, pt2, (255, 0, 255), 2)
            cv2.putText(annotated, name, pt1, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1, cv2.LINE_AA)

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


def build_payload(candidate: IncidentCandidate, cfg) -> dict:
    return {
        "id": candidate.incident_id,
        "camera_id": candidate.camera_id,
        "mode": candidate.mode,
        "severity": candidate.severity,
        "severity_reasons": candidate.severity_reasons,
        "signals": candidate.signals,
        "reasons": candidate.reasons,
        "location": {
            "lat": cfg.camera.location.lat,
            "lon": cfg.camera.location.lon,
            "label": cfg.camera.location.label,
        },
        "evidence": {
            "clip_path": candidate.evidence_clip_path,
            "snapshot_path": candidate.evidence_snapshot_path,
        },
        "detected_at": candidate.detected_at,
    }


def run(
    camera_yaml: str,
    headless: bool = False,
    debug_overlay: bool = False,
    speed_factor: float | None = None,
    max_frames: int | None = None,
    api_base_url: str = "http://localhost:8000",
    debug_overlay_output: str | None = None,
    evidence_out_root: str = "data/clips",
    queue_path: str = "data/queue/pending_incidents.jsonl",
    start_retry_thread: bool = True,
) -> list[IncidentCandidate]:
    cfg = load_engine_config(camera_yaml)
    if speed_factor is not None:
        cfg.processing.speed_factor = speed_factor

    device = None if cfg.detector.device == "auto" else cfg.detector.device
    detector = Detector(
        weights=cfg.detector.weights,
        imgsz=cfg.detector.imgsz,
        conf=cfg.detector.conf,
        iou=cfg.detector.iou,
        classes=tuple(cfg.detector.classes),
        device=device,
    )
    history = TrackHistoryBuilder()
    signals = build_signals(cfg)
    fusion = FusionEngine(cfg.fusion, camera_id=cfg.camera.camera_id, mode=cfg.camera.mode)
    evidence_buffer = EvidenceBuffer(target_fps=cfg.processing.target_fps, out_root=evidence_out_root)
    emitter = None if headless else Emitter(base_url=api_base_url, queue_path=queue_path, start_retry_thread=start_retry_thread)

    src = VideoSource(
        cfg.camera.source_video, target_fps=cfg.processing.target_fps, speed_factor=cfg.processing.speed_factor
    )

    overlay_writer = None
    overlay_path = None
    frame_size_configured = False
    results_out: list[IncidentCandidate] = []
    frame_count = 0

    for frame in src:
        evidence_buffer.push(frame)

        for signal in signals:
            signal.set_current_frame_image(frame.image)

        ctx = history.update(frame_index=frame.index, timestamp_s=frame.timestamp_s, detections=detector.track(frame.image))

        if not frame_size_configured:
            h, w = frame.image.shape[:2]
            fusion.configure_frame_size(w, h)
            frame_size_configured = True

        results = {signal.name: signal.update(ctx) for signal in signals}

        candidate = fusion.update(ctx, results)
        if candidate is not None:
            severity, severity_reasons = assess_severity(results, ctx)
            candidate.severity = severity
            candidate.severity_reasons = severity_reasons
            evidence_buffer.start_capture(candidate, ctx)
            print(
                f"[{frame.timestamp_s:.1f}s] candidate {candidate.incident_id} "
                f"severity={severity} signals={candidate.signals}"
            )

        for completed_candidate, clip_path, snapshot_path in evidence_buffer.tick(frame):
            completed_candidate.evidence_clip_path = clip_path
            completed_candidate.evidence_snapshot_path = snapshot_path
            if emitter is not None:
                emitter.emit(build_payload(completed_candidate, cfg))
            results_out.append(completed_candidate)

        if debug_overlay:
            annotated = draw_debug_overlay(frame.image, ctx, cfg.camera)
            if overlay_writer is None:
                overlay_path = debug_overlay_output or f"{cfg.camera.camera_id}_debug.mp4"
                h, w = annotated.shape[:2]
                overlay_writer = cv2.VideoWriter(overlay_path, cv2.VideoWriter_fourcc(*"mp4v"), cfg.processing.target_fps, (w, h))
            overlay_writer.write(annotated)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            break

    for completed_candidate, clip_path, snapshot_path in evidence_buffer.flush():
        completed_candidate.evidence_clip_path = clip_path
        completed_candidate.evidence_snapshot_path = snapshot_path
        if emitter is not None:
            emitter.emit(build_payload(completed_candidate, cfg))
        results_out.append(completed_candidate)

    if overlay_writer is not None:
        overlay_writer.release()
        print(f"wrote debug overlay video: {overlay_path} ({frame_count} frames)")

    return results_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Sanjeevani detection engine")
    parser.add_argument("--camera", required=True, help="path to a camera YAML (configs/cameras/*.yaml)")
    parser.add_argument("--headless", action="store_true", help="skip HTTP emission; just return/print candidates")
    parser.add_argument("--debug-overlay", action="store_true")
    parser.add_argument("--speed-factor", type=float, default=None)
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()

    candidates = run(
        args.camera,
        headless=args.headless,
        debug_overlay=args.debug_overlay,
        speed_factor=args.speed_factor,
        max_frames=args.max_frames,
        api_base_url=args.api_base_url,
    )
    print(f"engine run complete: {len(candidates)} candidate(s)")


if __name__ == "__main__":
    main()
