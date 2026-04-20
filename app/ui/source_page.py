"""Source / destination directory picker page."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class SourcePage(QWidget):
    scan_requested = pyqtSignal(Path, Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Semantic File Aggregator")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel(
            "Flatten deeply nested photo archives into canonical event categories."
        )
        subtitle.setStyleSheet("color: #555;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addItem(QSpacerItem(0, 8))

        self._source_edit = QLineEdit()
        self._source_edit.setPlaceholderText("Source folder to scan…")
        source_btn = QPushButton("Browse…")
        source_btn.clicked.connect(self._pick_source)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source:"))
        src_row.addWidget(self._source_edit, stretch=1)
        src_row.addWidget(source_btn)

        self._dest_edit = QLineEdit()
        self._dest_edit.setPlaceholderText("Destination folder (will be created)…")
        dest_btn = QPushButton("Browse…")
        dest_btn.clicked.connect(self._pick_dest)

        dst_row = QHBoxLayout()
        dst_row.addWidget(QLabel("Destination:"))
        dst_row.addWidget(self._dest_edit, stretch=1)
        dst_row.addWidget(dest_btn)

        layout.addLayout(src_row)
        layout.addLayout(dst_row)

        layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scan_btn = QPushButton("Scan")
        scan_btn.setDefault(True)
        scan_btn.setMinimumHeight(38)
        scan_btn.clicked.connect(self._emit_scan)
        layout.addWidget(scan_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _pick_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select source folder")
        if path:
            self._source_edit.setText(path)

    def _pick_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select destination folder")
        if path:
            self._dest_edit.setText(path)

    def _emit_scan(self) -> None:
        src_text = self._source_edit.text().strip()
        dst_text = self._dest_edit.text().strip()
        if not src_text or not dst_text:
            QMessageBox.warning(self, "Missing path", "Please choose both folders.")
            return
        src = Path(src_text)
        dst = Path(dst_text)
        if not src.is_dir():
            QMessageBox.warning(self, "Invalid source", f"{src} is not a directory.")
            return
        try:
            src_resolved = src.resolve()
            dst_resolved = dst.resolve()
        except OSError:
            src_resolved, dst_resolved = src, dst
        if src_resolved == dst_resolved:
            QMessageBox.warning(
                self, "Same folder", "Source and destination must be different."
            )
            return
        try:
            if str(dst_resolved).startswith(str(src_resolved) + "/") or str(
                dst_resolved
            ).startswith(str(src_resolved) + "\\"):
                QMessageBox.warning(
                    self,
                    "Nested destination",
                    "Destination cannot be inside the source folder.",
                )
                return
        except Exception:
            pass
        self.scan_requested.emit(src, dst)
