"""Idempotent seed-data loader for ambulances/hospitals/junctions (plan.md §8.1).

Missing seed files (i.e. before E6-T1 creates them) log a warning and are
skipped rather than raising, so E5 can be built and run standalone.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from services.api.models import Ambulance, CorridorJunction, Hospital

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "seed"


def _load_json(name: str) -> list[dict] | None:
    path = SEED_DIR / name
    if not path.exists():
        print(f"WARNING: seed file not found: {path} -- skipping (expected until E6-T1 lands)")
        return None
    with open(path) as f:
        return json.load(f)


def load_seed_data(db: Session) -> None:
    if db.query(Hospital).count() == 0:
        rows = _load_json("hospitals.json")
        if rows:
            for row in rows:
                db.add(
                    Hospital(id=row["id"], name=row["name"], lat=row["lat"], lon=row["lon"], trauma_level=row["trauma_level"])
                )

    if db.query(Ambulance).count() == 0:
        rows = _load_json("ambulances.json")
        if rows:
            for row in rows:
                db.add(
                    Ambulance(
                        id=row["id"],
                        name=row["name"],
                        home_lat=row["home_lat"],
                        home_lon=row["home_lon"],
                        status="IDLE",
                        current_lat=row["home_lat"],
                        current_lon=row["home_lon"],
                    )
                )

    if db.query(CorridorJunction).count() == 0:
        rows = _load_json("junctions.json")
        if rows:
            for row in rows:
                db.add(CorridorJunction(id=row["id"], name=row["name"], lat=row["lat"], lon=row["lon"]))

    db.commit()
