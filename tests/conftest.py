"""Shared pytest fixtures.

`vtest_video` provides a small real clip (pedestrians/cars) for tests that need
actual detectable content — synthetic solid-color frames don't produce real
YOLO detections. This is a standard OpenCV test asset (BSD-licensed), used only
as dev/test infrastructure — it is not part of the project's actual dataset
(see plan.md §6), which is acquired separately in epic E8.
"""

import urllib.request
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
VTEST_URL = "https://github.com/opencv/opencv/raw/master/samples/data/vtest.avi"
VTEST_PATH = FIXTURES_DIR / "vtest.avi"


@pytest.fixture(scope="session")
def vtest_video() -> Path:
    FIXTURES_DIR.mkdir(exist_ok=True)
    if not VTEST_PATH.exists():
        urllib.request.urlretrieve(VTEST_URL, VTEST_PATH)
    return VTEST_PATH
