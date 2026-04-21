"""QThread worker that executes the move/copy plan."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import ACTION_COPY
from app.engine.executor import ExecutionStats, execute_plan
from app.engine.planner import PlannedMove


class ProcessWorker(QThread):
    progress = pyqtSignal(int, int)           # done, total
    log = pyqtSignal(str)
    file_done = pyqtSignal(object)            # PlannedMove
    finished_stats = pyqtSignal(object)       # ExecutionStats
    error = pyqtSignal(str)

    def __init__(
        self,
        plan: list[PlannedMove],
        destination_root: Path,
        action: str = ACTION_COPY,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._plan = plan
        self._destination_root = destination_root
        self._action = action
        self._done = 0

    def _on_file_done(self, plan: PlannedMove) -> None:
        self._done += 1
        self.file_done.emit(plan)
        self.progress.emit(self._done, len(self._plan))

    def _cancel_check(self) -> bool:
        return self.isInterruptionRequested()

    def run(self) -> None:
        try:
            stats: ExecutionStats = execute_plan(
                self._plan,
                self._destination_root,
                action=self._action,
                file_done_cb=self._on_file_done,
                log_cb=self.log.emit,
                cancel_cb=self._cancel_check,
            )
            self.finished_stats.emit(stats)
        except Exception as exc:  # pragma: no cover
            self.error.emit(f"{type(exc).__name__}: {exc}")
