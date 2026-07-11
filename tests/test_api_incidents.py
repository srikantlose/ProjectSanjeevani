from services.api.models import IncidentSignal

CANDIDATE_PAYLOAD = {
    "id": "inc_20260708101530_001",
    "camera_id": "junction_cam",
    "mode": "city",
    "severity": "HIGH",
    "severity_reasons": ["severity HIGH: rider down (0.95)"],
    "signals": {"collision": 0.2, "rider_down": 0.95, "crowd": 0.8, "flow": 0.4},
    "reasons": [
        "rider_down: person 2 aspect 3.20 sustained 2.4s, near vehicle 1 impact signature at t=8.1s",
        "crowd: cluster grew by 5 members within 8s",
    ],
    "location": {"lat": 12.9730, "lon": 77.6194, "label": "Trinity Circle"},
    "evidence": {
        "clip_path": "data/clips/inc_20260708101530_001/evidence.mp4",
        "snapshot_path": "data/clips/inc_20260708101530_001/snapshot.jpg",
    },
    "detected_at": "2026-07-08T10:15:30.100Z",
}


def test_post_candidate_persists_and_creates_signal_rows(client):
    response = client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    assert response.status_code == 201
    assert response.json() == {"id": CANDIDATE_PAYLOAD["id"]}

    detail = client.get(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "PENDING_VERIFICATION"
    assert body["severity"] == "HIGH"
    assert body["signals"] == CANDIDATE_PAYLOAD["signals"]
    assert body["reasons"] == CANDIDATE_PAYLOAD["reasons"]
    assert body["location"] == CANDIDATE_PAYLOAD["location"]
    assert body["evidence"]["clip_url"] == f"/media/{CANDIDATE_PAYLOAD['id']}/evidence.mp4"
    assert body["evidence"]["snapshot_url"] == f"/media/{CANDIDATE_PAYLOAD['id']}/snapshot.jpg"

    db = client.test_session_local()
    try:
        signal_rows = db.query(IncidentSignal).filter_by(incident_id=CANDIDATE_PAYLOAD["id"]).all()
        assert {(r.signal_name, r.score) for r in signal_rows} == {
            (name, score) for name, score in CANDIDATE_PAYLOAD["signals"].items()
        }
    finally:
        db.close()


def test_duplicate_candidate_id_returns_409(client):
    first = client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    assert first.status_code == 201

    second = client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    assert second.status_code == 409


def test_list_incidents_returns_posted_candidate(client):
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)

    listing = client.get("/api/incidents")
    assert listing.status_code == 200
    body = listing.json()
    assert len(body) == 1
    assert body[0]["id"] == CANDIDATE_PAYLOAD["id"]


def test_get_missing_incident_returns_404(client):
    response = client.get("/api/incidents/does_not_exist")
    assert response.status_code == 404
