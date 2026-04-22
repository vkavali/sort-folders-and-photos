"""Summary page: big headline + stats grid + destination shortcut."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import ACTION_MOVE
from app.engine.executor import ExecutionStats
from app.ui.widgets import attach_shadow


class _StatCard(QFrame):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        attach_shadow(self, blur=16, y_offset=3, alpha=14)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        self._label = QLabel(label.upper())
        self._label.setProperty("role", "summaryStatLabel")
        self._value = QLabel("0")
        self._value.setProperty("role", "summaryStatNumber")
        layout.addWidget(self._label)
        layout.addWidget(self._value)

    def set_value(self, value: int | str) -> None:
        self._value.setText(str(value))

    def set_label(self, label: str) -> None:
        self._label.setText(label.upper())


class SummaryPage(QWidget):
    done = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._destination: Optional[Path] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 32)
        layout.setSpacing(20)

        self._title = QLabel("All done.")
        self._title.setObjectName("summaryTitle")
        layout.addWidget(self._title)

        tagline = QLabel(
            "Every unique byte was preserved. Duplicates were isolated, not dropped."
        )
        tagline.setProperty("role", "subtitle")
        tagline.setWordWrap(True)
        layout.addWidget(tagline)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        self._total = _StatCard("Files discovered")
        self._primary = _StatCard("Copied")
        self._duplicates = _StatCard("Duplicates isolated")
        self._collisions = _StatCard("Collisions renamed")
        self._errors = _StatCard("Errors")
        self._skipped = _StatCard("Skipped")
        grid.addWidget(self._total, 0, 0)
        grid.addWidget(self._primary, 0, 1)
        grid.addWidget(self._duplicates, 0, 2)
        grid.addWidget(self._collisions, 1, 0)
        grid.addWidget(self._errors, 1, 1)
        grid.addWidget(self._skipped, 1, 2)
        for c in range(3):
            grid.setColumnStretch(c, 1)
        layout.addLayout(grid)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        self._open_btn = QPushButton("Open destination")
        self._open_btn.setMinimumHeight(40)
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.clicked.connect(self._open_destination)
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch(1)
        done_btn = QPushButton("Done")
        done_btn.setDefault(True)
        done_btn.setMinimumHeight(40)
        done_btn.setMinimumWidth(140)
        done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        done_btn.clicked.connect(self.done.emit)
        btn_row.addWidget(done_btn)
        layout.addLayout(btn_row)

    def set_result(
        self, stats: ExecutionStats, destination: Path, action: str
    ) -> None:
        self._total.set_value(stats.total)
        if action == ACTION_MOVE:
            self._primary.set_label("Moved")
            self._primary.set_value(stats.moved)
        else:
            self._primary.set_label("Copied")
            self._primary.set_value(stats.copied)
        self._duplicates.set_value(stats.duplicates)
        self._collisions.set_value(stats.collisions_renamed)
        self._errors.set_value(stats.errors)
        self._skipped.set_value(stats.skipped)
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
