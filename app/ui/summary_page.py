"""Final summary page showing per-status counts and destination shortcut."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.engine.executor import ExecutionStats


class SummaryPage(QWidget):
    done = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._destination: Optional[Path] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        header = QLabel("All done.")
        header.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(header)

        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        form = QFormLayout(panel)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(8)

        self._total = QLabel("0")
        self._moved = QLabel("0")
        self._duplicates = QLabel("0")
        self._collisions = QLabel("0")
        self._errors = QLabel("0")
        self._skipped = QLabel("0")
        for label in (
            self._total,
            self._moved,
            self._duplicates,
            self._collisions,
            self._errors,
            self._skipped,
        ):
            label.setStyleSheet("font-weight: 600;")

        form.addRow("Total files discovered:", self._total)
        form.addRow("Moved:", self._moved)
        form.addRow("Duplicates isolated:", self._duplicates)
        form.addRow("Name collisions renamed:", self._collisions)
        form.addRow("Errors:", self._errors)
        form.addRow("Skipped (cancelled):", self._skipped)

        layout.addWidget(panel)
        layout.addStretch(1)

        btn_row = QHBoxLayout()
        self._open_btn = QPushButton("Open Destination")
        self._open_btn.clicked.connect(self._open_destination)
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch(1)
        done_btn = QPushButton("Done")
        done_btn.setDefault(True)
        done_btn.clicked.connect(self.done.emit)
        btn_row.addWidget(done_btn)
        layout.addLayout(btn_row)

    def set_result(self, stats: ExecutionStats, destination: Path) -> None:
        self._total.setText(str(stats.total))
        self._moved.setText(str(stats.moved))
        self._duplicates.setText(str(stats.duplicates))
        self._collisions.setText(str(stats.collisions_renamed))
        self._errors.setText(str(stats.errors))
        self._skipped.setText(str(stats.skipped))
        self._destination = destination

    def _open_destination(self) -> None:
        if self._destination is None:
            return
        path = str(self._destination)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
