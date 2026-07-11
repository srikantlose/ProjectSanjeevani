from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import Ambulance

router = APIRouter()


@router.get("/api/ambulances")
def list_ambulances(db: Session = Depends(get_db)):
    rows = db.query(Ambulance).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "home_lat": r.home_lat,
            "home_lon": r.home_lon,
            "status": r.status,
            "current_lat": r.current_lat,
            "current_lon": r.current_lon,
        }
        for r in rows
    ]
