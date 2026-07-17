from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from services.api.db import get_db
from services.api.models import CorridorJunction

router = APIRouter()


@router.get("/api/junctions")
def list_junctions(db: Session = Depends(get_db)):
    rows = db.query(CorridorJunction).all()
    return [{"id": r.id, "name": r.name, "lat": r.lat, "lon": r.lon} for r in rows]
