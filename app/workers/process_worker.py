"""QThread worker that executes the move plan using a ThreadPoolExecutor."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.engine import execute_plan, build_plan
from app.engine.executor import ExecutionStats
from app.engine.planner import PlannedMove
from app.engine.scanner import MediaItem


class ProcessWorker(QThread):
    progress = pyqtSignal(int, int)           # done, total
    log = pyqtSignal(str)
    file_done = pyqtSignal(object)            # PlannedMove
    finished_stats = pyqtSignal(object)       # ExecutionStats
    error = pyqtSignal(str)

    def __init__(
        self,
        items: list[MediaItem],
        mapping: dict[str, str],
        destination_root: Path,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._items = items
        self._mapping = mapping
        self._destination_root = destination_root
        self._done = 0

    def _on_file_done(self, plan: PlannedMove) -> None:
        self._done += 1
        self.file_done.emit(plan)
        self.progress.emit(self._done, len(self._items))

    def _cancel_check(self) -> bool:
        return self.isInterruptionRequested()

    def run(self) -> None:
        try:
            plan = build_plan(self._items, self._mapping, self._destination_root)
            stats: ExecutionStats = execute_plan(
                plan,
                self._destination_root,
                file_done_cb=self._on_file_done,
                log_cb=self.log.emit,
                cancel_cb=self._cancel_check,
            )
            self.finished_stats.emit(stats)
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"{type(exc).__name__}: {exc}")
