"""Interactive ROI annotation tool for camera configs (plan.md §13, E8-T0).

Opens the first frame of a video in an OpenCV window and lets a human click
out the road polygon, the live-lane polygon, exclusion zones, and count
lines, then deep-merges the result into an existing `--camera` YAML
(preserving unrelated keys like camera_id/mode/source_video/location).

`AnnotationState` holds all the shape-editing logic and is fully unit
testable without a display; `main()` is the thin OpenCV event-loop wrapper
around it (not exercised by tests -- it needs a real window/mouse).

Usage:
    venv\\Scripts\\python.exe scripts\\annotate_roi.py --video data/clips/demo.mp4 --camera configs/cameras/junction_cam.yaml

Keys:
    left-click  add a vertex to the shape currently being drawn
    r           start the `road` polygon (replaces any previous road shape)
    l           start the `live_lane` polygon (replaces any previous one)
    e           start a new exclusion zone, auto-named excl_N
    c           start a new 2-point count line, auto-named line_N
    n           finish/commit the shape currently being drawn
    u           undo the last vertex of the shape currently being drawn
    s           save: deep-merge all committed shapes into --camera YAML
    q           quit without saving
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

Point = tuple[float, float]


@dataclass
class _CurrentShape:
    kind: str  # "polygon" | "line"
    target: str  # "road" | "live_lane" | "exclusion" | "count_line"
    name: str
    points: list[Point] = field(default_factory=list)


class AnnotationState:
    """Tracks in-progress and committed ROI shapes for one camera config."""

    def __init__(self) -> None:
        self.rois: dict[str, list[Point]] = {}
        self.exclusion_zones: list[dict] = []
        self.count_lines: dict[str, dict[str, Point]] = {}
        self._current: _CurrentShape | None = None
        self._excl_counter = 0
        self._line_counter = 0

    @property
    def current(self) -> _CurrentShape | None:
        return self._current

    def start_road(self) -> None:
        self._current = _CurrentShape(kind="polygon", target="road", name="road")

    def start_live_lane(self) -> None:
        self._current = _CurrentShape(kind="polygon", target="live_lane", name="live_lane")

    def start_exclusion_zone(self) -> str:
        self._excl_counter += 1
        name = f"excl_{self._excl_counter}"
        self._current = _CurrentShape(kind="polygon", target="exclusion", name=name)
        return name

    def start_count_line(self) -> str:
        self._line_counter += 1
        name = f"line_{self._line_counter}"
        self._current = _CurrentShape(kind="line", target="count_line", name=name)
        return name

    def add_vertex(self, point: Point) -> None:
        if self._current is None:
            raise ValueError("no shape in progress -- press r/l/e/c to start one first")
        if self._current.kind == "line" and len(self._current.points) >= 2:
            raise ValueError("count lines take exactly 2 points -- press n to finish or u to undo")
        self._current.points.append(point)

    def undo_vertex(self) -> None:
        if self._current is None or not self._current.points:
            return
        self._current.points.pop()

    def finish_shape(self, rename_to: str | None = None) -> None:
        shape = self._current
        if shape is None:
            raise ValueError("no shape in progress")

        if shape.kind == "polygon" and len(shape.points) < 3:
            raise ValueError(f"'{shape.name}' polygon needs at least 3 points, has {len(shape.points)}")
        if shape.kind == "line" and len(shape.points) != 2:
            raise ValueError(f"'{shape.name}' count line needs exactly 2 points, has {len(shape.points)}")

        if shape.target == "road":
            self.rois["road"] = shape.points
        elif shape.target == "live_lane":
            self.rois["live_lane"] = shape.points
        elif shape.target == "exclusion":
            self.exclusion_zones.append({"name": shape.name, "polygon": shape.points})
        elif shape.target == "count_line":
            name = rename_to or shape.name
            self.count_lines[name] = {"p1": shape.points[0], "p2": shape.points[1]}

        self._current = None

    def to_camera_dict(self) -> dict:
        result: dict = {}
        if self.rois:
            result["rois"] = {name: [list(p) for p in poly] for name, poly in self.rois.items()}
        if self.exclusion_zones:
            result["exclusion_zones"] = [
                {"name": z["name"], "polygon": [list(p) for p in z["polygon"]]} for z in self.exclusion_zones
            ]
        if self.count_lines:
            result["count_lines"] = {
                name: {"p1": list(cl["p1"]), "p2": list(cl["p2"])} for name, cl in self.count_lines.items()
            }
        return result

    def save(self, camera_yaml_path: str | Path) -> None:
        camera_yaml_path = Path(camera_yaml_path)
        existing = {}
        if camera_yaml_path.exists():
            with open(camera_yaml_path) as f:
                existing = yaml.safe_load(f) or {}

        merged = dict(existing)
        merged.update(self.to_camera_dict())

        camera_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        with open(camera_yaml_path, "w") as f:
            yaml.safe_dump(merged, f, default_flow_style=False, sort_keys=False)


def main() -> None:
    import argparse

    import cv2

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, help="video file to grab the first frame from")
    parser.add_argument("--camera", required=True, help="camera YAML to merge annotations into")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"could not open video: {args.video}")
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"could not read a frame from: {args.video}")

    state = AnnotationState()
    window = "annotate_roi (r/l/e/c start, n finish, u undo, s save, q quit)"
    cv2.namedWindow(window)

    def on_mouse(event, x, y, _flags, _userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
            try:
                state.add_vertex((float(x), float(y)))
            except ValueError as exc:
                print(exc)

    cv2.setMouseCallback(window, on_mouse)

    def render():
        canvas = frame.copy()
        for name, poly in state.rois.items():
            pts = [(int(x), int(y)) for x, y in poly]
            for p in pts:
                cv2.circle(canvas, p, 3, (0, 255, 0), -1)
            if len(pts) > 1:
                cv2.polylines(canvas, [_np_array(pts)], True, (0, 255, 0), 2)
            cv2.putText(canvas, name, pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        for zone in state.exclusion_zones:
            pts = [(int(x), int(y)) for x, y in zone["polygon"]]
            cv2.polylines(canvas, [_np_array(pts)], True, (0, 0, 255), 2)
            cv2.putText(canvas, zone["name"], pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        for name, cl in state.count_lines.items():
            p1 = (int(cl["p1"][0]), int(cl["p1"][1]))
            p2 = (int(cl["p2"][0]), int(cl["p2"][1]))
            cv2.line(canvas, p1, p2, (255, 0, 0), 2)
            cv2.putText(canvas, name, p1, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        if state.current is not None:
            pts = [(int(x), int(y)) for x, y in state.current.points]
            for p in pts:
                cv2.circle(canvas, p, 3, (0, 255, 255), -1)
            if len(pts) > 1:
                cv2.polylines(canvas, [_np_array(pts)], False, (0, 255, 255), 1)
        cv2.imshow(window, canvas)

    while True:
        render()
        key = cv2.waitKey(20) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("s"):
            state.save(args.camera)
            print(f"saved annotations into {args.camera}")
            break
        elif key == ord("r"):
            state.start_road()
        elif key == ord("l"):
            state.start_live_lane()
        elif key == ord("e"):
            name = state.start_exclusion_zone()
            print(f"started exclusion zone '{name}'")
        elif key == ord("c"):
            name = state.start_count_line()
            print(f"started count line '{name}'")
        elif key == ord("u"):
            state.undo_vertex()
        elif key == ord("n"):
            try:
                if state.current is not None and state.current.target == "count_line":
                    default_name = state.current.name
                    typed = input(f"name for this count line [{default_name}]: ").strip()
                    state.finish_shape(rename_to=typed or None)
                else:
                    state.finish_shape()
            except ValueError as exc:
                print(exc)

    cv2.destroyAllWindows()


def _np_array(pts: list[tuple[int, int]]):
    import numpy as np

    return np.array(pts, dtype=np.int32)


if __name__ == "__main__":
    main()
