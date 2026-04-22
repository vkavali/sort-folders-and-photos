"""Modern Source page: drop zones + segmented toggles + single primary action."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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
from app.ui.widgets import DropZone, SegmentedControl


class SourcePage(QWidget):
    # src, dst, mode, action
    scan_requested = pyqtSignal(Path, Path, str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 40)
        outer.setSpacing(24)

        title = QLabel("Start a new run")
        title.setProperty("role", "title")
        subtitle = QLabel(
            "Pick a source folder to scan and a destination to receive "
            "the sorted files. Everything happens locally on this machine."
        )
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # Drop zones row
        zones = QHBoxLayout()
        zones.setSpacing(16)
        self._source_zone = DropZone("Source")
        self._dest_zone = DropZone("Destination")
        zones.addWidget(self._source_zone)
        zones.addWidget(self._dest_zone)
        outer.addLayout(zones)

        # Toggle row
        toggles = QHBoxLayout()
        toggles.setSpacing(36)

        mode_col = QVBoxLayout()
        mode_col.setSpacing(8)
        mode_label = QLabel("HOW TO SORT")
        mode_label.setProperty("role", "sectionTitle")
        self._mode_ctrl = SegmentedControl(
            [(PROCESSING_MODE_GROUP, "Folder picker"),
             (PROCESSING_MODE_FLATTEN, "Flatten all")],
            default=PROCESSING_MODE_GROUP,
        )
        mode_col.addWidget(mode_label)
        mode_col.addWidget(self._mode_ctrl)
        toggles.addLayout(mode_col)

        action_col = QVBoxLayout()
        action_col.setSpacing(8)
        action_label = QLabel("ACTION")
        action_label.setProperty("role", "sectionTitle")
        self._action_ctrl = SegmentedControl(
            [(ACTION_COPY, "Copy"), (ACTION_MOVE, "Move")],
            default=ACTION_COPY,
        )
        action_col.addWidget(action_label)
        action_col.addWidget(self._action_ctrl)
        toggles.addLayout(action_col)

        toggles.addStretch(1)
        outer.addLayout(toggles)

        # Helper text that reacts to selections
        self._helper = QLabel()
        self._helper.setProperty("role", "subtitle")
        self._helper.setWordWrap(True)
        self._mode_ctrl.changed.connect(lambda _k: self._update_helper())
        self._action_ctrl.changed.connect(lambda _k: self._update_helper())
        self._update_helper()
        outer.addWidget(self._helper)

        outer.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        scan_btn = QPushButton("Scan")
        scan_btn.setDefault(True)
        scan_btn.setMinimumHeight(44)
        scan_btn.setMinimumWidth(140)
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.clicked.connect(self._emit_scan)
        outer.addWidget(scan_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _update_helper(self) -> None:
        mode = self._mode_ctrl.value()
        action = self._action_ctrl.value()
        mode_text = (
            "You'll review every folder name and tick which ones to keep "
            "as destination categories."
            if mode == PROCESSING_MODE_GROUP
            else "Every file lands directly in the destination — no subfolders."
        )
        action_text = (
            "Copy leaves originals where they are."
            if action == ACTION_COPY
            else "Move deletes source files after each copy is hash-verified."
        )
        self._helper.setText(f"{mode_text}  {action_text}")

    def _emit_scan(self) -> None:
        src_text = self._source_zone.path().strip()
        dst_text = self._dest_zone.path().strip()
        if not src_text or not dst_text:
            QMessageBox.warning(self, "Missing folder", "Please choose both a source and a destination.")
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
            QMessageBox.warning(self, "Same folder", "Source and destination must be different.")
            return
        try:
            src_str = str(src_resolved)
            dst_str = str(dst_resolved)
            if dst_str == src_str or dst_str.startswith(src_str + "/") or dst_str.startswith(src_str + "\\"):
                QMessageBox.warning(
                    self,
                    "Nested destination",
                    "Destination cannot be inside the source folder.",
                )
                return
        except Exception:
            pass
        self.scan_requested.emit(
            src, dst, self._mode_ctrl.value(), self._action_ctrl.value()
        )
