"""YOLO11 detection + ByteTrack multi-object tracking wrapper (plan.md §7.3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from ultralytics import YOLO

DEFAULT_CLASSES = ("person", "bicycle", "car", "motorcycle", "bus", "truck")


@dataclass
class Detection:
    track_id: Optional[int]
    cls: str
    conf: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2, pixel coords


class Detector:
    def __init__(
        self,
        weights: str | Path = "models/yolo11s.pt",
        imgsz: int = 960,
        conf: float = 0.30,
        iou: float = 0.5,
        classes: tuple[str, ...] = DEFAULT_CLASSES,
        device: str | None = None,
    ):
        self.model = YOLO(str(weights))
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou
        self.device = device if device is not None else ("0" if torch.cuda.is_available() else "cpu")
        names = self.model.names  # {id: name}
        self.class_ids = [class_id for class_id, name in names.items() if name in classes]

    def track(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            classes=self.class_ids,
            device=self.device,
            verbose=False,
        )
        detections: list[Detection] = []
        boxes = results[0].boxes
        if boxes is None:
            return detections
        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            detections.append(
                Detection(
                    track_id=int(boxes.id[i].item()) if boxes.id is not None else None,
                    cls=self.model.names[cls_id],
                    conf=float(boxes.conf[i].item()),
                    bbox=tuple(boxes.xyxy[i].tolist()),
                )
            )
        return detections


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from services.detection.video_source import VideoSource

    if len(sys.argv) < 2:
        print("usage: python detector.py <video_path>")
        raise SystemExit(1)

    detector = Detector()
    src = VideoSource(sys.argv[1], target_fps=10, speed_factor=8.0)
    for frame in src:
        dets = detector.track(frame.image)
        summary = ", ".join(f"id={d.track_id} {d.cls} conf={d.conf:.2f}" for d in dets)
        print(f"frame {frame.index}: {summary}")
