import httpx
import pytest

from services.api.sim import routing


def test_get_route_live_osrm_returns_polyline():
    amb_lat, amb_lon = routing.known_points()["amb_01"]
    scene_lat, scene_lon = routing.SCENARIO_LOCATIONS["scenario1_trinity_circle"]

    route = routing.get_route(amb_lat, amb_lon, scene_lat, scene_lon)

    assert route["distance_m"] > 0
    assert len(route["coordinates"]) > 1


def test_get_route_falls_back_to_cache_when_osrm_unreachable(monkeypatch):
    def broken_fetch(*args, **kwargs):
        raise httpx.ConnectError("simulated OSRM outage")

    monkeypatch.setattr(routing, "_fetch_from_osrm", broken_fetch)

    amb_lat, amb_lon = routing.known_points()["amb_01"]
    scene_lat, scene_lon = routing.SCENARIO_LOCATIONS["scenario1_trinity_circle"]

    route = routing.get_route(amb_lat, amb_lon, scene_lat, scene_lon)

    assert route["distance_m"] > 0
    assert len(route["coordinates"]) > 1


def test_get_route_raises_when_osrm_down_and_no_cache_match(monkeypatch):
    def broken_fetch(*args, **kwargs):
        raise httpx.ConnectError("simulated OSRM outage")

    monkeypatch.setattr(routing, "_fetch_from_osrm", broken_fetch)

    with pytest.raises(RuntimeError):
        routing.get_route(0.0, 0.0, 1.0, 1.0)  # nowhere near any known point
