"""Geo helpers for the simulation layer (plan.md §9.2).

Route coordinates are GeoJSON order: [lon, lat] pairs, not [lat, lon] -- careful.
"""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6371000.0

Coord = tuple[float, float]  # (lon, lat)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def polyline_cumdist(coords: list[Coord]) -> list[float]:
    """Returns cumulative distance in meters at each vertex, starting at 0."""
    cum = [0.0]
    for i in range(1, len(coords)):
        lon1, lat1 = coords[i - 1]
        lon2, lat2 = coords[i]
        cum.append(cum[-1] + haversine_m(lat1, lon1, lat2, lon2))
    return cum


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def point_at_distance(coords: list[Coord], cumdist: list[float], d: float) -> tuple[float, float, float]:
    """Returns (lat, lon, heading_deg) at route-distance `d` along `coords`,
    via linear interpolation within the enclosing segment."""
    if d <= 0:
        lon, lat = coords[0]
        heading = _bearing_deg(coords[0][1], coords[0][0], coords[1][1], coords[1][0]) if len(coords) > 1 else 0.0
        return lat, lon, heading
    if d >= cumdist[-1]:
        lon, lat = coords[-1]
        heading = _bearing_deg(coords[-2][1], coords[-2][0], coords[-1][1], coords[-1][0]) if len(coords) > 1 else 0.0
        return lat, lon, heading

    for i in range(len(cumdist) - 1):
        if cumdist[i] <= d <= cumdist[i + 1]:
            seg_len = cumdist[i + 1] - cumdist[i]
            frac = 0.0 if seg_len == 0 else (d - cumdist[i]) / seg_len
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            lat = lat1 + frac * (lat2 - lat1)
            lon = lon1 + frac * (lon2 - lon1)
            heading = _bearing_deg(lat1, lon1, lat2, lon2)
            return lat, lon, heading

    lon, lat = coords[-1]
    return lat, lon, 0.0


def project_distance(coords: list[Coord], cumdist: list[float], lat: float, lon: float) -> tuple[float, float]:
    """Nearest-vertex approximation: returns (route_dist_m, offset_m) where
    route_dist_m is the matched vertex's cumulative distance and offset_m is
    the distance from (lat, lon) to that vertex."""
    best_i = 0
    best_dist = float("inf")
    for i, (vlon, vlat) in enumerate(coords):
        dist = haversine_m(lat, lon, vlat, vlon)
        if dist < best_dist:
            best_dist = dist
            best_i = i
    return cumdist[best_i], best_dist
