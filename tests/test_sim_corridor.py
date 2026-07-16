import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.db import Base
from services.api.models import CorridorJunction
from services.api.sim import corridor as corridor_module
from services.api.sim.corridor import CorridorController
from services.api.sim.geo import polyline_cumdist


class _RecordingManager:
    def __init__(self):
        self.messages = []

    async def broadcast(self, type_, payload):
        self.messages.append((type_, payload))


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_junction_turns_green_within_500m_and_reverts_after_pass(monkeypatch):
    recorder = _RecordingManager()
    monkeypatch.setattr(corridor_module, "manager", recorder)

    db = _make_db()
    # A straight route due north at lon=0, ~2200m total (0.02 degrees lat),
    # densely sampled (~22m between vertices) -- project_distance uses a
    # nearest-vertex approximation (plan.md §9.2), so a sparse 2-point line
    # would put any midpoint junction ~1km from the "nearest vertex", same as
    # real OSRM routes are dense (E6-T2 found ~1 vertex per 27m on a real route).
    n_points = 100
    coords = [(0.0, 0.02 * i / n_points) for i in range(n_points + 1)]
    cumdist = polyline_cumdist(coords)
    total_dist = cumdist[-1]

    # Junction sitting almost exactly on the route, at roughly the midpoint.
    mid_lat = 0.01
    db.add(CorridorJunction(id="jct_test", name="Test Junction", lat=mid_lat, lon=0.0))
    db.commit()

    controller = CorridorController("disp_test", db)
    controller.set_route(coords, cumdist)
    assert len(controller._junctions) == 1
    junction_route_dist = controller._junctions[0].route_dist_m

    clock = {"t": 0.0}

    async def run():
        # Before the 500m lookahead window: signal_state should stay DEFAULT (no broadcast).
        far_before = junction_route_dist - 600
        await controller.update(max(0.0, far_before), clock["t"])
        assert recorder.messages == []
        assert controller.speed_multiplier(max(0.0, far_before)) == 1.0

        # Within 500m upstream: should turn GREEN.
        near_before = junction_route_dist - 300
        await controller.update(near_before, clock["t"])
        assert recorder.messages[-1] == (
            "corridor.updated",
            {"dispatch_id": "disp_test", "junction_id": "jct_test", "junction_name": "Test Junction", "signal_state": "GREEN"},
        )
        assert controller.speed_multiplier(near_before) == 1.4

        # Just past the junction: still GREEN (revert delay hasn't elapsed).
        just_past = junction_route_dist + 5
        await controller.update(just_past, clock["t"])
        assert recorder.messages[-1][1]["signal_state"] == "GREEN"  # unchanged, no new broadcast for this

        # 10+ seconds after being observed past it: should revert to DEFAULT.
        clock["t"] += 11.0
        await controller.update(just_past, clock["t"])
        assert recorder.messages[-1] == (
            "corridor.updated",
            {"dispatch_id": "disp_test", "junction_id": "jct_test", "junction_name": "Test Junction", "signal_state": "DEFAULT"},
        )

    asyncio.run(run())


def test_junction_far_from_route_is_not_selected():
    db = _make_db()
    coords = [(0.0, 0.0), (0.0, 0.02)]
    cumdist = polyline_cumdist(coords)

    # ~1km east of the route -- well outside the 30m proximity threshold.
    db.add(CorridorJunction(id="jct_far", name="Far Junction", lat=0.01, lon=0.01))
    db.commit()

    controller = CorridorController("disp_test", db)
    controller.set_route(coords, cumdist)

    assert controller._junctions == []
