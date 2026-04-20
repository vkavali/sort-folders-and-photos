"""Root QMainWindow wiring the four stacked pages together."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
)

from app.config import (
    PROCESSING_MODE_FLATTEN,
    PROCESSING_MODE_GROUP,
    SIMILARITY_THRESHOLD,
)
from app.engine.clusterer import Cluster, cluster_folders, merge_clusters
from app.engine.scanner import MediaItem
from app.workers import ProcessWorker, ScanWorker
from app.ui.source_page import SourcePage
from app.ui.mapping_page import MappingPage
from app.ui.progress_page import ProgressPage
from app.ui.summary_page import SummaryPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Semantic File Aggregator")
        self.resize(960, 640)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self.setStatusBar(QStatusBar())

        self._source_page = SourcePage()
        self._mapping_page = MappingPage()
        self._progress_page = ProgressPage()
        self._summary_page = SummaryPage()

        for page in (
            self._source_page,
            self._mapping_page,
            self._progress_page,
            self._summary_page,
        ):
            self._stack.addWidget(page)

        self._source_page.scan_requested.connect(self._on_scan_requested)
        self._mapping_page.start_processing.connect(self._on_start_processing)
        self._mapping_page.recluster_requested.connect(self._on_recluster)
        self._mapping_page.merge_requested.connect(self._on_merge)
        self._progress_page.cancel_requested.connect(self._on_cancel)
        self._summary_page.done.connect(self._on_done)

        self._scan_worker: Optional[ScanWorker] = None
        self._process_worker: Optional[ProcessWorker] = None

        self._source_root: Optional[Path] = None
        self._destination_root: Optional[Path] = None
        self._mode: str = PROCESSING_MODE_GROUP
        self._similarity_threshold: float = SIMILARITY_THRESHOLD
        self._items: list[MediaItem] = []
        self._clusters: list[Cluster] = []

    def _on_scan_requested(
        self, source: Path, destination: Path, mode: str, threshold: float
    ) -> None:
        self._source_root = source
        self._destination_root = destination
        self._mode = mode
        self._similarity_threshold = threshold
        self.statusBar().showMessage(f"Scanning {source}…")
        self._scan_worker = ScanWorker(source, mode=mode, similarity_threshold=threshold)
        self._scan_worker.progress.connect(
            lambda n: self.statusBar().showMessage(f"Scanning… {n} files")
        )
        self._scan_worker.scan_done.connect(self._on_scan_done)
        self._scan_worker.error.connect(self._on_worker_error)
        self._scan_worker.start()

    def _on_scan_done(self, items: list[MediaItem], clusters: list[Cluster]) -> None:
        self._items = items
        self._clusters = clusters
        self.statusBar().showMessage(
            f"{len(items)} media files discovered across "
            f"{len({i.parent_folder for i in items})} folders."
        )
        if not items:
            QMessageBox.information(
                self, "Nothing found", "No supported media files were found."
            )
            return

        if self._mode == PROCESSING_MODE_FLATTEN:
            mapping = {item.parent_folder: "" for item in items}
            self._start_processing_with_mapping(mapping)
            return

        self._mapping_page.set_clusters(clusters, self._similarity_threshold)
        self._stack.setCurrentWidget(self._mapping_page)

    def _on_recluster(self, threshold: float) -> None:
        self._similarity_threshold = threshold
        if not self._items:
            return
        counts = Counter(item.parent_folder for item in self._items)
        self._clusters = cluster_folders(counts.items(), threshold=threshold)
        self._mapping_page.set_clusters(self._clusters, threshold)

    def _on_merge(self, ids: list[int], target_id: object) -> None:
        if not self._clusters or len(ids) < 2:
            return
        ordered = list(dict.fromkeys(ids))
        if isinstance(target_id, int) and target_id in ordered:
            ordered.remove(target_id)
            ordered.insert(0, target_id)
        survivor_label = next(
            (c.label for c in self._clusters if c.id == ordered[0]), None
        )
        self._clusters = merge_clusters(self._clusters, ordered, new_label=survivor_label)
        self._mapping_page.set_clusters(self._clusters, self._similarity_threshold)

    def _on_start_processing(self, mapping: dict[str, str]) -> None:
        self._start_processing_with_mapping(mapping)

    def _start_processing_with_mapping(self, mapping: dict[str, str]) -> None:
        if self._destination_root is None:
            return
        self._progress_page.reset(len(self._items))
        self._stack.setCurrentWidget(self._progress_page)
        self._process_worker = ProcessWorker(
            self._items, mapping, self._destination_root
        )
        self._process_worker.progress.connect(self._progress_page.set_progress)
        self._process_worker.log.connect(self._progress_page.append_log)
        self._process_worker.finished_stats.connect(self._on_process_finished)
        self._process_worker.error.connect(self._on_worker_error)
        self._process_worker.start()

    def _on_cancel(self) -> None:
        if self._process_worker is not None:
            self._process_worker.requestInterruption()
            self.statusBar().showMessage(
                "Cancellation requested — finishing in-flight copies…"
            )

    def _on_process_finished(self, stats) -> None:
        self.statusBar().showMessage("Done.")
        assert self._destination_root is not None
        self._summary_page.set_result(stats, self._destination_root)
        self._stack.setCurrentWidget(self._summary_page)

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Worker error", message)

    def _on_done(self) -> None:
        self._items.clear()
        self._clusters.clear()
        self._stack.setCurrentWidget(self._source_page)
