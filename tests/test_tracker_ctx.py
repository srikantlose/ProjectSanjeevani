from services.detection.detector import Detection
from services.detection.tracker_ctx import TrackHistoryBuilder


def _detection_at(track_id: int, x: float, y: float, w: float = 40.0, h: float = 80.0) -> Detection:
    return Detection(track_id=track_id, cls="car", conf=0.9, bbox=(x, y, x + w, y + h))


def test_velocity_matches_known_pixel_rate():
    builder = TrackHistoryBuilder(smoothing_window=5)

    # Track moves +10 px/frame in x, +2 px/frame in y, starting at (0, 0).
    dx, dy = 10.0, 2.0
    ctx = None
    for frame_index in range(8):
        x, y = dx * frame_index, dy * frame_index
        detections = [_detection_at(1, x, y)]
        ctx = builder.update(frame_index=frame_index, timestamp_s=frame_index / 10.0, detections=detections)

    assert ctx is not None
    track = ctx.tracks[1]
    assert track.age_frames == 8
    assert abs(track.velocity[0] - dx) < 0.1
    assert abs(track.velocity[1] - dy) < 0.1


def test_bbox_aspect_ratio():
    builder = TrackHistoryBuilder()
    ctx = builder.update(frame_index=0, timestamp_s=0.0, detections=[_detection_at(1, 0, 0, w=60, h=30)])
    assert abs(ctx.tracks[1].bbox_aspect - 2.0) < 1e-6


def test_velocity_zero_on_first_frame():
    builder = TrackHistoryBuilder()
    ctx = builder.update(frame_index=0, timestamp_s=0.0, detections=[_detection_at(1, 0, 0)])
    assert ctx.tracks[1].velocity == (0.0, 0.0)


def test_untracked_detection_ignored():
    builder = TrackHistoryBuilder()
    untracked = Detection(track_id=None, cls="person", conf=0.5, bbox=(0, 0, 10, 10))
    ctx = builder.update(frame_index=0, timestamp_s=0.0, detections=[untracked])
    assert ctx.tracks == {}
