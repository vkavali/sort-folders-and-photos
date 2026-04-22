"""All-depths folder enumeration, smart-default suggestions, and routing.

Replaces the fuzzy clusterer. Under the new user model, every distinct
folder name that appears anywhere in the source tree is a candidate
destination category. The user ticks which names are meaningful, gives
each a destination label, and optionally splits by EXIF timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from app.config import (
    is_generic_folder_name,
    looks_like_timestamp_name,
)
from app.engine.scanner import MediaItem


@dataclass
class FolderEntry:
    name: str
    occurrences: int             # number of distinct ancestor paths using this name
    file_count: int              # media files whose path includes this folder name
    auto_suggested: bool         # sensible default for the "Use" checkbox


@dataclass
class TimeSplit:
    """Half-open time window: start <= t < end.

    Either bound may be None (open-ended). destination_label is required.
    """
    start: Optional[datetime]
    end: Optional[datetime]
    destination_label: str

    def contains(self, t: datetime) -> bool:
        if self.start is not None and t < self.start:
            return False
        if self.end is not None and t >= self.end:
            return False
        return True


@dataclass
class FolderPick:
    """The user's decision about one folder name."""
    name: str
    destination_label: str


def build_folder_index(items: Iterable[MediaItem]) -> list[FolderEntry]:
    """Enumerate every unique ancestor-folder name with counts + defaults."""
    occurrences: dict[str, set[tuple[str, ...]]] = {}
    file_counts: dict[str, int] = {}

    for item in items:
        seen_this_file: set[str] = set()
        for depth in range(1, len(item.ancestors) + 1):
            prefix = item.ancestors[:depth]
            name = prefix[-1]
            occurrences.setdefault(name, set()).add(prefix)
            if name not in seen_this_file:
                file_counts[name] = file_counts.get(name, 0) + 1
                seen_this_file.add(name)

    entries: list[FolderEntry] = []
    for name in sorted(occurrences.keys(), key=str.lower):
        entries.append(
            FolderEntry(
                name=name,
                occurrences=len(occurrences[name]),
                file_count=file_counts.get(name, 0),
                auto_suggested=_auto_suggest(name),
            )
        )
    entries.sort(key=lambda e: (-e.file_count, e.name.lower()))
    return entries


def _auto_suggest(name: str) -> bool:
    if is_generic_folder_name(name):
        return False
    if looks_like_timestamp_name(name):
        return False
    if not name.strip():
        return False
    return True


def route_file(
    item: MediaItem,
    picks: dict[str, FolderPick],
    timestamp: datetime | None = None,
    time_splits: list[TimeSplit] | None = None,
) -> str:
    """Pick a destination label for one file.

    1. Walk ancestors from deepest to shallowest; first ticked pick wins.
    2. If global time_splits are provided AND the file has a matching
       ticked ancestor, a matching time window OVERRIDES the folder's
       destination label. Files not under any ticked ancestor are NOT
       affected by time_splits — they fall through to Unsorted.
    """
    base_label = ""
    for i in range(len(item.ancestors) - 1, -1, -1):
        name = item.ancestors[i]
        pick = picks.get(name)
        if pick is not None:
            base_label = pick.destination_label
            break
    if not base_label:
        return ""
    if time_splits and timestamp is not None:
        for split in time_splits:
            if split.contains(timestamp):
                return split.destination_label
    return base_label
