"""Prefetches and commits GeoJSON routes for every demo pair (plan.md §9.2, E6-T2).

26 pairs total: 5 ambulance homes -> 2 scenario locations (10), plus 2 scenario
locations -> 8 hospitals (16). Re-runnable: skips pairs whose cache file
already exists. This is the offline fallback the routing client falls back to
if the public OSRM server is unreachable during the demo.

Usage:
    venv\\Scripts\\python.exe scripts\\prefetch_routes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.api.sim.routing import ROUTES_DIR, SCENARIO_LOCATIONS, _fetch_from_osrm, _load_seed_points  # noqa: E402


def main() -> None:
    ambulances = _load_seed_points("ambulances.json", "id", "home_lat", "home_lon")
    hospitals = _load_seed_points("hospitals.json", "id", "lat", "lon")

    pairs = []
    for amb_id, (alat, alon) in ambulances.items():
        for scene_id, (slat, slon) in SCENARIO_LOCATIONS.items():
            pairs.append((amb_id, alat, alon, scene_id, slat, slon))
    for scene_id, (slat, slon) in SCENARIO_LOCATIONS.items():
        for hosp_id, (hlat, hlon) in hospitals.items():
            pairs.append((scene_id, slat, slon, hosp_id, hlat, hlon))

    ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for from_id, flat, flon, to_id, tlat, tlon in pairs:
        out_path = ROUTES_DIR / f"{from_id}__{to_id}.geojson"
        if out_path.exists():
            results.append((from_id, to_id, "skipped (exists)"))
            continue
        try:
            route = _fetch_from_osrm(flat, flon, tlat, tlon)
        except Exception as exc:
            results.append((from_id, to_id, f"FAILED: {exc}"))
            continue
        with open(out_path, "w") as f:
            json.dump(route, f)
        results.append((from_id, to_id, f"ok ({route['distance_m']:.0f}m)"))

    print(f"{'from':<24} {'to':<28} status")
    for from_id, to_id, status in results:
        print(f"{from_id:<24} {to_id:<28} {status}")

    n_ok = sum(1 for _, _, s in results if s.startswith("ok") or s.startswith("skipped"))
    print(f"\n{n_ok}/{len(results)} routes available")


if __name__ == "__main__":
    main()
