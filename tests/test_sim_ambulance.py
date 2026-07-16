import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.db import Base
from services.api.models import Ambulance, Hospital, Incident
from services.api.sim import ambulance as ambulance_module
from services.api.sim import corridor as corridor_module
from services.api.sim import hospital as hospital_module

AMBULANCE_HOME = (12.9430, 77.5960)
INCIDENT_LOCATION = (12.9730, 77.6194)
HOSPITAL_LOCATION = (12.9293, 77.6198)

# ~2km straight line for both legs (amb->scene and scene->hospital) -- the mock
# doesn't need to reflect real geography, just be short enough to tick through fast.
FAKE_ROUTE = {
    "coordinates": [[77.6000, 12.9500], [77.6100, 12.9600], [77.6194, 12.9700]],
    "distance_m": 2000.0,
}


class _RecordingManager:
    def __init__(self):
        self.messages = []

    async def broadcast(self, type_, payload):
        self.messages.append((type_, payload))


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed(db):
    db.add(Hospital(id="hosp_test", name="Test Hospital", lat=HOSPITAL_LOCATION[0], lon=HOSPITAL_LOCATION[1], trauma_level=1))
    db.add(
        Ambulance(
            id="amb_test",
            name="Test Ambulance",
            home_lat=AMBULANCE_HOME[0],
            home_lon=AMBULANCE_HOME[1],
            status="IDLE",
            current_lat=AMBULANCE_HOME[0],
            current_lon=AMBULANCE_HOME[1],
        )
    )
    incident = Incident(
        id="inc_test",
        camera_id="cam1",
        mode="city",
        status="CONFIRMED",
        severity="HIGH",
        severity_reasons="[]",
        signals=json.dumps({"rider_down": 0.95}),
        reasons="[]",
        lat=INCIDENT_LOCATION[0],
        lon=INCIDENT_LOCATION[1],
        location_label="Test Incident Location",
        detected_at="2026-01-01T00:00:00.000Z",
    )
    db.add(incident)
    db.commit()
    return incident


def test_full_dispatch_lifecycle_state_sequence(monkeypatch):
    recorder = _RecordingManager()
    monkeypatch.setattr(ambulance_module, "manager", recorder)
    monkeypatch.setattr(corridor_module, "manager", recorder)
    monkeypatch.setattr(hospital_module, "manager", recorder)
    monkeypatch.setattr(ambulance_module, "get_route", lambda *a, **kw: dict(FAKE_ROUTE))

    db = _make_db()
    incident = _seed(db)

    async def run():
        dispatch_dict = ambulance_module.dispatch_incident(incident, db, tick_interval_s=0.005)
        current = asyncio.current_task()
        others = [t for t in asyncio.all_tasks() if t is not current]
        await asyncio.gather(*others)
        return dispatch_dict

    dispatch_dict = asyncio.run(run())

    assert dispatch_dict["ambulance_id"] == "amb_test"
    assert dispatch_dict["hospital_id"] == "hosp_test"

    # ambulance marked BUSY at dispatch time, back to IDLE once ARRIVED
    ambulance = db.get(Ambulance, "amb_test")
    assert ambulance.status == "IDLE"

    position_states = [p["state"] for t, p in recorder.messages if t == "ambulance.position"]
    assert position_states, "expected at least one ambulance.position broadcast"
    assert position_states[0] == "TO_SCENE"
    assert position_states[-1] == "TO_HOSPITAL"
    # every state that appears must be contiguous and in the right order
    seen_order = list(dict.fromkeys(position_states))  # de-dup while preserving order
    assert seen_order == ["TO_SCENE", "TO_HOSPITAL"]

    to_scene_count = position_states.count("TO_SCENE")
    to_hospital_count = position_states.count("TO_HOSPITAL")
    assert to_scene_count >= 1
    assert to_hospital_count >= 1

    hospital_alerts = [p for t, p in recorder.messages if t == "hospital.alert"]
    assert len(hospital_alerts) == 1
    assert hospital_alerts[0]["hospital_id"] == "hosp_test"
    assert hospital_alerts[0]["incident_type"] == "rider_down"

    incident_updates = [p for t, p in recorder.messages if t == "incident.updated"]
    assert incident_updates[-1] == {"id": "inc_test", "status": "RESOLVED"}

    db.refresh(incident)
    assert incident.status == "RESOLVED"

    # eta should be non-increasing within each leg (monotonically decreasing as it approaches)
    to_scene_etas = [p["eta_seconds"] for t, p in recorder.messages if t == "ambulance.position" and p["state"] == "TO_SCENE"]
    assert all(a >= b for a, b in zip(to_scene_etas, to_scene_etas[1:]))

    to_hospital_etas = [p["eta_seconds"] for t, p in recorder.messages if t == "ambulance.position" and p["state"] == "TO_HOSPITAL"]
    assert all(a >= b for a, b in zip(to_hospital_etas, to_hospital_etas[1:]))


def test_dispatch_incident_raises_when_no_idle_ambulances(monkeypatch):
    monkeypatch.setattr(ambulance_module, "get_route", lambda *a, **kw: dict(FAKE_ROUTE))

    db = _make_db()
    incident = _seed(db)
    ambulance = db.get(Ambulance, "amb_test")
    ambulance.status = "BUSY"
    db.commit()

    async def run():
        ambulance_module.dispatch_incident(incident, db, tick_interval_s=0.005)

    try:
        asyncio.run(run())
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "no idle ambulances" in str(exc)
