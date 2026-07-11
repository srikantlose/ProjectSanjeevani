CANDIDATE_PAYLOAD = {
    "id": "inc_20260708101530_002",
    "camera_id": "junction_cam",
    "mode": "city",
    "severity": "HIGH",
    "severity_reasons": ["severity HIGH: rider down (0.95)"],
    "signals": {"collision": 0.2, "rider_down": 0.95, "crowd": 0.8, "flow": 0.4},
    "reasons": ["rider_down: person 2 fell"],
    "location": {"lat": 12.9730, "lon": 77.6194, "label": "Trinity Circle"},
    "evidence": {
        "clip_path": "data/clips/inc_20260708101530_002/evidence.mp4",
        "snapshot_path": "data/clips/inc_20260708101530_002/snapshot.jpg",
    },
    "detected_at": "2026-07-08T10:15:30.100Z",
}


def test_post_candidate_broadcasts_incident_new(client):
    with client.websocket_connect("/ws") as websocket:
        response = client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
        assert response.status_code == 201

        message = websocket.receive_json()

    assert message["type"] == "incident.new"
    assert message["ts"].endswith("Z")

    payload = message["payload"]
    assert payload["id"] == CANDIDATE_PAYLOAD["id"]
    assert payload["status"] == "PENDING_VERIFICATION"
    assert payload["signals"] == CANDIDATE_PAYLOAD["signals"]
    assert payload["evidence"]["clip_url"] == f"/media/{CANDIDATE_PAYLOAD['id']}/evidence.mp4"
    assert payload["evidence"]["snapshot_url"] == f"/media/{CANDIDATE_PAYLOAD['id']}/snapshot.jpg"


def test_connection_survives_after_disconnect(client):
    # A stale/disconnected socket must not break broadcasting to a later, still-open one.
    with client.websocket_connect("/ws") as first:
        pass  # closes immediately on exiting the `with` block

    with client.websocket_connect("/ws") as second:
        response = client.post("/api/incidents/candidate", json=CANDIDATE_PAYLOAD)
        assert response.status_code == 201
        message = second.receive_json()
        assert message["type"] == "incident.new"
