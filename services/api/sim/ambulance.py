"""Ambulance dispatch simulation (plan.md §9.3).

`tick_interval_s` is purely a wall-clock speed-up factor -- it's both the real
`asyncio.sleep` duration between ticks AND the multiplier applied to
SCENE_DWELL_S. It deliberately does NOT affect how far the ambulance moves per
tick: that's always `speed * SIMULATED_SECONDS_PER_TICK` (a fixed 1 simulated
second per tick, i.e. real 1 Hz ticks), so the number of ticks a leg takes is
independent of tick_interval_s. Coupling the per-tick distance to
tick_interval_s as well would cancel out: half the sleep time but also half
the distance per tick means twice as many ticks, so the total wall-clock time
would stay the same regardless of tick_interval_s -- exactly the opposite of
what a "run 200x faster for tests" parameter needs to do. Production uses
tick_interval_s=1.0 (real-time); tests pass e.g. 0.005 to finish in ms.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session, sessionmaker

from services.api.models import Ambulance, Dispatch, Hospital, Incident
from services.api.sim import hospital as hospital_module
from services.api.sim.corridor import CorridorController
from services.api.sim.geo import haversine_m, point_at_distance, polyline_cumdist
from services.api.sim.routing import get_route
from services.api.ws import manager

BASE_SPEED_KMH = 35.0
BASE_SPEED_MPS = BASE_SPEED_KMH / 3.6
SCENE_DWELL_S = 45.0
ARRIVAL_THRESHOLD_M = 15.0
SIMULATED_SECONDS_PER_TICK = 1.0  # 1 Hz: fixed simulated-time step, independent of tick_interval_s


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _next_dispatch_id(db: Session) -> str:
    return f"disp_{db.query(Dispatch).count() + 1:04d}"


def dispatch_incident(incident: Incident, db: Session, tick_interval_s: float = 1.0) -> dict:
    """Selects the nearest idle ambulance + destination hospital, creates the
    `dispatches` row, marks the ambulance BUSY, and schedules the background
    movement task. Returns the dict embedded in the DISPATCHED broadcast."""
    idle_ambulances = db.query(Ambulance).filter(Ambulance.status == "IDLE").all()
    if not idle_ambulances:
        raise RuntimeError("no idle ambulances available")
    nearest = min(idle_ambulances, key=lambda a: haversine_m(incident.lat, incident.lon, a.current_lat, a.current_lon))

    hosp = hospital_module.select_hospital(incident, db)

    route = get_route(nearest.current_lat, nearest.current_lon, incident.lat, incident.lon)
    eta_seconds_initial = route["distance_m"] / BASE_SPEED_MPS

    dispatch = Dispatch(
        id=_next_dispatch_id(db),
        incident_id=incident.id,
        ambulance_id=nearest.id,
        hospital_id=hosp.id,
        route_to_scene_geojson=json.dumps(route),
        state="TO_SCENE",
        eta_seconds_initial=eta_seconds_initial,
        created_at=_now_iso(),
    )
    db.add(dispatch)
    nearest.status = "BUSY"
    db.commit()

    # run_dispatch is a fire-and-forget background task that outlives this request,
    # so it needs its own DB session -- but it must bind to the SAME engine the
    # request used (not the global production SessionLocal), or it silently
    # operates on the wrong database in tests (and is just bad practice generally).
    session_factory = sessionmaker(bind=db.get_bind())
    asyncio.create_task(run_dispatch(dispatch.id, session_factory, tick_interval_s=tick_interval_s))

    return {
        "dispatch_id": dispatch.id,
        "ambulance_id": nearest.id,
        "hospital_id": hosp.id,
        "hospital_name": hosp.name,
        "eta_seconds": eta_seconds_initial,
        "route": route["coordinates"],
    }


async def _drive_leg(
    dispatch_id: str,
    ambulance: Ambulance,
    corridor: CorridorController,
    coords: list,
    cumdist: list[float],
    state_label: str,
    tick_interval_s: float,
    db: Session,
) -> None:
    total_dist = cumdist[-1]
    traveled = 0.0
    while True:
        await corridor.update(traveled, time.monotonic())
        speed = BASE_SPEED_MPS * corridor.speed_multiplier(traveled)
        traveled = min(total_dist, traveled + speed * SIMULATED_SECONDS_PER_TICK)

        lat, lon, heading = point_at_distance(coords, cumdist, traveled)
        ambulance.current_lat, ambulance.current_lon = lat, lon
        remaining = total_dist - traveled
        eta = remaining / speed if speed > 0 else 0.0

        await manager.broadcast(
            "ambulance.position",
            {
                "dispatch_id": dispatch_id,
                "ambulance_id": ambulance.id,
                "lat": lat,
                "lon": lon,
                "heading_deg": heading,
                "state": state_label,
                "eta_seconds": eta,
            },
        )
        db.commit()

        if total_dist - traveled <= ARRIVAL_THRESHOLD_M:
            break
        await asyncio.sleep(tick_interval_s)


async def run_dispatch(dispatch_id: str, session_factory: sessionmaker, tick_interval_s: float = 1.0) -> None:
    db = session_factory()
    try:
        dispatch = db.get(Dispatch, dispatch_id)
        incident = db.get(Incident, dispatch.incident_id)
        ambulance = db.get(Ambulance, dispatch.ambulance_id)
        hosp = db.get(Hospital, dispatch.hospital_id)

        signals = json.loads(incident.signals)
        incident_type = hospital_module.determine_incident_type(signals)

        scene_route = json.loads(dispatch.route_to_scene_geojson)
        scene_coords = [tuple(c) for c in scene_route["coordinates"]]
        scene_cumdist = polyline_cumdist(scene_coords)

        corridor = CorridorController(dispatch_id, db)
        corridor.set_route(scene_coords, scene_cumdist)

        await _drive_leg(dispatch_id, ambulance, corridor, scene_coords, scene_cumdist, "TO_SCENE", tick_interval_s, db)

        dispatch.state = "AT_SCENE"
        dispatch.arrived_scene_at = _now_iso()
        db.commit()

        hospital_route = get_route(incident.lat, incident.lon, hosp.lat, hosp.lon)
        dispatch.route_to_hospital_geojson = json.dumps(hospital_route)
        db.commit()

        eta_to_hospital = hospital_route["distance_m"] / BASE_SPEED_MPS
        await hospital_module.fire_prealert(dispatch, hosp, incident.severity, incident_type, eta_to_hospital)

        await asyncio.sleep(SCENE_DWELL_S * tick_interval_s)

        dispatch.state = "TO_HOSPITAL"
        dispatch.departed_scene_at = _now_iso()
        db.commit()

        hospital_coords = [tuple(c) for c in hospital_route["coordinates"]]
        hospital_cumdist = polyline_cumdist(hospital_coords)
        corridor.set_route(hospital_coords, hospital_cumdist)

        await _drive_leg(dispatch_id, ambulance, corridor, hospital_coords, hospital_cumdist, "TO_HOSPITAL", tick_interval_s, db)

        dispatch.state = "ARRIVED"
        dispatch.arrived_hospital_at = _now_iso()
        ambulance.status = "IDLE"
        ambulance.current_lat, ambulance.current_lon = hosp.lat, hosp.lon
        incident.status = "RESOLVED"
        db.commit()

        await manager.broadcast("incident.updated", {"id": incident.id, "status": "RESOLVED"})
    finally:
        db.close()
