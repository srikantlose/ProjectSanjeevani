"""Shared pytest fixtures.

`vtest_video` provides a small real clip (pedestrians/cars) for tests that need
actual detectable content — synthetic solid-color frames don't produce real
YOLO detections. This is a standard OpenCV test asset (BSD-licensed), used only
as dev/test infrastructure — it is not part of the project's actual dataset
(see plan.md §6), which is acquired separately in epic E8.
"""

import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pytest

from services.detection.detector import Detection
from services.detection.tracker_ctx import FrameContext, TrackHistoryBuilder

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VTEST_URL = "https://github.com/opencv/opencv/raw/master/samples/data/vtest.avi"
VTEST_PATH = FIXTURES_DIR / "vtest.avi"


@pytest.fixture(scope="session")
def vtest_video() -> Path:
    FIXTURES_DIR.mkdir(exist_ok=True)
    if not VTEST_PATH.exists():
        urllib.request.urlretrieve(VTEST_URL, VTEST_PATH)
    return VTEST_PATH


@dataclass
class SyntheticTrack:
    """One track's bbox in a single synthetic frame, for building signal-test fixtures."""

    track_id: int
    cls: str
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2


@pytest.fixture
def frame_context_builder():
    """Factory fixture: turns a list of per-frame track lists into a list of
    FrameContext objects, running them through the real TrackHistoryBuilder so
    velocity/aspect are computed the same way as in production. Lets signal
    tests describe scenarios (e.g. "two tracks converge then one stops")
    without needing any video.

    Usage:
        contexts = frame_context_builder([
            [SyntheticTrack(1, "car", (0, 0, 40, 20)), SyntheticTrack(2, "car", (100, 0, 140, 20))],
            [SyntheticTrack(1, "car", (10, 0, 50, 20)), SyntheticTrack(2, "car", (90, 0, 130, 20))],
            ...
        ])
    """

    def _build(frames: list[list[SyntheticTrack]], fps: float = 10.0, smoothing_window: int = 5) -> list[FrameContext]:
        builder = TrackHistoryBuilder(smoothing_window=smoothing_window)
        contexts = []
        for i, frame_tracks in enumerate(frames):
            detections = [
                Detection(track_id=t.track_id, cls=t.cls, conf=1.0, bbox=t.bbox) for t in frame_tracks
            ]
            contexts.append(builder.update(frame_index=i, timestamp_s=i / fps, detections=detections))
        return contexts

    return _build
