"""Routing client: live OSRM with a committed-GeoJSON fallback (plan.md §9.2).

`get_route` takes raw lat/lon (matching plan.md's literal signature) and, on
live-routing failure, matches the endpoints against a registry of known named
points (ambulance homes, hospitals, demo scenario locations) by rounding to
4 decimal places, then looks up the cached `{from_id}__{to_id}.geojson` file.
Route coordinates are GeoJSON order: [lon, lat].
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

OSRM_BASE_URL = "https://router.project-osrm.org"
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
ROUTES_DIR = DATA_DIR / "routes"

# Fixed demo incident locations (plan.md §9.1) -- part of the known-points registry
# alongside the seeded ambulances/hospitals so cache lookups can resolve an id
# from raw coordinates.
SCENARIO_LOCATIONS: dict[str, tuple[float, float]] = {
    "scenario1_trinity_circle": (12.9730, 77.6194),
    "scenario2_hebbal": (13.0358, 77.5970),
}


def _load_seed_points(filename: str, id_field: str, lat_field: str, lon_field: str) -> dict[str, tuple[float, float]]:
    path = DATA_DIR / "seed" / filename
    if not path.exists():
        return {}
    with open(path) as f:
        rows = json.load(f)
    return {row[id_field]: (row[lat_field], row[lon_field]) for row in rows}


def known_points() -> dict[str, tuple[float, float]]:
    points: dict[str, tuple[float, float]] = dict(SCENARIO_LOCATIONS)
    points.update(_load_seed_points("hospitals.json", "id", "lat", "lon"))
    points.update(_load_seed_points("ambulances.json", "id", "home_lat", "home_lon"))
    return points


def _round4(lat: float, lon: float) -> tuple[float, float]:
    return (round(lat, 4), round(lon, 4))


def _match_ids(lat: float, lon: float) -> list[str]:
    """Returns every known point id whose coordinates round-match (lat, lon).
    Multiple named points can share identical coordinates by design (e.g. an
    ambulance staged at its home hospital), so this can't assume a single
    match -- the caller must try all candidates."""
    target = _round4(lat, lon)
    return [point_id for point_id, (plat, plon) in known_points().items() if _round4(plat, plon) == target]


def _load_cached_route(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict | None:
    from_ids = _match_ids(from_lat, from_lon)
    to_ids = _match_ids(to_lat, to_lon)
    for from_id in from_ids:
        for to_id in to_ids:
            path = ROUTES_DIR / f"{from_id}__{to_id}.geojson"
            if path.exists():
                with open(path) as f:
                    return json.load(f)
    return None


def _fetch_from_osrm(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict:
    url = f"{OSRM_BASE_URL}/route/v1/driving/{from_lon},{from_lat};{to_lon},{to_lat}"
    response = httpx.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=2.0)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM returned no route: {data.get('code')}")
    route = data["routes"][0]
    return {"coordinates": route["geometry"]["coordinates"], "distance_m": route["distance"]}


def get_route(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> dict:
    """Returns {"coordinates": [[lon, lat], ...], "distance_m": float}.
    Tries live OSRM first (2s timeout); falls back to a committed cache file
    matched by rounding coordinates against the known-points registry."""
    try:
        return _fetch_from_osrm(from_lat, from_lon, to_lat, to_lon)
    except (httpx.HTTPError, RuntimeError):
        pass

    cached = _load_cached_route(from_lat, from_lon, to_lat, to_lon)
    if cached is not None:
        return cached

    raise RuntimeError(
        f"no route available: live OSRM failed and no cached route matches "
        f"({from_lat},{from_lon}) -> ({to_lat},{to_lon})"
    )
