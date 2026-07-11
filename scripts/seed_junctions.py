"""Fetches OSM traffic-signal junction nodes for the green-corridor simulation (plan.md §9.1).

Tries a live Overpass API query first; falls back to a hand-curated list of 20
real Bengaluru junctions if Overpass is unreachable or returns nothing. Either
path writes the same data/seed/junctions.json shape. This is a one-time
build-time data pull -- Overpass is never called at demo runtime.

Usage:
    venv\\Scripts\\python.exe scripts\\seed_junctions.py
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "seed" / "junctions.json"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = (12.88, 77.54, 13.04, 77.66)  # south, west, north, east
MAX_JUNCTIONS = 40

FALLBACK_JUNCTIONS = [
    {"id": "jct_001", "name": "Trinity Circle", "lat": 12.9730, "lon": 77.6194},
    {"id": "jct_002", "name": "Domlur", "lat": 12.9609, "lon": 77.6387},
    {"id": "jct_003", "name": "Ulsoor/Kensington", "lat": 12.9790, "lon": 77.6210},
    {"id": "jct_004", "name": "Richmond Circle", "lat": 12.9611, "lon": 77.5950},
    {"id": "jct_005", "name": "Hudson Circle", "lat": 12.9660, "lon": 77.5880},
    {"id": "jct_006", "name": "Town Hall", "lat": 12.9645, "lon": 77.5855},
    {"id": "jct_007", "name": "Mysore Bank Circle", "lat": 12.9689, "lon": 77.5800},
    {"id": "jct_008", "name": "Anil Kumble Circle", "lat": 12.9757, "lon": 77.6070},
    {"id": "jct_009", "name": "Cubbon Park/Minsk Sq", "lat": 12.9800, "lon": 77.5970},
    {"id": "jct_010", "name": "Chalukya Circle", "lat": 12.9846, "lon": 77.5900},
    {"id": "jct_011", "name": "Windsor Manor", "lat": 12.9910, "lon": 77.5860},
    {"id": "jct_012", "name": "Mekhri Circle", "lat": 13.0060, "lon": 77.5760},
    {"id": "jct_013", "name": "Sanjaynagar", "lat": 13.0230, "lon": 77.5700},
    {"id": "jct_014", "name": "Hebbal", "lat": 13.0358, "lon": 77.5920},
    {"id": "jct_015", "name": "Cauvery Junction", "lat": 13.0130, "lon": 77.5800},
    {"id": "jct_016", "name": "Shivananda Circle", "lat": 12.9855, "lon": 77.5790},
    {"id": "jct_017", "name": "Majestic/KBS", "lat": 12.9767, "lon": 77.5710},
    {"id": "jct_018", "name": "Corporation Circle", "lat": 12.9645, "lon": 77.5900},
    {"id": "jct_019", "name": "Residency-Brigade", "lat": 12.9720, "lon": 77.6070},
    {"id": "jct_020", "name": "MG-Brigade", "lat": 12.9752, "lon": 77.6060},
]


def fetch_from_overpass() -> list[dict] | None:
    south, west, north, east = BBOX
    query = f"""
    [out:json][timeout:60];
    node["highway"="traffic_signals"]({south},{west},{north},{east});
    out;
    """
    headers = {"Accept": "application/json", "User-Agent": "SanjeevaniDemo/1.0 (academic project)"}
    try:
        response = httpx.post(OVERPASS_URL, data={"data": query}, headers=headers, timeout=65.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Overpass query failed ({exc}); falling back to curated junction list.")
        return None

    elements = response.json().get("elements", [])
    if not elements:
        print("Overpass returned no elements; falling back to curated junction list.")
        return None

    step = max(1, len(elements) // MAX_JUNCTIONS)
    sampled = elements[::step][:MAX_JUNCTIONS]

    junctions = []
    for i, el in enumerate(sampled, start=1):
        name = el.get("tags", {}).get("name") or f"Signal jct_{i:03d}"
        junctions.append({"id": f"jct_{i:03d}", "name": name, "lat": el["lat"], "lon": el["lon"]})
    return junctions


def main() -> None:
    junctions = fetch_from_overpass() or FALLBACK_JUNCTIONS
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(junctions, f, indent=2)
    print(f"wrote {len(junctions)} junctions to {OUT_PATH}")


if __name__ == "__main__":
    main()
