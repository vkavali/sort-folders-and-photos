"""Source / destination picker with mode + action + drag-and-drop."""

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
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    ACTION_COPY,
    ACTION_MOVE,
    PROCESSING_MODE_FLATTEN,
    PROCESSING_MODE_GROUP,
)


class _DropLineEdit(QLineEdit):
    def __init__(self, placeholder: str, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAcceptDrops(True)
        self._default_border: str = ""

    def _highlight(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                "QLineEdit { border: 2px solid #2563eb; background: #eff6ff; }"
            )
        else:
            self.setStyleSheet(self._default_border)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        md = event.mimeData()
        if md.hasUrls() and any(u.isLocalFile() for u in md.urls()):
            event.acceptProposedAction()
            self._highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
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


def _make_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("role", "card")
    frame.setFrameShape(QFrame.Shape.NoFrame)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 16)
    layout.setSpacing(6)
    title_label = QLabel(title)
    title_label.setProperty("role", "sectionTitle")
    layout.addWidget(title_label)
    return frame, layout


class SourcePage(QWidget):
    # src, dst, mode, action
    scan_requested = pyqtSignal(Path, Path, str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 28, 32, 28)
        outer.setSpacing(18)

        title = QLabel("Semantic File Aggregator")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Pick a source folder, a destination, and how you want things "
            "sorted. Originals stay untouched unless you choose Move."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # Mode card
        mode_card, mode_layout = _make_card("Processing mode")
        self._mode_group_radio = QRadioButton(
            "Folder picker  —  review every folder name, tick which to keep as categories"
        )
        self._mode_group_radio.setChecked(True)
        self._mode_flatten_radio = QRadioButton(
            "Flatten All  —  every file lands in the destination root, no subfolders"
        )
        mode_layout.addWidget(self._mode_group_radio)
        mode_layout.addWidget(self._mode_flatten_radio)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_group_radio)
        self._mode_group.addButton(self._mode_flatten_radio)
        outer.addWidget(mode_card)

        # Action card
        action_card, action_layout = _make_card("Action")
        self._action_copy_radio = QRadioButton(
            "Copy  —  originals stay where they are (recommended)"
        )
        self._action_copy_radio.setChecked(True)
        self._action_move_radio = QRadioButton(
            "Move  —  source files are deleted after each copy is hash-verified"
        )
        action_layout.addWidget(self._action_copy_radio)
        action_layout.addWidget(self._action_move_radio)
        self._action_group = QButtonGroup(self)
        self._action_group.addButton(self._action_copy_radio)
        self._action_group.addButton(self._action_move_radio)
        outer.addWidget(action_card)

        # Folder pickers card
        paths_card, paths_layout = _make_card("Folders")
        paths_layout.setSpacing(10)

        self._source_edit = _DropLineEdit("Drop a folder here, or browse…")
        source_btn = QPushButton("Browse…")
        source_btn.clicked.connect(self._pick_source)
        src_row = QHBoxLayout()
        src_row.addWidget(self._labeled("Source"))
        src_row.addWidget(self._source_edit, stretch=1)
        src_row.addWidget(source_btn)
        paths_layout.addLayout(src_row)

        self._dest_edit = _DropLineEdit("Drop a folder here, or browse…")
        dest_btn = QPushButton("Browse…")
        dest_btn.clicked.connect(self._pick_dest)
        dst_row = QHBoxLayout()
        dst_row.addWidget(self._labeled("Destination"))
        dst_row.addWidget(self._dest_edit, stretch=1)
        dst_row.addWidget(dest_btn)
        paths_layout.addLayout(dst_row)

        outer.addWidget(paths_card)

        outer.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scan_btn = QPushButton("Scan")
        scan_btn.setDefault(True)
        scan_btn.setMinimumHeight(40)
        scan_btn.setMinimumWidth(120)
        scan_btn.clicked.connect(self._emit_scan)
        outer.addWidget(scan_btn, alignment=Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _labeled(text: str) -> QLabel:
        label = QLabel(text)
        label.setMinimumWidth(86)
        return label

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
        action = (
            ACTION_COPY if self._action_copy_radio.isChecked() else ACTION_MOVE
        )
        self.scan_requested.emit(src, dst, mode, action)
