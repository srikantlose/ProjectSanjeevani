"""Incident candidate ingestion + list/detail endpoints (plan.md §8.1, §8.2)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import Incident, IncidentSignal
from services.api.schemas import CandidateSubmission
from services.api.ws import manager

router = APIRouter()


def incident_to_payload(incident: Incident) -> dict:
    return {
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

    await manager.broadcast("incident.new", incident_to_payload(incident))

    return {"id": incident.id}


@router.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.query(Incident).order_by(Incident.detected_at.desc()).all()
    return [incident_to_payload(r) for r in rows]


@router.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident_to_payload(incident)
