import shutil

import cv2
import numpy as np
import pytest

from scripts.make_clips import normalize_directory


def _write_raw_clip(path, width=320, height=240, fps=30.0, num_frames=20):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    for i in range(num_frames):
        image = np.full((height, width, 3), i % 256, dtype=np.uint8)
        writer.write(image)
    writer.release()


def test_normalize_directory_rejects_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        normalize_directory(tmp_path / "does_not_exist", tmp_path / "out")


def test_normalize_directory_returns_empty_list_for_no_videos(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed on this machine")

    src = tmp_path / "raw" / "some_source"
    src.mkdir(parents=True)
    (src / "notes.txt").write_text("not a video")

    written = normalize_directory(src, tmp_path / "out")
    assert written == []


def test_normalize_directory_encodes_and_names_clips_sequentially(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed on this machine")

    src = tmp_path / "raw" / "cadp"
    src.mkdir(parents=True)
    _write_raw_clip(src / "b_clip.avi")
    _write_raw_clip(src / "a_clip.avi")

    out_dir = tmp_path / "processed"
    written = normalize_directory(src, out_dir)

    assert [p.name for p in written] == ["cadp_0001.mp4", "cadp_0002.mp4"]
    for dst in written:
        assert dst.exists()
        cap = cv2.VideoCapture(str(dst))
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 1280
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 720
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        assert abs(fps - 25.0) < 0.5
