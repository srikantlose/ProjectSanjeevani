"""Plays back a scenario video file paced to real-world wall-clock time, simulating a live camera feed."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np


@dataclass
class Frame:
    index: int
    timestamp_s: float
    image: np.ndarray


class VideoSource:
    """Iterates frames from `video_path`, sleeping between yields so playback matches
    the source's own frame rate in real time (see plan.md §7.2).

    `speed_factor` scales playback speed (1.0 = real time; >1.0 = faster, for dev iteration).
    `target_fps` throttles how many frames are actually yielded by skipping frames —
    the video is not played faster, frames are just dropped to hit the processing rate.
    """

    def __init__(self, video_path: str | Path, target_fps: float = 10.0, speed_factor: float = 1.0):
        self.video_path = Path(video_path)
        self.target_fps = target_fps
        self.speed_factor = speed_factor
        self._cap = cv2.VideoCapture(str(self.video_path))
        if not self._cap.isOpened():
            raise FileNotFoundError(f"could not open video: {self.video_path}")
        self.source_fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0

    def __iter__(self) -> Iterator[Frame]:
        frame_interval_s = 1.0 / self.source_fps
        keep_every = max(1, round(self.source_fps / self.target_fps))
        start_wall = time.monotonic()
        index = 0
        while True:
            ok, image = self._cap.read()
            if not ok:
                break
            timestamp_s = index * frame_interval_s
            if index % keep_every == 0:
                target_wall = start_wall + timestamp_s / self.speed_factor
                sleep_s = target_wall - time.monotonic()
                if sleep_s > 0:
                    time.sleep(sleep_s)
                yield Frame(index=index, timestamp_s=timestamp_s, image=image)
            index += 1
        self._cap.release()

    def close(self) -> None:
        if self._cap.isOpened():
            self._cap.release()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python video_source.py <video_path> [target_fps] [speed_factor]")
        raise SystemExit(1)
    path = sys.argv[1]
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    src = VideoSource(path, target_fps=fps, speed_factor=speed)
    wall_start = time.monotonic()
    for frame in src:
        print(f"frame {frame.index} ts={frame.timestamp_s:.2f}s wall={time.monotonic() - wall_start:.2f}s")
