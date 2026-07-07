from collections import Counter

from services.detection.detector import Detector
from services.detection.video_source import VideoSource


def test_stable_track_ids_persist_across_frames(vtest_video):
    detector = Detector()
    src = VideoSource(vtest_video, target_fps=10, speed_factor=20.0)

    id_frame_counts: Counter[int] = Counter()
    n_frames = 0
    for frame in src:
        dets = detector.track(frame.image)
        for d in dets:
            if d.track_id is not None:
                id_frame_counts[d.track_id] += 1
        n_frames += 1
        if n_frames >= 40:
            break

    # The background car/truck are stationary and unoccluded — their track IDs
    # should persist across almost every processed frame, proving ByteTrack
    # maintains identity rather than re-detecting a fresh ID each frame.
    assert n_frames >= 20
    most_stable_counts = sorted(id_frame_counts.values(), reverse=True)[:2]
    assert most_stable_counts[0] >= n_frames * 0.9
    assert most_stable_counts[1] >= n_frames * 0.9
