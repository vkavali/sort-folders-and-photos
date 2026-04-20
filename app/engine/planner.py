"""Builds the PlannedMove list that the executor will apply."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    category: str
    dest_filename: str = ""
    dest_path: Optional[Path] = None
    hash_digest: Optional[str] = None
    status: Status = "pending"
    message: str = ""


def build_plan(
    items: list[MediaItem],
    mapping: dict[str, str],
    destination_root: Path,
) -> list[PlannedMove]:
    """Create one PlannedMove per MediaItem using the user-confirmed mapping.

    Destination filename + collision suffixing are resolved later by the
    executor, because both depend on live filesystem state and hash results.
    """
    plan: list[PlannedMove] = []
    for item in items:
        category = mapping.get(item.parent_folder, "Unsorted")
        plan.append(
            PlannedMove(
                item=item,
                category=category,
                dest_path=destination_root / category,
            )
        )
    return plan
