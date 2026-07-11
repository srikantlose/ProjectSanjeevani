import math

from services.api.sim.geo import haversine_m, point_at_distance, polyline_cumdist, project_distance


def test_haversine_matches_known_value():
    # 1 degree of latitude along a meridian is a known great-circle distance
    # on the sphere haversine assumes: R * radians(1).
    expected = 6371000.0 * math.radians(1.0)
    actual = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert abs(actual - expected) / expected < 0.01


def test_haversine_zero_distance_for_identical_points():
    assert haversine_m(12.97, 77.59, 12.97, 77.59) == 0.0


def test_point_at_distance_on_two_segment_line():
    # Straight line due north at lon=0, two equal-length segments.
    coords = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
    cumdist = polyline_cumdist(coords)
    assert len(cumdist) == 3
    assert cumdist[0] == 0.0
    # both segments should be (almost) equal length along a meridian
    assert abs((cumdist[1] - cumdist[0]) - (cumdist[2] - cumdist[1])) < 1.0

    midpoint_d = cumdist[1] / 2
    lat, lon, heading = point_at_distance(coords, cumdist, midpoint_d)
    assert abs(lat - 0.5) < 1e-6
    assert abs(lon - 0.0) < 1e-6
    assert abs(heading - 0.0) < 1.0  # heading due north

    # distance beyond the end clamps to the last vertex
    lat_end, lon_end, _ = point_at_distance(coords, cumdist, cumdist[-1] + 1000)
    assert abs(lat_end - 2.0) < 1e-6
    assert abs(lon_end - 0.0) < 1e-6

    # distance before the start clamps to the first vertex
    lat_start, lon_start, _ = point_at_distance(coords, cumdist, -100)
    assert abs(lat_start - 0.0) < 1e-6


def test_project_distance_matches_nearest_vertex():
    coords = [(0.0, 0.0), (0.0, 1.0), (0.0, 2.0)]
    cumdist = polyline_cumdist(coords)

    route_dist, offset_m = project_distance(coords, cumdist, lat=1.0, lon=0.0)
    assert route_dist == cumdist[1]
    assert offset_m < 1.0  # essentially on top of the middle vertex

    route_dist_near_start, offset_near_start = project_distance(coords, cumdist, lat=0.01, lon=0.0)
    assert route_dist_near_start == cumdist[0]
