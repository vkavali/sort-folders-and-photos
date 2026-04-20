"""Builds the PlannedMove list from a cluster mapping (Group mode) or empty
category (Flatten mode)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from app.engine.scanner import MediaItem


Status = Literal[
    "pending",
    "moved",
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


def build_plan(
    items: list[MediaItem],
    folder_to_category: dict[str, str],
    destination_root: Path,
) -> list[PlannedMove]:
    """Map each item to a PlannedMove.

    folder_to_category maps parent folder name → target category label.
    An empty-string category routes the file to the destination root (Flatten
    mode); a non-empty category routes it to <destination_root>/<category>/.
    """
    plan: list[PlannedMove] = []
    for item in items:
        category = folder_to_category.get(item.parent_folder, "")
        plan.append(PlannedMove(item=item, category=category))
    return plan
