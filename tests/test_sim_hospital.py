from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.db import Base
from services.api.models import Hospital, Incident
from services.api.sim.hospital import determine_incident_type, select_hospital

INCIDENT_LAT, INCIDENT_LON = 12.9700, 77.6000

# Small-angle offsets north of the incident, ~1000m / ~1400m / ~5000m respectively.
NEAR_L2_LAT = INCIDENT_LAT + 1000 / 111320  # nearest overall, but trauma_level 2
NEAR_L1_LAT = INCIDENT_LAT + 1400 / 111320  # within 1.5x of the nearest (1500m bound), trauma_level 1
FAR_L1_LAT = INCIDENT_LAT + 5000 / 111320  # trauma_level 1 but far outside the preference bound


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_hospitals(db):
    db.add_all(
        [
            Hospital(id="near_l2", name="Near L2", lat=NEAR_L2_LAT, lon=INCIDENT_LON, trauma_level=2),
            Hospital(id="near_l1", name="Near L1", lat=NEAR_L1_LAT, lon=INCIDENT_LON, trauma_level=1),
            Hospital(id="far_l1", name="Far L1", lat=FAR_L1_LAT, lon=INCIDENT_LON, trauma_level=1),
        ]
    )
    db.commit()


def _make_incident(severity):
    return Incident(
        id="inc_test",
        camera_id="cam1",
        mode="city",
        status="CONFIRMED",
        severity=severity,
        severity_reasons="[]",
        signals="{}",
        reasons="[]",
        lat=INCIDENT_LAT,
        lon=INCIDENT_LON,
        location_label="Test Location",
        detected_at="2026-01-01T00:00:00.000Z",
    )


def test_high_severity_prefers_trauma_l1_within_bound():
    db = _make_db()
    _seed_hospitals(db)
    incident = _make_incident("HIGH")

    chosen = select_hospital(incident, db)

    assert chosen.id == "near_l1"


def test_medium_severity_picks_absolute_nearest_regardless_of_trauma_level():
    db = _make_db()
    _seed_hospitals(db)
    incident = _make_incident("MEDIUM")

    chosen = select_hospital(incident, db)

    assert chosen.id == "near_l2"


def test_high_severity_falls_back_to_nearest_when_no_l1_within_bound():
    db = _make_db()
    db.add_all(
        [
            Hospital(id="near_l2", name="Near L2", lat=NEAR_L2_LAT, lon=INCIDENT_LON, trauma_level=2),
            Hospital(id="far_l1", name="Far L1", lat=FAR_L1_LAT, lon=INCIDENT_LON, trauma_level=1),
        ]
    )
    db.commit()
    incident = _make_incident("HIGH")

    chosen = select_hospital(incident, db)

    assert chosen.id == "near_l2"  # far_l1 is outside the 1.5x preference bound


def test_determine_incident_type_rider_down():
    assert determine_incident_type({"rider_down": 0.9, "collision": 0.1}) == "rider_down"


def test_determine_incident_type_collision():
    assert determine_incident_type({"rider_down": 0.5, "collision": 0.7}) == "collision"


def test_determine_incident_type_stationary():
    assert determine_incident_type({"collision": 0.3, "stationary": 0.9}) == "stationary_vehicle"


def test_determine_incident_type_unspecified():
    assert determine_incident_type({"collision": 0.1, "flow": 0.2}) == "unspecified"
