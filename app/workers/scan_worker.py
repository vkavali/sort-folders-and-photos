"""QThread worker that walks the source tree and suggests category mappings."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.engine import scan, suggest_mappings
from app.engine.matcher import Mapping
from app.engine.scanner import MediaItem


class ScanWorker(QThread):
    progress = pyqtSignal(int)
    scan_done = pyqtSignal(list, list)  # list[MediaItem], list[Mapping]
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
            counts = Counter(item.parent_folder for item in items)
            mappings: list[Mapping] = suggest_mappings(counts.items())
            self.scan_done.emit(items, mappings)
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"{type(exc).__name__}: {exc}")
