import cv2
import numpy as np

from services.detection.engine import run


def test_debug_overlay_produces_playable_annotated_video(vtest_video, tmp_path):
    out_path = tmp_path / "debug_out.mp4"
    result_path = run(
        str(vtest_video),
        target_fps=5,
        speed_factor=30.0,
        debug_overlay=True,
        output_path=str(out_path),
        max_frames=15,
    )

    assert result_path == str(out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    cap = cv2.VideoCapture(str(out_path))
    assert cap.isOpened()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert frame_count >= 10  # some frames may be dropped by the mp4v encoder's keyframe handling

    # Confirm overlay pixels were actually drawn (boxes/labels), not just raw passthrough frames:
    # the annotator draws in pure green (0, 255, 0) and orange (0, 128, 255) which the source
    # footage (a muted outdoor scene) is not expected to contain.
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
