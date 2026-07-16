"""Hospital selection + pre-alert firing (plan.md §9.5).

`select_hospital` is needed by the ambulance mover (E6-T3) at dispatch time, so
it's built alongside that task rather than waiting for E6-T5 — see PROGRESS.md.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from services.api.models import Dispatch, Hospital, Incident
from services.api.sim.geo import haversine_m
from services.api.ws import manager

TRAUMA_PREFERENCE_MULTIPLIER = 1.5


def select_hospital(incident: Incident, db: Session) -> Hospital:
    hospitals = db.query(Hospital).all()
    if not hospitals:
        raise RuntimeError("no hospitals seeded")

    ranked = sorted(hospitals, key=lambda h: haversine_m(incident.lat, incident.lon, h.lat, h.lon))
    nearest = ranked[0]

    if incident.severity == "HIGH":
        trauma_l1 = [h for h in ranked if h.trauma_level == 1]
        if trauma_l1:
            nearest_l1 = trauma_l1[0]
            nearest_dist = haversine_m(incident.lat, incident.lon, nearest.lat, nearest.lon)
            l1_dist = haversine_m(incident.lat, incident.lon, nearest_l1.lat, nearest_l1.lon)
            if l1_dist <= TRAUMA_PREFERENCE_MULTIPLIER * nearest_dist:
                return nearest_l1

    return nearest


def determine_incident_type(signals: dict[str, float]) -> str:
    if signals.get("rider_down", 0.0) >= 0.85:
        return "rider_down"
    if signals.get("collision", 0.0) >= 0.6:
        return "collision"
    if signals.get("stationary", 0.0) >= 0.85:
        return "stationary_vehicle"
    return "unspecified"


async def fire_prealert(dispatch: Dispatch, hospital: Hospital, severity: str, incident_type: str, eta_seconds: float) -> None:
    await manager.broadcast(
        "hospital.alert",
        {
            "dispatch_id": dispatch.id,
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "severity": severity,
            "incident_type": incident_type,
            "eta_seconds": eta_seconds,
        },
    )
