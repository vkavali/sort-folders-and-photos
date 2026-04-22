"""Root QMainWindow: sidebar stepper + stacked pages."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QWidget,
)

from app.config import ACTION_COPY, PROCESSING_MODE_FLATTEN, PROCESSING_MODE_GROUP
from app.engine.pathindex import FolderEntry, FolderPick
from app.engine.planner import build_plan, build_plan_from_picks
from app.engine.scanner import MediaItem
from app.workers import ProcessWorker, ScanWorker
from app.ui.source_page import SourcePage
from app.ui.mapping_page import MappingPage
from app.ui.progress_page import ProgressPage
from app.ui.summary_page import SummaryPage
from app.ui.widgets import Sidebar


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Semantic File Aggregator")
        self.resize(1100, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = Sidebar(
            ["Start", "Review folders", "Processing", "Summary"]
        )
        root.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

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
        self._mapping_page.start_processing.connect(self._on_start_with_picks)
        self._progress_page.cancel_requested.connect(self._on_cancel)
        self._summary_page.done.connect(self._on_done)

        self._scan_worker: Optional[ScanWorker] = None
        self._process_worker: Optional[ProcessWorker] = None

        self._source_root: Optional[Path] = None
        self._destination_root: Optional[Path] = None
        self._mode: str = PROCESSING_MODE_GROUP
        self._action: str = ACTION_COPY
        self._items: list[MediaItem] = []
        self._folder_entries: list[FolderEntry] = []

        self._goto(0)

    # ---------- navigation ----------
    def _goto(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        self._sidebar.set_current(index)

    # ---------- workflow ----------
    def _on_scan_requested(
        self, source: Path, destination: Path, mode: str, action: str
    ) -> None:
        self._source_root = source
        self._destination_root = destination
        self._mode = mode
        self._action = action
        self.statusBar().showMessage(f"Scanning {source}…")
        self._scan_worker = ScanWorker(source)
        self._scan_worker.progress.connect(
            lambda n: self.statusBar().showMessage(f"Scanning… {n} files")
        )
        self._scan_worker.scan_done.connect(self._on_scan_done)
        self._scan_worker.error.connect(self._on_worker_error)
        self._scan_worker.start()

    def _on_scan_done(
        self, items: list[MediaItem], folder_entries: list[FolderEntry]
    ) -> None:
        self._items = items
        self._folder_entries = folder_entries
        if not items:
            QMessageBox.information(
                self, "Nothing found", "No supported media files were found."
            )
            self.statusBar().showMessage("Scan complete — no media files found.")
            return
        self.statusBar().showMessage(
            f"{len(items)} media files in {len(folder_entries)} unique folder names."
        )
        if self._mode == PROCESSING_MODE_FLATTEN:
            self._run_flatten()
            return
        self._mapping_page.set_entries(folder_entries, items)
        self._goto(1)

    def _run_flatten(self) -> None:
        if not self._destination_root:
            return
        mapping = {item.parent_folder: "" for item in self._items}
        plan = build_plan(self._items, mapping, self._destination_root)
        self._progress_page.reset(len(plan))
        self._goto(2)
        self._process_worker = ProcessWorker(
            plan, self._destination_root, action=self._action
        )
        self._process_worker.progress.connect(self._progress_page.set_progress)
        self._process_worker.log.connect(self._progress_page.append_log)
        self._process_worker.finished_stats.connect(self._on_process_finished)
        self._process_worker.error.connect(self._on_worker_error)
        self._process_worker.start()

    def _on_start_with_picks(self, picks: list[FolderPick]) -> None:
        if not self._destination_root:
            return
        plan = build_plan_from_picks(self._items, picks, self._destination_root)
        self._progress_page.reset(len(plan))
        self._goto(2)
        self._process_worker = ProcessWorker(
            plan, self._destination_root, action=self._action
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
        self._summary_page.set_result(stats, self._destination_root, self._action)
        self._goto(3)

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Worker error", message)

    def _on_done(self) -> None:
        self._items.clear()
        self._folder_entries.clear()
        self._goto(0)
