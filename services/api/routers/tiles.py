"""Cache-through OSM tile proxy (plan.md §4, §8.1).

The browser never hits OpenStreetMap directly -- every tile the demo touches
gets fetched once (with the required User-Agent header) and cached forever,
so a rehearsal run makes the whole demo tile set network-independent.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Response

USER_AGENT = "SanjeevaniDemo/1.0 (academic project)"

router = APIRouter()


def _cache_root() -> Path:
    return Path(os.environ.get("SANJEEVANI_TILE_CACHE_DIR", "data/tile_cache"))


async def _fetch_upstream(z: int, x: int, y: int) -> bytes:
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(url, headers={"User-Agent": USER_AGENT}, timeout=5.0)
        response.raise_for_status()
        return response.content


@router.get("/tiles/{z}/{x}/{y}.png")
async def get_tile(z: int, x: int, y: int):
    cache_path = _cache_root() / str(z) / str(x) / f"{y}.png"
    if cache_path.exists():
        return Response(content=cache_path.read_bytes(), media_type="image/png")

    try:
        content = await _fetch_upstream(z, x, y)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="upstream tile fetch failed") from None

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(content)

    return Response(content=content, media_type="image/png")
