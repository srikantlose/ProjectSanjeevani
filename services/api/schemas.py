"""Pydantic request schemas mirroring plan.md §8.2 (TS mirror: apps/dashboard/src/types/events.ts)."""

from __future__ import annotations

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float
    label: str


class Evidence(BaseModel):
    clip_path: str
    snapshot_path: str


class CandidateSubmission(BaseModel):
    id: str
    camera_id: str
    mode: str
    severity: str
    severity_reasons: list[str]
    signals: dict[str, float]
    reasons: list[str]
    location: Location
    evidence: Evidence
    detected_at: str


class VerifyRequest(BaseModel):
    decision: str  # "confirm" | "reject"
