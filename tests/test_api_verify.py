CANDIDATE_PAYLOAD = {
    "id": "inc_20260708101530_003",
    "camera_id": "junction_cam",
    "mode": "city",
    "severity": "HIGH",
    "severity_reasons": ["severity HIGH: rider down (0.95)"],
    "signals": {"collision": 0.2, "rider_down": 0.95, "crowd": 0.8, "flow": 0.4},
    "reasons": ["rider_down: person 2 fell"],
    "location": {"lat": 12.9730, "lon": 77.6194, "label": "Trinity Circle"},
    "evidence": {
        "clip_path": "data/clips/inc_20260708101530_003/evidence.mp4",
        "snapshot_path": "data/clips/inc_20260708101530_003/snapshot.jpg",
    },
    "detected_at": "2026-07-08T10:15:30.100Z",
}


def test_reject_transitions_to_rejected_and_broadcasts(client):
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)

    with client.websocket_connect("/ws") as ws:
        response = client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "reject"})
        assert response.status_code == 200
        assert response.json() == {"id": CANDIDATE_PAYLOAD["id"], "status": "REJECTED"}
        message = ws.receive_json()

    assert message["type"] == "incident.updated"
    assert message["payload"] == {"id": CANDIDATE_PAYLOAD["id"], "status": "REJECTED"}

    detail = client.get(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}")
    assert detail.json()["status"] == "REJECTED"


def test_confirm_transitions_to_dispatched_and_broadcasts_twice(client):
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)

    with client.websocket_connect("/ws") as ws:
        response = client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "confirm"})
        assert response.status_code == 200
        assert response.json() == {"id": CANDIDATE_PAYLOAD["id"], "status": "DISPATCHED"}

        first = ws.receive_json()
        second = ws.receive_json()

    assert first["type"] == "incident.updated"
    assert first["payload"]["status"] == "CONFIRMED"
    assert second["type"] == "incident.updated"
    assert second["payload"]["status"] == "DISPATCHED"

    detail = client.get(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}")
    assert detail.json()["status"] == "DISPATCHED"


def test_dispatch_info_survives_a_rest_reload_after_confirm(client):
    # Regression: GET /api/incidents(/{id}) must include the dispatch object once one
    # exists, not just the one-time WS broadcast at the moment of confirmation --
    # otherwise a client that (re)loads via REST after the fact (e.g. a page refresh
    # mid-demo) has no way to know an ambulance/route/hospital were ever assigned.
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "confirm"})

    detail = client.get(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}").json()
    assert "dispatch" in detail
    dispatch = detail["dispatch"]
    assert dispatch["dispatch_id"]
    assert dispatch["ambulance_id"]
    assert dispatch["hospital_id"]
    assert dispatch["hospital_name"]
    assert isinstance(dispatch["route"], list) and len(dispatch["route"]) > 1

    listing = client.get("/api/incidents").json()
    assert "dispatch" in listing[0]


def test_reverify_after_confirm_returns_409(client):
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "confirm"})

    second = client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "reject"})
    assert second.status_code == 409


def test_verify_missing_incident_returns_404(client):
    response = client.post("/api/incidents/does_not_exist/verify", json={"decision": "confirm"})
    assert response.status_code == 404


def test_verify_invalid_decision_returns_400(client):
    client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
    response = client.post(f"/api/incidents/{CANDIDATE_PAYLOAD['id']}/verify", json={"decision": "maybe"})
    assert response.status_code == 400
