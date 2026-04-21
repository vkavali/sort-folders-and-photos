"""Builds the PlannedMove list.

Supports three categorization paths:
  * Flatten mode              — everyone gets category "".
  * Folder-picker mode        — route_file() against user's picks.
  * Pre-baked mapping (tests) — explicit parent_folder → label dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from app.config import UNSORTED_DIR
from app.engine.exif import extract_timestamp
from app.engine.pathindex import FolderPick, route_file
from app.engine.scanner import MediaItem


Status = Literal[
    "pending",
    "moved",
    "copied",
    "duplicate",
    "collision_renamed",
    "error",
    "skipped",
]


@dataclass
class PlannedMove:
    item: MediaItem
    category: str = ""
    dest_filename: str = ""
    dest_path: Optional[Path] = None
    hash_digest: Optional[str] = None
    status: Status = "pending"
    message: str = ""


def build_plan_from_picks(
    items: list[MediaItem],
    picks: list[FolderPick],
    destination_root: Path,
    *,
    fallback_to_unsorted: bool = True,
) -> list[PlannedMove]:
    """Route each item to the deepest-matching ticked folder-name pick."""
    by_name: dict[str, FolderPick] = {p.name: p for p in picks}
    plan: list[PlannedMove] = []
    needs_time = any(p.time_splits for p in picks)
    for item in items:
        timestamp = extract_timestamp(item.source_path) if needs_time else None
        label = route_file(item, by_name, timestamp)
        if not label:
            label = UNSORTED_DIR if fallback_to_unsorted else ""
        plan.append(PlannedMove(item=item, category=label))
    return plan


def build_plan(
    items: list[MediaItem],
    folder_to_category: dict[str, str],
    destination_root: Path,
) -> list[PlannedMove]:
    """Simple explicit mapping path (Flatten mode passes empty strings)."""
    plan: list[PlannedMove] = []
    for item in items:
        category = folder_to_category.get(item.parent_folder, "")
        plan.append(PlannedMove(item=item, category=category))
    return plan
