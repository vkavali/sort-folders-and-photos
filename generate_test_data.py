"""Generate a deliberately messy nested media tree for self-verification.

The layout mirrors what a real wedding export looks like (multiple
top-level timestamped containers, each holding the same named event
subfolders). Uses tiny 2x2 PNGs so EXIF-less branches exercise the
mtime fallback and hash-dedup logic.

Run:
    python generate_test_data.py [--root _test_tree]
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import struct
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image


def _jpeg_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (2, 2), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (2, 2), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _fake_mp4_bytes(marker: bytes) -> bytes:
    ftyp = (
        struct.pack(">I", 20)
        + b"ftyp"
        + b"isom"
        + struct.pack(">I", 512)
        + b"isomiso2mp41"
    )
    return ftyp + b"\x00" * 16 + marker


def _write(path: Path, data: bytes, mtime: datetime | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mtime is not None:
        ts = mtime.timestamp()
        os.utime(path, (ts, ts))


def build_tree(root: Path) -> None:
    source = root / "source"
    destination = root / "destination"
    if root.exists():
        shutil.rmtree(root)
    source.mkdir(parents=True)
    destination.mkdir(parents=True)

    base_time = datetime(2024, 6, 1, 9, 0, 0)

    # Distinct-content photos
    haldi_1 = _jpeg_bytes((230, 200, 40))
    haldi_2 = _jpeg_bytes((200, 180, 20))
    sangeet_1 = _jpeg_bytes((30, 30, 200))
    sangeet_2 = _jpeg_bytes((10, 10, 180))
    reception_1 = _jpeg_bytes((200, 200, 200))
    reception_dup = _jpeg_bytes((200, 200, 200))  # note: same bytes as reception_1
    other_png = _png_bytes((120, 120, 120))
    other_mp4 = _fake_mp4_bytes(b"CLIP1")

    # --- Google-Drive-export-looking timestamped top-level folders,
    # each with the SAME named subfolders we want to merge across them. ---
    #
    # Day 1 batch
    _write(
        source / "Marriage-20260111T075732Z-3-001" / "Marriage" / "HALDI&SANGEETH"
        / "PICS" / "IMG_0001.JPG",
        haldi_1,
        base_time,
    )
    _write(
        source / "Marriage-20260111T075732Z-3-001" / "Marriage" / "Marriage Selected"
        / "DSC_9000.JPG",
        reception_1,
        base_time + timedelta(minutes=30),
    )

    # Day 2 batch — same named subfolders, different content, plus a duplicate
    _write(
        source / "Marriage-20260111T075732Z-3-002" / "Marriage" / "HALDI&SANGEETH"
        / "PICS" / "IMG_0002.JPG",
        haldi_2,
        base_time + timedelta(hours=1),
    )
    _write(
        source / "Marriage-20260111T075732Z-3-002" / "Marriage" / "HALDI&SANGEETH"
        / "PICS" / "IMG_SANGEET_1.JPG",
        sangeet_1,
        base_time + timedelta(hours=8),   # evening = Sangeet
    )
    _write(
        source / "Marriage-20260111T075732Z-3-002" / "Marriage" / "HALDI&SANGEETH"
        / "PICS" / "IMG_SANGEET_2.JPG",
        sangeet_2,
        base_time + timedelta(hours=9),   # evening = Sangeet
    )
    _write(
        source / "Marriage-20260111T075732Z-3-002" / "Marriage" / "Marriage Selected"
        / "DSC_9000.JPG",
        reception_dup,    # EXACT duplicate of Day-1 reception_1
        base_time + timedelta(hours=25),
    )
    _write(
        source / "Marriage-20260111T075732Z-3-002" / "Marriage" / "Marriage Selected"
        / "DSC_9001.JPG",
        _jpeg_bytes((220, 220, 220)),
        base_time + timedelta(hours=26),
    )

    # A non-Marriage branch to test ignored / Unsorted paths
    _write(source / "unrelated_notes" / "notes.png", other_png, base_time)
    _write(source / "videos" / "clip1.mp4", other_mp4, base_time + timedelta(hours=3))

    print(f"Built test tree at {root.resolve()}")
    print(f"  source:      {source}")
    print(f"  destination: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="_test_tree", type=Path)
    args = parser.parse_args()
    build_tree(args.root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
