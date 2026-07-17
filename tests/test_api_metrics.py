import json

from services.api.models import EvalRun


def test_metrics_summary_returns_no_runs_when_empty(client):
    response = client.get("/api/metrics/summary")
    assert response.status_code == 200
    assert response.json() == {"status": "no_runs"}


def test_metrics_summary_returns_latest_eval_run(client):
    db = client.test_session_local()
    try:
        db.add(EvalRun(run_at="2026-07-01T00:00:00Z", manifest_path="m1.csv", results_json=json.dumps({"tpr": 0.5})))
        db.add(EvalRun(run_at="2026-07-02T00:00:00Z", manifest_path="m2.csv", results_json=json.dumps({"tpr": 0.9})))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/metrics/summary")
    assert response.status_code == 200
    assert response.json() == {"tpr": 0.9}
