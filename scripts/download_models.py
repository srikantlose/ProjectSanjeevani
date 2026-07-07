"""Download the pretrained YOLO11 weights used by the detection engine into models/.

Usage:
    venv\\Scripts\\python.exe scripts\\download_models.py
"""

from pathlib import Path

from ultralytics import YOLO

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
WEIGHTS = ["yolo11s.pt", "yolo11s-pose.pt"]


def main() -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    for name in WEIGHTS:
        dest = MODELS_DIR / name
        if dest.exists():
            print(f"already present: {dest}")
            continue
        print(f"downloading {name} -> {dest}")
        YOLO(str(dest))
        if not dest.exists():
            raise RuntimeError(f"expected {dest} to exist after download")
        print(f"done: {dest}")


if __name__ == "__main__":
    main()
