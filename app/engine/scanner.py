"""Recursive media-file scanner using os.scandir for speed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from app.categories import MEDIA_EXTENSIONS


@dataclass(frozen=True)
class MediaItem:
    source_path: Path
    parent_folder: str
    size_bytes: int

    @property
    def extension(self) -> str:
        return self.source_path.suffix.lower()


ProgressCb = Callable[[int], None]


def _iter_media(root: Path) -> Iterator[MediaItem]:
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in MEDIA_EXTENSIONS:
                                stat = entry.stat(follow_symlinks=False)
                                yield MediaItem(
                                    source_path=Path(entry.path),
                                    parent_folder=current.name,
                                    size_bytes=stat.st_size,
                                )
                    except (PermissionError, FileNotFoundError):
                        continue
        except (PermissionError, FileNotFoundError):
            continue


def scan(root: Path, progress_cb: ProgressCb | None = None) -> list[MediaItem]:
    """Walk root recursively; return every media file found.

    progress_cb, if supplied, is invoked with the running count periodically.
    """
    items: list[MediaItem] = []
    for item in _iter_media(root):
        items.append(item)
        if progress_cb is not None and len(items) % 50 == 0:
            progress_cb(len(items))
    if progress_cb is not None:
        progress_cb(len(items))
    return items
