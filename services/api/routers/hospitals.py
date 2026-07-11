from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import Hospital

router = APIRouter()


@router.get("/api/hospitals")
def list_hospitals(db: Session = Depends(get_db)):
    rows = db.query(Hospital).all()
    return [
        {"id": r.id, "name": r.name, "lat": r.lat, "lon": r.lon, "trauma_level": r.trauma_level} for r in rows
    ]
