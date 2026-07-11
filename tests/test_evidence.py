import shutil

import cv2
import numpy as np
import pytest

from services.detection.evidence import EvidenceBuffer
from services.detection.fusion import IncidentCandidate
from services.detection.tracker_ctx import FrameContext
from services.detection.video_source import Frame


def _make_frame(index, fps=10.0):
    image = np.full((120, 160, 3), index % 256, dtype=np.uint8)
    cv2.putText(image, str(index), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return Frame(index=index, timestamp_s=index / fps, image=image)


def _make_candidate():
    return IncidentCandidate(
        incident_id="inc_test_001",
        camera_id="cam1",
        mode="city",
        detected_ts=12.0,
        detected_at="2026-01-01T00:00:00.000Z",
        signals={"collision": 0.9},
        reasons=["collision: test reason"],
        fired_track_ids=[],
        trigger_cell=(0, 0),
    )


def _empty_ctx(ts):
    return FrameContext(frame_index=0, timestamp_s=ts, tracks={})


def _run_capture(tmp_path, fps=10.0, pre_seconds=10.0, post_seconds=5.0, trigger_frame_index=120, total_frames=200):
    buffer = EvidenceBuffer(target_fps=fps, pre_seconds=pre_seconds, post_seconds=post_seconds, out_root=tmp_path)
    candidate = _make_candidate()
    completed = []

    for i in range(total_frames):
        frame = _make_frame(i, fps=fps)
        buffer.push(frame)
        if i == trigger_frame_index:
            buffer.start_capture(candidate, _empty_ctx(frame.timestamp_s))
        completed.extend(buffer.tick(frame))

    return candidate, completed


def _assert_valid_capture(candidate, completed):
    assert len(completed) == 1
    cand, clip_path, snapshot_path = completed[0]
    assert cand.incident_id == candidate.incident_id

    cap = cv2.VideoCapture(clip_path)
    assert cap.isOpened()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    expected = (10 + 5) * 10  # (pre_seconds + post_seconds) * fps
    assert abs(frame_count - expected) <= expected * 0.1

    snapshot = cv2.imread(snapshot_path)
    assert snapshot is not None


def test_evidence_capture_with_ffmpeg(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed on this machine")

    candidate, completed = _run_capture(tmp_path)
    _assert_valid_capture(candidate, completed)


def test_evidence_capture_without_ffmpeg_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    candidate, completed = _run_capture(tmp_path)
    _assert_valid_capture(candidate, completed)
