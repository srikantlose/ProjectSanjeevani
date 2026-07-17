def test_list_junctions_returns_seeded_rows(client):
    response = client.get("/api/junctions")
    assert response.status_code == 200

    rows = response.json()
    assert len(rows) > 0
    for row in rows:
        assert set(row.keys()) == {"id", "name", "lat", "lon"}
        assert isinstance(row["lat"], float)
        assert isinstance(row["lon"], float)
