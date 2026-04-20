"""Source / destination picker with mode radio, similarity slider, drag-and-drop."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    PROCESSING_MODE_FLATTEN,
    PROCESSING_MODE_GROUP,
    SIMILARITY_MAX,
    SIMILARITY_MIN,
    SIMILARITY_THRESHOLD,
)


class _DropLineEdit(QLineEdit):
    """A QLineEdit that accepts a dragged folder and sets its path as text."""

    def __init__(self, placeholder: str, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)
        self._default_style = self.styleSheet()

    def _highlight(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                "QLineEdit { border: 2px solid #2d7ef7; background: #eef5ff; }"
            )
        else:
            self.setStyleSheet(self._default_style)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        md = event.mimeData()
        if md.hasUrls() and any(u.isLocalFile() for u in md.urls()):
            event.acceptProposedAction()
            self._highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: D401
        self._highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._highlight(False)
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.setText(str(path))
                event.acceptProposedAction()
                return
        event.ignore()


class SourcePage(QWidget):
    scan_requested = pyqtSignal(Path, Path, str, float)  # src, dst, mode, threshold

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        title = QLabel("Semantic File Aggregator")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel(
            "Flatten deeply nested media archives, or dynamically group them "
            "into AI-discovered event folders. Preserves every unique byte."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #555;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        mode_box = QFrame()
        mode_box.setFrameShape(QFrame.Shape.StyledPanel)
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(14, 10, 14, 14)
        mode_label = QLabel("Processing mode")
        mode_label.setStyleSheet("font-weight: 600;")
        mode_layout.addWidget(mode_label)

        self._mode_group_radio = QRadioButton("Dynamic Grouping  (recommended)")
        self._mode_group_radio.setChecked(True)
        self._mode_flatten_radio = QRadioButton("Flatten All")
        mode_layout.addWidget(self._mode_group_radio)
        mode_layout.addWidget(self._mode_flatten_radio)

        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_group_radio)
        self._mode_group.addButton(self._mode_flatten_radio)

        self._slider_row = QWidget()
        slider_row_layout = QHBoxLayout(self._slider_row)
        slider_row_layout.setContentsMargins(18, 4, 4, 0)
        slider_row_layout.addWidget(QLabel("Similarity threshold:"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(SIMILARITY_MIN), int(SIMILARITY_MAX))
        self._slider.setValue(int(SIMILARITY_THRESHOLD))
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(5)
        self._slider_value = QLabel(f"{int(SIMILARITY_THRESHOLD)}")
        self._slider_value.setMinimumWidth(28)
        self._slider.valueChanged.connect(
            lambda v: self._slider_value.setText(str(v))
        )
        slider_row_layout.addWidget(self._slider, stretch=1)
        slider_row_layout.addWidget(self._slider_value)
        mode_layout.addWidget(self._slider_row)

        self._mode_group_radio.toggled.connect(self._on_mode_changed)
        layout.addWidget(mode_box)

        self._source_edit = _DropLineEdit("Drop or browse the source folder…")
        source_btn = QPushButton("Browse…")
        source_btn.clicked.connect(self._pick_source)
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source:     "))
        src_row.addWidget(self._source_edit, stretch=1)
        src_row.addWidget(source_btn)
        layout.addLayout(src_row)

        self._dest_edit = _DropLineEdit("Drop or browse the destination folder…")
        dest_btn = QPushButton("Browse…")
        dest_btn.clicked.connect(self._pick_dest)
        dst_row = QHBoxLayout()
        dst_row.addWidget(QLabel("Destination:"))
        dst_row.addWidget(self._dest_edit, stretch=1)
        dst_row.addWidget(dest_btn)
        layout.addLayout(dst_row)

        layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scan_btn = QPushButton("Scan")
        scan_btn.setDefault(True)
        scan_btn.setMinimumHeight(38)
        scan_btn.clicked.connect(self._emit_scan)
        layout.addWidget(scan_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _on_mode_changed(self, _checked: bool) -> None:
        self._slider_row.setEnabled(self._mode_group_radio.isChecked())

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
            src_str = str(src_resolved)
            dst_str = str(dst_resolved)
            if dst_str == src_str or dst_str.startswith(src_str + "/") or dst_str.startswith(
                src_str + "\\"
            ):
                QMessageBox.warning(
                    self,
                    "Nested destination",
                    "Destination cannot be inside the source folder.",
                )
                return
        except Exception:
            pass
        mode = (
            PROCESSING_MODE_GROUP
            if self._mode_group_radio.isChecked()
            else PROCESSING_MODE_FLATTEN
        )
        threshold = float(self._slider.value())
        self.scan_requested.emit(src, dst, mode, threshold)
