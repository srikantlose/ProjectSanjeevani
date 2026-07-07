from services.detection.signals.flow import BIN_DURATION_S, FlowSignal
from tests.conftest import SyntheticTrack

COUNT_LINE = {"north_approach": ((0.0, 100.0), (1000.0, 100.0))}


def _flow_frames(bin_crossing_counts, fps=1.0):
    """Builds a frame sequence where each bin has the given number of tracks
    crossing the horizontal count line at y=100 (each crossing track appears
    for exactly two frames: one just above the line, one just below)."""
    frames_per_bin = int(BIN_DURATION_S * fps)
    frames = []
    next_id = 1000
    for count in bin_crossing_counts:
        bin_frames = [[] for _ in range(frames_per_bin)]
        if count > 0:
            step = max(1, frames_per_bin // count)
            for i in range(count):
                offset = i * step
                end = min(offset + 1, frames_per_bin - 1)
                if end == offset:
                    offset = max(0, end - 1)
                tid = next_id
                next_id += 1
                bin_frames[offset].append(SyntheticTrack(tid, "car", (500, 85, 540, 95)))
                bin_frames[end].append(SyntheticTrack(tid, "car", (500, 105, 540, 115)))
        frames.extend(bin_frames)
    return frames


def test_flow_collapse_fires_after_two_low_bins(frame_context_builder):
    # 8 baseline bins at ~4 crossings/bin, then 4 bins with zero crossings (traffic stopped).
    bin_counts = [4] * 8 + [0] * 4
    contexts = frame_context_builder(_flow_frames(bin_counts, fps=1.0), fps=1.0)
    signal = FlowSignal(count_lines=COUNT_LINE)

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.4


def test_steady_traffic_does_not_fire(frame_context_builder):
    bin_counts = [4] * 12
    contexts = frame_context_builder(_flow_frames(bin_counts, fps=1.0), fps=1.0)
    signal = FlowSignal(count_lines=COUNT_LINE)

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0
