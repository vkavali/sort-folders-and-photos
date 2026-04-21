"""Recursive media-file scanner using os.scandir for speed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from app.config import MEDIA_EXTENSIONS


@dataclass(frozen=True)
class MediaItem:
    source_path: Path
    ancestors: tuple[str, ...]   # folder names from source_root (exclusive) down to immediate parent
    size_bytes: int

    @property
    def parent_folder(self) -> str:
        return self.ancestors[-1] if self.ancestors else ""

    @property
    def extension(self) -> str:
        return self.source_path.suffix.lower()


ProgressCb = Callable[[int], None]


def _iter_media(root: Path) -> Iterator[MediaItem]:
    root = root.resolve()
    stack: list[tuple[Path, tuple[str, ...]]] = [(root, tuple())]
    while stack:
        current, ancestors = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(
                                (Path(entry.path), ancestors + (entry.name,))
                            )
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in MEDIA_EXTENSIONS:
                                stat = entry.stat(follow_symlinks=False)
                                yield MediaItem(
                                    source_path=Path(entry.path),
                                    ancestors=ancestors,
                                    size_bytes=stat.st_size,
                                )
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue


def scan(root: Path, progress_cb: ProgressCb | None = None) -> list[MediaItem]:
    """Walk root recursively; return every media file found."""
    items: list[MediaItem] = []
    for item in _iter_media(root):
        items.append(item)
        if progress_cb is not None and len(items) % 50 == 0:
            progress_cb(len(items))
    if progress_cb is not None:
        progress_cb(len(items))
    return items
