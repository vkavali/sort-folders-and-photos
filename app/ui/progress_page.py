"""Progress page: determinate progress bar + live log + cancel button."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ProgressPage(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QLabel("Processing…")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(header)

        self._counter = QLabel("0 / 0")
        self._counter.setStyleSheet("color: #555;")
        layout.addWidget(self._counter)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1)
        self._bar.setValue(0)
        layout.addWidget(self._bar)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(5000)
        self._log.setStyleSheet(
            "QPlainTextEdit { font-family: Consolas, 'Courier New', monospace; "
            "font-size: 11px; background: #111; color: #ddd; }"
        )
        layout.addWidget(self._log, stretch=1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel)
        bar.addWidget(self._cancel_btn)
        layout.addLayout(bar)

    def reset(self, total: int) -> None:
        self._bar.setRange(0, max(1, total))
        self._bar.setValue(0)
        self._counter.setText(f"0 / {total}")
        self._log.clear()
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText("Cancel")

    def set_progress(self, done: int, total: int) -> None:
        self._bar.setRange(0, max(1, total))
        self._bar.setValue(done)
        self._counter.setText(f"{done} / {total}")

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def _on_cancel(self) -> None:
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("Cancelling…")
        self.cancel_requested.emit()
