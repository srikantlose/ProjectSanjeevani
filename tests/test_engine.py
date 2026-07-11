import json
from pathlib import Path

import cv2
import numpy as np

from services.detection.engine import run

VTEST_CAMERA_YAML = str(Path(__file__).resolve().parent.parent / "configs" / "cameras" / "vtest_highway_test.yaml")


def test_debug_overlay_produces_playable_annotated_video(tmp_path):
    out_path = tmp_path / "debug_out.mp4"
    run(
        VTEST_CAMERA_YAML,
        headless=True,
        debug_overlay=True,
        speed_factor=30.0,
        max_frames=15,
        debug_overlay_output=str(out_path),
        evidence_out_root=str(tmp_path / "clips"),
    )

    assert out_path.exists()
    assert out_path.stat().st_size > 0

    cap = cv2.VideoCapture(str(out_path))
    assert cap.isOpened()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert frame_count >= 10  # some frames may be dropped by the mp4v encoder's keyframe handling

    found_overlay_pixel = False
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        green_mask = np.all(frame == [0, 255, 0], axis=-1)
        if green_mask.any():
            found_overlay_pixel = True
            break
    cap.release()

    assert found_overlay_pixel


def test_headless_run_fires_stationary_candidate_with_evidence(tmp_path):
    clips_root = tmp_path / "clips"
    candidates = run(
        VTEST_CAMERA_YAML,
        headless=True,
        speed_factor=30.0,
        max_frames=250,  # ~25s of video at 10fps -- comfortably past the 20s full-ramp point
        evidence_out_root=str(clips_root),
    )

    assert len(candidates) >= 1
    stationary_candidates = [c for c in candidates if c.signals.get("stationary", 0.0) >= 0.85]
    assert stationary_candidates, f"no candidate reached stationary>=0.85; got {[c.signals for c in candidates]}"

    candidate = stationary_candidates[0]
    assert candidate.severity is not None
    assert candidate.evidence_clip_path is not None
    assert candidate.evidence_snapshot_path is not None

    clip_path = Path(candidate.evidence_clip_path)
    snapshot_path = Path(candidate.evidence_snapshot_path)
    assert clip_path.exists()
    assert snapshot_path.exists()

    cap = cv2.VideoCapture(str(clip_path))
    assert cap.isOpened()
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 0
    cap.release()

    snapshot = cv2.imread(str(snapshot_path))
    assert snapshot is not None


def test_non_headless_run_queues_candidate_when_api_unreachable(tmp_path):
    queue_path = tmp_path / "queue" / "pending_incidents.jsonl"
    candidates = run(
        VTEST_CAMERA_YAML,
        headless=False,
        speed_factor=30.0,
        max_frames=250,
        evidence_out_root=str(tmp_path / "clips"),
        queue_path=str(queue_path),
        api_base_url="http://localhost:1",  # unreachable on purpose
        start_retry_thread=False,
    )

    assert len(candidates) >= 1
    assert queue_path.exists()
    with open(queue_path) as f:
        queued = [json.loads(line) for line in f if line.strip()]
    assert len(queued) >= 1
    assert queued[0]["camera_id"] == "vtest_highway_test"
