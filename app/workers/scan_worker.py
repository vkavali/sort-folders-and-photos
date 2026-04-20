"""QThread worker that walks the source tree and clusters parent folders."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import (
    PROCESSING_MODE_FLATTEN,
    PROCESSING_MODE_GROUP,
    SIMILARITY_THRESHOLD,
)
from app.engine import scan, cluster_folders
from app.engine.clusterer import Cluster
from app.engine.scanner import MediaItem


class ScanWorker(QThread):
    progress = pyqtSignal(int)
    scan_done = pyqtSignal(list, list)  # list[MediaItem], list[Cluster]
    error = pyqtSignal(str)

    def __init__(
        self,
        source_root: Path,
        mode: str = PROCESSING_MODE_GROUP,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source_root = source_root
        self._mode = mode
        self._threshold = similarity_threshold

    def run(self) -> None:
        try:
            items: list[MediaItem] = scan(
                self._source_root,
                progress_cb=lambda n: self.progress.emit(n),
            )
            clusters: list[Cluster] = []
            if self._mode == PROCESSING_MODE_GROUP:
                counts = Counter(item.parent_folder for item in items)
                clusters = cluster_folders(counts.items(), threshold=self._threshold)
            self.scan_done.emit(items, clusters)
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"{type(exc).__name__}: {exc}")
