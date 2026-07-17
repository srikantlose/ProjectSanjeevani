"""Metrics summary endpoint (plan.md §11, wired now in E7-T7; real content lands in E9-T2)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import EvalRun

router = APIRouter()


@router.get("/api/metrics/summary")
def get_metrics_summary(db: Session = Depends(get_db)):
    latest = db.query(EvalRun).order_by(EvalRun.run_at.desc()).first()
    if latest is None:
        return {"status": "no_runs"}
    return json.loads(latest.results_json)
