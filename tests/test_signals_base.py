from services.detection.signals.base import Signal, SignalResult
from tests.conftest import SyntheticTrack


class NoOpSignal(Signal):
    name = "noop"

    def update(self, frame_ctx):
        return SignalResult(score=0.0, reasons=[], fired_track_ids=[])


def test_noop_signal_runs_against_synthetic_fixture(frame_context_builder):
    contexts = frame_context_builder(
        [
            [SyntheticTrack(1, "car", (0, 0, 40, 20))],
            [SyntheticTrack(1, "car", (10, 0, 50, 20))],
        ]
    )

    signal = NoOpSignal()
    results = [signal.update(ctx) for ctx in contexts]

    assert len(results) == 2
    assert all(isinstance(r, SignalResult) for r in results)
    assert all(r.score == 0.0 for r in results)
