"""SQLAlchemy ORM models (plan.md §8.3)."""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from services.api.db import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    camera_id = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDING_VERIFICATION")
    severity = Column(String, nullable=True)
    severity_reasons = Column(Text, nullable=False, default="[]")
    signals = Column(Text, nullable=False, default="{}")
    reasons = Column(Text, nullable=False, default="[]")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    location_label = Column(String, nullable=False)
    evidence_clip_path = Column(String, nullable=True)
    evidence_snapshot_path = Column(String, nullable=True)
    detected_at = Column(String, nullable=False)
    verified_at = Column(String, nullable=True)
    verify_decision = Column(String, nullable=True)

    signal_rows = relationship("IncidentSignal", back_populates="incident", cascade="all, delete-orphan")
    dispatches = relationship("Dispatch", back_populates="incident", cascade="all, delete-orphan")


class IncidentSignal(Base):
    __tablename__ = "incident_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    signal_name = Column(String, nullable=False)
    score = Column(Float, nullable=False)

    incident = relationship("Incident", back_populates="signal_rows")


class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(String, primary_key=True)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    ambulance_id = Column(String, ForeignKey("ambulances.id"), nullable=False)
    hospital_id = Column(String, ForeignKey("hospitals.id"), nullable=False)
    route_to_scene_geojson = Column(Text, nullable=True)
    route_to_hospital_geojson = Column(Text, nullable=True)
    state = Column(String, nullable=False, default="TO_SCENE")
    eta_seconds_initial = Column(Float, nullable=True)
    created_at = Column(String, nullable=False)
    arrived_scene_at = Column(String, nullable=True)
    departed_scene_at = Column(String, nullable=True)
    arrived_hospital_at = Column(String, nullable=True)

    incident = relationship("Incident", back_populates="dispatches")


class Ambulance(Base):
    __tablename__ = "ambulances"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    home_lat = Column(Float, nullable=False)
    home_lon = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="IDLE")
    current_lat = Column(Float, nullable=False)
    current_lon = Column(Float, nullable=False)


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    trauma_level = Column(Integer, nullable=False)


class CorridorJunction(Base):
    __tablename__ = "corridor_junctions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_at = Column(String, nullable=False)
    manifest_path = Column(String, nullable=False)
    results_json = Column(Text, nullable=False)
