import httpx

import services.api.routers.tiles as tiles_module


def test_tile_cache_through_and_hit_on_second_request(client, tmp_path, monkeypatch):
    monkeypatch.setattr(tiles_module, "_cache_root", lambda: tmp_path)

    call_count = {"n": 0}

    async def fake_fetch(z, x, y):
        call_count["n"] += 1
        return b"fake-png-bytes"

    monkeypatch.setattr(tiles_module, "_fetch_upstream", fake_fetch)

    first = client.get("/tiles/1/2/3.png")
    assert first.status_code == 200
    assert first.content == b"fake-png-bytes"
    assert call_count["n"] == 1

    cached_file = tmp_path / "1" / "2" / "3.png"
    assert cached_file.exists()
    assert cached_file.read_bytes() == b"fake-png-bytes"

    async def failing_fetch(z, x, y):
        raise AssertionError("upstream should not be called on a cache hit")

    monkeypatch.setattr(tiles_module, "_fetch_upstream", failing_fetch)

    second = client.get("/tiles/1/2/3.png")
    assert second.status_code == 200
    assert second.content == b"fake-png-bytes"
    assert call_count["n"] == 1  # unchanged -- served from cache, upstream never called


def test_tile_upstream_failure_returns_502(client, tmp_path, monkeypatch):
    monkeypatch.setattr(tiles_module, "_cache_root", lambda: tmp_path)

    async def failing_fetch(z, x, y):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(tiles_module, "_fetch_upstream", failing_fetch)

    response = client.get("/tiles/9/9/9.png")
    assert response.status_code == 502


def test_media_static_mount_serves_files(client):
    from pathlib import Path

    clips_dir = Path("data/clips/test_static_mount_check")
    clips_dir.mkdir(parents=True, exist_ok=True)
    test_file = clips_dir / "hello.txt"
    test_file.write_text("hello from evidence clip dir")
    try:
        response = client.get("/media/test_static_mount_check/hello.txt")
        assert response.status_code == 200
        assert response.text == "hello from evidence clip dir"
    finally:
        test_file.unlink()
        clips_dir.rmdir()
