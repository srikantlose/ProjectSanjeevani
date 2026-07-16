"""Green corridor sequencer (plan.md §9.4).

One `CorridorController` instance lives for the lifetime of a single dispatch
(created by the ambulance mover, E6-T3), re-`set_route()` when the ambulance
moves onto its second leg (scene -> hospital).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.api.models import CorridorJunction
from services.api.sim.geo import Coord, project_distance
from services.api.ws import manager

PROXIMITY_M = 30.0
LOOKAHEAD_M = 500.0
REVERT_DELAY_S = 10.0


@dataclass
class _JunctionState:
    junction_id: str
    name: str
    route_dist_m: float
    is_green: bool = False
    passed_at: float | None = None  # monotonic seconds when the ambulance was first observed past it


class CorridorController:
    def __init__(self, dispatch_id: str, db: Session):
        self.dispatch_id = dispatch_id
        self._db = db
        self._junctions: list[_JunctionState] = []

    def set_route(self, coords: list[Coord], cumdist: list[float]) -> None:
        junctions = self._db.query(CorridorJunction).all()
        selected = []
        for j in junctions:
            route_dist_m, offset_m = project_distance(coords, cumdist, j.lat, j.lon)
            if offset_m <= PROXIMITY_M:
                selected.append(_JunctionState(junction_id=j.id, name=j.name, route_dist_m=route_dist_m))
        self._junctions = selected

    async def update(self, ambulance_route_dist: float, now_s: float) -> None:
        for j in self._junctions:
            should_be_green = 0 <= (j.route_dist_m - ambulance_route_dist) <= LOOKAHEAD_M
            if should_be_green and not j.is_green:
                j.is_green = True
                j.passed_at = None
                await manager.broadcast(
                    "corridor.updated",
                    {"dispatch_id": self.dispatch_id, "junction_id": j.junction_id, "junction_name": j.name, "signal_state": "GREEN"},
                )
            elif not should_be_green and j.is_green and ambulance_route_dist > j.route_dist_m:
                if j.passed_at is None:
                    j.passed_at = now_s
                elif now_s - j.passed_at >= REVERT_DELAY_S:
                    j.is_green = False
                    j.passed_at = None
                    await manager.broadcast(
                        "corridor.updated",
                        {"dispatch_id": self.dispatch_id, "junction_id": j.junction_id, "junction_name": j.name, "signal_state": "DEFAULT"},
                    )

    def speed_multiplier(self, ambulance_route_dist: float) -> float:
        for j in self._junctions:
            if j.is_green and ambulance_route_dist <= j.route_dist_m <= ambulance_route_dist + LOOKAHEAD_M:
                return 1.4
        return 1.0
