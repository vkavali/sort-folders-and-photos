"""End-to-end tests for planner + executor (flatten + group modes, collisions, dupes)."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest

from app.config import DUPLICATES_DIR
from app.engine import build_plan, cluster_folders, execute_plan, scan


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _jpeg(color: int) -> bytes:
    """Produce a tiny unique-byte blob with a .jpg extension semantic.

    Pillow isn't needed for these tests; the scanner only cares about the
    extension, and we use mtime fallback for timestamps.
    """
    return b"\xff\xd8\xff\xe0" + bytes([color]) + b"\x00" * 32 + bytes([color])


def _build_group_mode_fixture(tmp_path: Path) -> tuple[Path, Path]:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    # alpha cluster — same-name different-content IMG_0001.JPG in two of three
    _write(src / "alpha_raw" / "IMG_0001.JPG", _jpeg(0x11))
    _write(src / "Alpha Raw" / "IMG_0002.JPG", _jpeg(0x12))
    _write(src / "Alpha-final" / "IMG_0001.JPG", _jpeg(0x33))
    # bravo cluster — includes an exact duplicate across its two folders
    _write(src / "bravo_shoot_day1" / "DSC_9000.JPG", _jpeg(0x55))
    _write(src / "Bravo Shoot Day 2" / "DSC_9000.JPG", _jpeg(0x55))  # exact dup
    # singleton
    _write(src / "unrelated_notes" / "notes.png", _jpeg(0x99))
    return src, dst


def test_group_mode_end_to_end(tmp_path: Path):
    src, dst = _build_group_mode_fixture(tmp_path)
    items = scan(src)
    assert len(items) == 6

    counts = Counter(i.parent_folder for i in items)
    clusters = cluster_folders(counts.items(), threshold=80)

    mapping: dict[str, str] = {}
    for c in clusters:
        for m in c.members:
            mapping[m] = c.label

    plan = build_plan(items, mapping, dst)
    stats = execute_plan(plan, dst)

    assert stats.total == 6
    # 5 unique files + 1 exact duplicate → 5 moved, 1 duplicate isolated
    assert stats.duplicates == 1
    assert stats.moved + stats.collisions_renamed >= 5
    assert stats.errors == 0

    # Exactly 1 Duplicates tree present
    dup_root = dst / DUPLICATES_DIR
    assert dup_root.exists()
    dup_files = [p for p in dup_root.rglob("*") if p.is_file()]
    assert len(dup_files) == 1

    # Same-name-different-content IMG_0001.JPG collides inside the alpha
    # cluster → automatic _N suffix.
    all_dest_files = [p for p in dst.rglob("*") if p.is_file()]
    names = [p.name for p in all_dest_files]
    img_0001_in_dest = [n for n in names if "IMG_0001" in n]
    assert len(img_0001_in_dest) >= 2  # both variants preserved

    # Every destination filename is timestamp-prefixed (YYYYMMDD_HHMMSS_)
    for p in all_dest_files:
        assert len(p.name) >= 16
        assert p.name[8] == "_"

    # All source FILES removed after successful copy/verify
    remaining_src_files = [p for p in src.rglob("*") if p.is_file()]
    assert remaining_src_files == [], (
        f"source still has files: {remaining_src_files}"
    )
    # Empty source directories are intentionally left in place per spec §12
    remaining_src_dirs = [p for p in src.rglob("*") if p.is_dir()]
    assert len(remaining_src_dirs) >= 1


def test_flatten_mode_single_bucket(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "folder_a" / "IMG_0001.JPG", _jpeg(0x11))
    _write(src / "folder_b" / "IMG_0001.JPG", _jpeg(0x22))  # name-collision
    _write(src / "folder_c" / "IMG_0001.JPG", _jpeg(0x11))  # exact dup of #1

    items = scan(src)
    mapping = {i.parent_folder: "" for i in items}
    plan = build_plan(items, mapping, dst)
    stats = execute_plan(plan, dst)

    assert stats.total == 3
    assert stats.duplicates == 1
    assert stats.errors == 0
    # With one true dup + one distinct collision, 2 files land in dst,
    # 1 lands in Duplicates.
    live_files = [p for p in dst.iterdir() if p.is_file()]
    assert len(live_files) == 2
    dup_files = list((dst / DUPLICATES_DIR).rglob("*"))
    assert any(p.is_file() for p in dup_files)


def test_size_prefilter_avoids_hashing_unique_sizes(tmp_path: Path):
    """Files with unique sizes must NOT trigger full-file hashing."""
    import app.engine.executor as exe

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "f1" / "a.jpg", b"\xff\xd8\xff" + b"x" * 100)   # unique size
    _write(src / "f2" / "b.jpg", b"\xff\xd8\xff" + b"y" * 200)   # unique size
    _write(src / "f3" / "c.jpg", b"\xff\xd8\xff" + b"z" * 200)   # size-peer with b.jpg

    items = scan(src)
    plan = build_plan(items, {i.parent_folder: "" for i in items}, dst)

    hash_calls = {"n": 0}
    original = exe.file_digest

    def _spy(path: Path, **kwargs):
        hash_calls["n"] += 1
        return original(path, **kwargs)

    exe.file_digest = _spy
    try:
        stats = execute_plan(plan, dst)
    finally:
        exe.file_digest = original

    assert stats.errors == 0
    # a.jpg (unique size) skips hashing on the source. b.jpg and c.jpg are
    # size-peers so they DO hash. Each also re-hashes the destination for
    # verification. Unique-size file verifies by size, so it shouldn't
    # contribute to hash_calls for either source or dest.
    # Lower bound: at least 2 hash calls for size-peer pair; upper bound
    # 4 (2 source + 2 dest). Strictly less than 6 (all six possible).
    assert hash_calls["n"] >= 2
    assert hash_calls["n"] <= 4
