"""QThread worker that walks the source tree and builds the folder index."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.engine import scan, build_folder_index
from app.engine.pathindex import FolderEntry
from app.engine.scanner import MediaItem


class ScanWorker(QThread):
    progress = pyqtSignal(int)
    scan_done = pyqtSignal(list, list)   # list[MediaItem], list[FolderEntry]
    error = pyqtSignal(str)

    def __init__(self, source_root: Path, parent=None) -> None:
        super().__init__(parent)
        self._source_root = source_root

    def run(self) -> None:
        try:
            items: list[MediaItem] = scan(
                self._source_root,
                progress_cb=lambda n: self.progress.emit(n),
            )
            folders: list[FolderEntry] = build_folder_index(items)
            self.scan_done.emit(items, folders)
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"{type(exc).__name__}: {exc}")
