import math

from services.detection.signals.crowd import CrowdSignal
from tests.conftest import SyntheticTrack


def _converging_frames(n_people=5, n_frames=12, start_radius=200.0, end_radius=15.0, center=(500.0, 500.0)):
    """5 pedestrians start scattered around `center` and walk steadily inward,
    converging on the same point — the occluded-crash bystander-clustering scenario."""
    frames = []
    for frame_i in range(n_frames):
        frac = frame_i / (n_frames - 1)
        radius = start_radius + (end_radius - start_radius) * frac
        frame_tracks = []
        for p in range(n_people):
            angle = 2 * math.pi * p / n_people
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            frame_tracks.append(SyntheticTrack(100 + p, "person", (x - 10, y - 20, x + 10, y + 20)))
        frames.append(frame_tracks)
    return frames


def _parallel_walkers_frames(n_people=10, n_frames=20):
    """10 pedestrians already walking together as a stable group (e.g. a sidewalk
    crowd) — closely spaced so they cluster, but with no growth and no convergence."""
    frames = []
    for frame_i in range(n_frames):
        frame_tracks = []
        for p in range(n_people):
            x = 100 + p * 20 + frame_i * 10
            y = 300
            frame_tracks.append(SyntheticTrack(200 + p, "person", (x - 10, y - 20, x + 10, y + 20)))
        frames.append(frame_tracks)
    return frames


def test_converging_crowd_fires_within_6s(frame_context_builder):
    # 12 frames at fps=2.0 -> 5.5s span, well within the "6s" acceptance window.
    contexts = frame_context_builder(_converging_frames(), fps=2.0)
    signal = CrowdSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) >= 0.7


def test_stable_parallel_group_does_not_fire(frame_context_builder):
    contexts = frame_context_builder(_parallel_walkers_frames(), fps=2.0)
    signal = CrowdSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0
