import math

from services.detection.signals.crowd import CrowdSignal
from tests.conftest import SyntheticTrack


def _converging_frames(n_people=5, n_converge_frames=20, n_settle_frames=6, start_radius=200.0, end_radius=10.0, center=(500.0, 500.0)):
    """5 pedestrians start scattered around `center` and walk steadily inward,
    converging on the same point, then stop and stay put — bystanders rushing
    to an occluded crash and then stopping to look, not just passing through."""
    frames = []
    for frame_i in range(n_converge_frames):
        frac = frame_i / (n_converge_frames - 1)
        radius = start_radius + (end_radius - start_radius) * frac
        frame_tracks = []
        for p in range(n_people):
            angle = 2 * math.pi * p / n_people
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            frame_tracks.append(SyntheticTrack(100 + p, "person", (x - 10, y - 20, x + 10, y + 20)))
        frames.append(frame_tracks)
    for _ in range(n_settle_frames):
        frame_tracks = []
        for p in range(n_people):
            angle = 2 * math.pi * p / n_people
            x = center[0] + end_radius * math.cos(angle)
            y = center[1] + end_radius * math.sin(angle)
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


def _flowing_crosswalk_frames(n_people=6, n_frames=20):
    """A crosswalk's worth of pedestrians joins a tightly-spaced walking line
    one by one (real growth, real spatial clustering) but everyone keeps
    walking through at a steady pace and nobody ever stops — this must not be
    mistaken for bystanders gathering around an incident."""
    frames = []
    for frame_i in range(n_frames):
        frame_tracks = []
        for p in range(n_people):
            entry_frame = p * 2
            if frame_i < entry_frame:
                continue
            local_i = frame_i - entry_frame
            x = 100 + p * 25 + local_i * 12
            y = 300
            frame_tracks.append(SyntheticTrack(300 + p, "person", (x - 10, y - 20, x + 10, y + 20)))
        frames.append(frame_tracks)
    return frames


def test_converging_crowd_settles_and_fires(frame_context_builder):
    # 26 frames at fps=2.0 -> 12.5s: people converge gradually, then stop and
    # stay put, well within the 8s formation window measured from when
    # clustering first appears (not from the start of the clip).
    contexts = frame_context_builder(_converging_frames(), fps=2.0)
    signal = CrowdSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) >= 0.7


def test_stable_parallel_group_does_not_fire(frame_context_builder):
    contexts = frame_context_builder(_parallel_walkers_frames(), fps=2.0)
    signal = CrowdSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0


def test_flowing_crosswalk_group_does_not_fire(frame_context_builder):
    # Grows and spatially clusters just like real bystanders, but never stops
    # moving -- the settling check (not the growth check) must be what blocks it.
    contexts = frame_context_builder(_flowing_crosswalk_frames(), fps=2.0)
    signal = CrowdSignal()

    scores = [signal.update(ctx).score for ctx in contexts]

    assert max(scores) == 0.0
