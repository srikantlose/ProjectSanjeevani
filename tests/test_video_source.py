import time

import cv2
import numpy as np
import pytest

from services.detection.video_source import VideoSource


def _write_synthetic_video(path, fps=25, n_frames=50, size=(320, 240)):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, size)
    for i in range(n_frames):
        frame = np.full((size[1], size[0], 3), i % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()


@pytest.fixture
def synthetic_video(tmp_path):
    path = tmp_path / "synthetic.mp4"
    _write_synthetic_video(path, fps=25, n_frames=50)
    return path


def test_real_time_pacing(synthetic_video):
    # 50 frames at 25 fps = 2.0s of source video; speed_factor=1.0 should take ~2.0s wall time.
    src = VideoSource(synthetic_video, target_fps=25, speed_factor=1.0)
    start = time.monotonic()
    frames = list(src)
    elapsed = time.monotonic() - start

    assert len(frames) == 50
    assert 1.8 <= elapsed <= 2.2  # within 10% of the expected 2.0s


def test_target_fps_skips_frames(synthetic_video):
    # source is 25 fps, target_fps=5 should keep roughly 1 in 5 frames -> 10 frames.
    src = VideoSource(synthetic_video, target_fps=5, speed_factor=10.0)
    frames = list(src)
    assert len(frames) == 10


def test_speed_factor_speeds_up_playback(synthetic_video):
    src = VideoSource(synthetic_video, target_fps=25, speed_factor=4.0)
    start = time.monotonic()
    frames = list(src)
    elapsed = time.monotonic() - start

    assert len(frames) == 50
    assert elapsed <= 0.7  # ~0.5s expected (2.0s / 4.0), generous upper bound
