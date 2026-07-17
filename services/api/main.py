"""FastAPI app entrypoint (plan.md §8.1)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from services.api import models  # noqa: F401 -- registers ORM models on Base before create_all
from services.api.db import Base, SessionLocal, engine
from services.api.routers import ambulances, hospitals, incidents, junctions, metrics, tiles
from services.api.seed import load_seed_data
from services.api.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        load_seed_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Project Sanjeevani API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hospitals.router)
app.include_router(ambulances.router)
app.include_router(incidents.router)
app.include_router(junctions.router)
app.include_router(metrics.router)
app.include_router(ws_router)
app.include_router(tiles.router)

Path("data/clips").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory="data/clips"), name="media")
app.mount("/scenario_media", StaticFiles(directory="data/processed"), name="scenario_media")
