"""Incident candidate ingestion + list/detail endpoints (plan.md §8.1, §8.2)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import Hospital, Incident, IncidentSignal
from services.api.schemas import CandidateSubmission, VerifyRequest
from services.api.sim.ambulance import dispatch_incident
from services.api.ws import manager

router = APIRouter()


def _dispatch_payload(incident: Incident, db: Session) -> dict | None:
    """Same shape as the DISPATCHED WS broadcast (plan.md §8.2.2), so a client
    that (re)loads via REST after a dispatch already happened -- e.g. a page
    refresh mid-demo -- still gets the ambulance/hospital/route info, not just
    clients that were connected at the moment it was originally broadcast."""
    dispatches = sorted(incident.dispatches, key=lambda d: d.created_at)
    if not dispatches:
        return None
    dispatch = dispatches[-1]
    hospital = db.get(Hospital, dispatch.hospital_id)
    route = json.loads(dispatch.route_to_scene_geojson)["coordinates"] if dispatch.route_to_scene_geojson else []
    return {
        "dispatch_id": dispatch.id,
        "ambulance_id": dispatch.ambulance_id,
        "hospital_id": dispatch.hospital_id,
        "hospital_name": hospital.name if hospital else None,
        "eta_seconds": dispatch.eta_seconds_initial,
        "route": route,
    }


def incident_to_payload(incident: Incident, db: Session) -> dict:
    payload = {
        "id": incident.id,
        "camera_id": incident.camera_id,
        "mode": incident.mode,
        "status": incident.status,
        "severity": incident.severity,
        "severity_reasons": json.loads(incident.severity_reasons),
        "signals": json.loads(incident.signals),
        "reasons": json.loads(incident.reasons),
        "location": {"lat": incident.lat, "lon": incident.lon, "label": incident.location_label},
        "evidence": {
            "clip_url": f"/media/{incident.id}/evidence.mp4" if incident.evidence_clip_path else None,
            "snapshot_url": f"/media/{incident.id}/snapshot.jpg" if incident.evidence_snapshot_path else None,
        },
        "detected_at": incident.detected_at,
    }
    dispatch = _dispatch_payload(incident, db)
    if dispatch is not None:
        payload["dispatch"] = dispatch
    return payload


@router.post("/api/incidents/candidate", status_code=201)
async def create_candidate(body: CandidateSubmission, db: Session = Depends(get_db)):
    existing = db.get(Incident, body.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"incident {body.id} already exists")

    incident = Incident(
        id=body.id,
        camera_id=body.camera_id,
        mode=body.mode,
        status="PENDING_VERIFICATION",
        severity=body.severity,
        severity_reasons=json.dumps(body.severity_reasons),
        signals=json.dumps(body.signals),
        reasons=json.dumps(body.reasons),
        lat=body.location.lat,
        lon=body.location.lon,
        location_label=body.location.label,
        evidence_clip_path=body.evidence.clip_path,
        evidence_snapshot_path=body.evidence.snapshot_path,
        detected_at=body.detected_at,
    )
    db.add(incident)
    for name, score in body.signals.items():
        db.add(IncidentSignal(incident_id=incident.id, signal_name=name, score=score))
    db.commit()

    await manager.broadcast("incident.new", incident_to_payload(incident, db))

    return {"id": incident.id}


@router.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.query(Incident).order_by(Incident.detected_at.desc()).all()
    return [incident_to_payload(r, db) for r in rows]


@router.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident_to_payload(incident, db)


@router.post("/api/incidents/{incident_id}/verify")
async def verify_incident(incident_id: str, body: VerifyRequest, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    if incident.status != "PENDING_VERIFICATION":
        raise HTTPException(status_code=409, detail=f"incident is {incident.status}, not PENDING_VERIFICATION")

    if body.decision == "reject":
        incident.status = "REJECTED"
        db.commit()
        await manager.broadcast("incident.updated", {"id": incident.id, "status": incident.status})
        return {"id": incident.id, "status": incident.status}

    if body.decision == "confirm":
        incident.status = "CONFIRMED"
        db.commit()
        await manager.broadcast("incident.updated", {"id": incident.id, "status": incident.status})

        dispatch_dict = dispatch_incident(incident, db)

        incident.status = "DISPATCHED"
        db.commit()
        await manager.broadcast(
            "incident.updated", {"id": incident.id, "status": incident.status, "dispatch": dispatch_dict}
        )

        return {"id": incident.id, "status": incident.status}

    raise HTTPException(status_code=400, detail=f"invalid decision: {body.decision!r} (must be confirm or reject)")
