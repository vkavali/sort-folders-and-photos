"""End-to-end tests for planner + executor in both actions and both modes."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import ACTION_COPY, ACTION_MOVE, DUPLICATES_DIR, UNSORTED_DIR
from app.engine import (
    build_folder_index,
    build_plan,
    execute_plan,
    scan,
)
from app.engine.pathindex import FolderPick
from app.engine.planner import build_plan_from_picks


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _jpeg(color: int) -> bytes:
    return b"\xff\xd8\xff\xe0" + bytes([color]) + b"\x00" * 32 + bytes([color])


def _build_nested_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Mimic the user's real tree: two Marriage-xxx containers each with the
    same HALDI&SANGEETH and Marriage Selected named subfolders."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(
        src / "Marriage-001" / "Marriage" / "HALDI&SANGEETH" / "PICS" / "IMG_0001.JPG",
        _jpeg(0x11),
    )
    _write(
        src / "Marriage-002" / "Marriage" / "HALDI&SANGEETH" / "PICS" / "IMG_0002.JPG",
        _jpeg(0x22),
    )
    _write(
        src / "Marriage-001" / "Marriage" / "Marriage Selected" / "DSC_9000.JPG",
        _jpeg(0x55),
    )
    _write(
        src / "Marriage-002" / "Marriage" / "Marriage Selected" / "DSC_9000.JPG",
        _jpeg(0x55),   # EXACT duplicate
    )
    _write(src / "unrelated" / "note.png", _jpeg(0x99))
    return src, dst


def test_folder_picker_routes_across_timestamped_parents(tmp_path: Path):
    src, dst = _build_nested_fixture(tmp_path)
    items = scan(src)
    assert len(items) == 5

    index = {e.name: e for e in build_folder_index(items)}
    # Generic container name → untick; meaningful name → tick.
    assert index["PICS"].auto_suggested is False
    assert index["HALDI&SANGEETH"].auto_suggested is True

    picks = [
        FolderPick(name="HALDI&SANGEETH", destination_label="Haldi_Sangeet"),
        FolderPick(name="Marriage Selected", destination_label="Wedding"),
    ]
    plan = build_plan_from_picks(items, picks, dst)
    stats = execute_plan(plan, dst, action=ACTION_COPY)

    assert stats.errors == 0
    assert stats.copied >= 3      # 2 HALDI files + 1 Wedding file
    assert stats.duplicates == 1  # 1 Wedding duplicate isolated
    assert stats.moved == 0       # Copy action leaves source alive

    # Two Marriage-xxx parents routed to the same Haldi_Sangeet folder.
    hs = [p for p in (dst / "Haldi_Sangeet").iterdir() if p.is_file()]
    assert len(hs) == 2
    # Wedding has one live file + the dup is in Duplicates/.
    wed = [p for p in (dst / "Wedding").iterdir() if p.is_file()]
    assert len(wed) == 1
    dups = [p for p in (dst / DUPLICATES_DIR).rglob("*") if p.is_file()]
    assert len(dups) == 1
    # unrelated/note.png didn't match any pick → Unsorted.
    assert (dst / UNSORTED_DIR).is_dir()


def test_copy_leaves_sources_move_removes_them(tmp_path: Path):
    src, dst = _build_nested_fixture(tmp_path)
    items = scan(src)
    picks = [FolderPick(name="HALDI&SANGEETH", destination_label="HS")]

    plan = build_plan_from_picks(items, picks, dst)
    execute_plan(plan, dst, action=ACTION_COPY)

    # Every source file still exists.
    remaining = sorted(p.relative_to(src) for p in src.rglob("*") if p.is_file())
    assert len(remaining) == 5, remaining

    # Redo with MOVE on a fresh fixture.
    src2 = tmp_path / "src2"
    dst2 = tmp_path / "dst2"
    _write(src2 / "Marriage-001" / "HALDI&SANGEETH" / "PICS" / "a.jpg", _jpeg(0x11))
    items2 = scan(src2)
    picks2 = [FolderPick(name="HALDI&SANGEETH", destination_label="HS")]
    plan2 = build_plan_from_picks(items2, picks2, dst2)
    stats2 = execute_plan(plan2, dst2, action=ACTION_MOVE)

    assert stats2.moved == 1
    assert stats2.copied == 0
    assert [p for p in src2.rglob("*") if p.is_file()] == []


def test_flatten_mode_single_bucket(tmp_path: Path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "a" / "IMG_0001.JPG", _jpeg(0x11))
    _write(src / "b" / "IMG_0001.JPG", _jpeg(0x22))  # collision
    _write(src / "c" / "IMG_0001.JPG", _jpeg(0x11))  # exact dup of first

    items = scan(src)
    mapping = {i.parent_folder: "" for i in items}
    plan = build_plan(items, mapping, dst)
    stats = execute_plan(plan, dst, action=ACTION_COPY)

    assert stats.errors == 0
    assert stats.duplicates == 1
    live = [p for p in dst.iterdir() if p.is_file()]
    assert len(live) == 2
    assert any(p.is_file() for p in (dst / DUPLICATES_DIR).rglob("*"))


def test_cancel_stops_submitting_new_files(tmp_path: Path):
    """cancel_cb returning True should result in remaining files being
    marked skipped, and no further files touched on disk."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    # Make several files so the batch-submit loop runs more than once.
    for i in range(12):
        _write(src / f"folder_{i}" / f"IMG_{i}.JPG", _jpeg(i))

    items = scan(src)
    mapping = {i.parent_folder: "" for i in items}
    plan = build_plan(items, mapping, dst)

    # Flip cancellation on after the 3rd file finishes.
    processed = {"n": 0}
    cancelled = {"flag": False}

    def _on_done(_p):
        processed["n"] += 1
        if processed["n"] >= 3:
            cancelled["flag"] = True

    stats = execute_plan(
        plan,
        dst,
        action=ACTION_COPY,
        max_workers=2,
        file_done_cb=_on_done,
        cancel_cb=lambda: cancelled["flag"],
    )

    # Some files should be skipped.
    assert stats.skipped > 0
    # The ones we did process land in destination; source copies still exist.
    assert stats.total == 12
    assert (stats.copied + stats.skipped + stats.errors + stats.duplicates) == 12


def test_size_prefilter_avoids_hashing_unique_sizes(tmp_path: Path):
    import app.engine.executor as exe

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    _write(src / "f1" / "a.jpg", b"\xff\xd8\xff" + b"x" * 100)   # unique size
    _write(src / "f2" / "b.jpg", b"\xff\xd8\xff" + b"y" * 200)   # unique size
    _write(src / "f3" / "c.jpg", b"\xff\xd8\xff" + b"z" * 200)   # size-peer of b.jpg

    items = scan(src)
    plan = build_plan(items, {i.parent_folder: "" for i in items}, dst)

    calls = {"n": 0}
    orig = exe.file_digest

    def _spy(path: Path, **kwargs):
        calls["n"] += 1
        return orig(path, **kwargs)

    exe.file_digest = _spy
    try:
        stats = execute_plan(plan, dst, action=ACTION_COPY)
    finally:
        exe.file_digest = orig

    assert stats.errors == 0
    # Size-peers hash: 2 source + 2 dest verifications = 4. Unique-size file
    # verifies by size, no hash. Strict upper bound is 4.
    assert 2 <= calls["n"] <= 4
