"""Normalizes raw downloaded footage into a consistent encode for the eval manifest
(plan.md §6.3, E8-T1): 1280x720, 25fps, H.264 crf 23, faststart, named
`{source}_{index:04d}.mp4`, written to data/processed/.

Usage:
    venv\\Scripts\\python.exe scripts\\make_clips.py --src data/raw/cadp --out data/processed
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def normalize_clip(ffmpeg_path: str, src: Path, dst: Path) -> None:
    subprocess.run(
        [
            ffmpeg_path, "-y", "-i", str(src),
            "-vf", "scale=1280:720",
            "-r", "25",
            "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(dst),
        ],
        check=True,
        capture_output=True,
    )


def normalize_directory(src_dir: Path, out_dir: Path) -> list[Path]:
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg not found on PATH -- install it first (winget install Gyan.FFmpeg)")

    if not src_dir.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {src_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    source_name = src_dir.name
    clips = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)

    written = []
    for index, clip in enumerate(clips, start=1):
        dst = out_dir / f"{source_name}_{index:04d}.mp4"
        normalize_clip(ffmpeg_path, clip, dst)
        written.append(dst)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--src", required=True, help="directory of raw downloaded clips (data/raw/<source>)")
    parser.add_argument("--out", default="data/processed", help="output directory for normalized clips")
    args = parser.parse_args()

    written = normalize_directory(Path(args.src), Path(args.out))
    if not written:
        print(f"no video files found in {args.src}")
        return

    for dst in written:
        print(f"wrote {dst}")
    print(f"normalized {len(written)} clip(s) from {args.src} into {args.out}")


if __name__ == "__main__":
    main()
