"""Generate a deliberately messy, taxonomy-agnostic test tree for self-verification.

Run from the repository root:
    python3 generate_test_data.py [--root PATH]

Creates:
  <root>/source/        — messy nested tree to be processed.
  <root>/destination/   — empty target folder for the app to write into.

The produced images are real JPEGs (2×2 pixels) so that EXIF extraction can
succeed where EXIF is present and fall back to mtime otherwise. Duplicate
files share byte-for-byte content; collision files share a filename but have
different bytes.
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
    # Minimal ISO-BMFF header so extension sniffing is harmless; content is
    # irrelevant to our tool, which treats mp4 as "no EXIF → use mtime".
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

    jpg_alpha1 = _jpeg_bytes((230, 40, 40))
    jpg_alpha2 = _jpeg_bytes((40, 200, 40))
    jpg_alpha3 = _jpeg_bytes((40, 40, 230))
    jpg_bravo = _jpeg_bytes((200, 200, 0))
    jpg_bravo_extra = _jpeg_bytes((0, 200, 200))
    png_note = _png_bytes((120, 120, 120))
    mp4_clip = _fake_mp4_bytes(b"CLIP1")

    # alpha_raw + "Alpha Raw" + "Alpha-final" should all cluster together
    _write(
        source / "ProjectAlpha" / "alpha_raw" / "IMG_0001.JPG",
        jpg_alpha1,
        base_time,
    )
    _write(
        source / "ProjectAlpha" / "Alpha Raw" / "IMG_0002.JPG",
        jpg_alpha2,
        base_time + timedelta(minutes=2),
    )
    _write(
        source / "ProjectAlpha" / "Alpha-final" / "IMG_0001.JPG",
        jpg_alpha3,  # same name as the first one, DIFFERENT content
        base_time + timedelta(minutes=5),
    )

    # bravo cluster with an exact duplicate
    _write(
        source / "ClientBravo" / "bravo_shoot_day1" / "DSC_9000.JPG",
        jpg_bravo,
        base_time + timedelta(hours=1),
    )
    _write(
        source / "ClientBravo" / "bravo_shoot_day1" / "DSC_9001.JPG",
        jpg_bravo_extra,
        base_time + timedelta(hours=1, minutes=3),
    )
    _write(
        source / "ClientBravo" / "Bravo Shoot Day 2" / "DSC_9000.JPG",
        jpg_bravo,  # EXACT duplicate of the one above
        base_time + timedelta(hours=25),
    )

    # Singleton clusters
    _write(source / "unrelated_notes" / "notes.png", png_note, base_time)
    _write(source / "videos" / "clip1.mp4", mp4_clip, base_time + timedelta(hours=3))

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
