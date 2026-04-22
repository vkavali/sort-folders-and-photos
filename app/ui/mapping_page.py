"""Folder picker: every unique folder name in the tree is tickable.

Ticked rows get a destination label and an optional list of time windows
that further split the files by EXIF capture time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from PyQt6.QtCore import QDateTime, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.engine.pathindex import FolderEntry, FolderPick, TimeSplit


_COL_USE = 0
_COL_NAME = 1
_COL_OCCUR = 2
_COL_FILES = 3
_COL_LABEL = 4
_COL_SPLIT = 5


class TimeSplitDialog(QDialog):
    """Edit time-window splits for one folder pick."""

    def __init__(
        self,
        folder_name: str,
        default_label: str,
        initial_splits: list[TimeSplit],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Time splits for '{folder_name}'")
        self.resize(640, 360)
        self._default_label = default_label
        self._build_ui()
        for split in initial_splits:
            self._add_row(split)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        info = QLabel(
            "Route photos inside this folder by their EXIF capture time. "
            "Files are assigned to the first matching window; files with no "
            "matching window use the folder's default destination."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["Start (inclusive)", "End (exclusive)", "Destination label"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add window")
        add_btn.clicked.connect(lambda: self._add_row())
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_row(self, split: TimeSplit | None = None) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        start = QDateTimeEdit()
        start.setDisplayFormat("yyyy-MM-dd HH:mm")
        start.setCalendarPopup(True)
        if split and split.start is not None:
            start.setDateTime(QDateTime(split.start))
        else:
            start.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self._table.setCellWidget(row, 0, start)

        end = QDateTimeEdit()
        end.setDisplayFormat("yyyy-MM-dd HH:mm")
        end.setCalendarPopup(True)
        if split and split.end is not None:
            end.setDateTime(QDateTime(split.end))
        else:
            end.setDateTime(QDateTime.currentDateTime())
        self._table.setCellWidget(row, 1, end)

        label = QLineEdit(split.destination_label if split else self._default_label)
        self._table.setCellWidget(row, 2, label)

    def _remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()}, reverse=True)
        for r in rows:
            self._table.removeRow(r)

    def splits(self) -> list[TimeSplit]:
        result: list[TimeSplit] = []
        for row in range(self._table.rowCount()):
            start_widget = self._table.cellWidget(row, 0)
            end_widget = self._table.cellWidget(row, 1)
            label_widget = self._table.cellWidget(row, 2)
            if not start_widget or not end_widget or not label_widget:
                continue
            start: datetime = start_widget.dateTime().toPyDateTime()  # type: ignore[attr-defined]
            end: datetime = end_widget.dateTime().toPyDateTime()  # type: ignore[attr-defined]
            label = label_widget.text().strip()  # type: ignore[attr-defined]
            if not label:
                continue
            result.append(TimeSplit(start=start, end=end, destination_label=label))
        return result


class MappingPage(QWidget):
    start_processing = pyqtSignal(list)   # list[FolderPick]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[FolderEntry] = []
        # Keep per-folder-name split config separate from the table widget state
        self._time_splits: dict[str, list[TimeSplit]] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 32)
        layout.setSpacing(14)

        header = QLabel("Review discovered folders")
        header.setProperty("role", "title")
        sub = QLabel(
            "Every unique folder name in your source is listed below. Tick "
            "the ones to keep as categories. Files route to the deepest "
            "ticked ancestor. Optionally split a folder by EXIF time."
        )
        sub.setProperty("role", "subtitle")
        sub.setWordWrap(True)
        layout.addWidget(header)
        layout.addWidget(sub)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Use", "Folder name", "Occurrences", "Photos under it",
             "Destination label", "Time splits"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_NAME, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_LABEL, QHeaderView.ResizeMode.Stretch
        )
        for c in (_COL_USE, _COL_OCCUR, _COL_FILES, _COL_SPLIT):
            self._table.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.ResizeToContents
            )
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        layout.addWidget(self._table, stretch=1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        select_all = QPushButton("Select all")
        select_all.clicked.connect(lambda: self._set_all_checked(True))
        toolbar.addWidget(select_all)
        deselect_all = QPushButton("Deselect all")
        deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        toolbar.addWidget(deselect_all)
        restore = QPushButton("Restore suggestions")
        restore.clicked.connect(self._restore_suggestions)
        toolbar.addWidget(restore)
        toolbar.addStretch(1)
        start_btn = QPushButton("Start Processing")
        start_btn.setDefault(True)
        start_btn.setMinimumHeight(38)
        start_btn.setMinimumWidth(160)
        start_btn.clicked.connect(self._emit_start)
        toolbar.addWidget(start_btn)
        layout.addLayout(toolbar)

    def set_entries(self, entries: Iterable[FolderEntry]) -> None:
        self._entries = list(entries)
        self._time_splits.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for entry in self._entries:
            row = self._table.rowCount()
            self._table.insertRow(row)

            use_cell = QWidget()
            use_layout = QHBoxLayout(use_cell)
            use_layout.setContentsMargins(0, 0, 0, 0)
            use_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.setChecked(entry.auto_suggested)
            use_layout.addWidget(cb)
            self._table.setCellWidget(row, _COL_USE, use_cell)

            name_item = QTableWidgetItem(entry.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setData(Qt.ItemDataRole.UserRole, entry.name)
            self._table.setItem(row, _COL_NAME, name_item)

            occ_item = QTableWidgetItem(str(entry.occurrences))
            occ_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            occ_item.setFlags(occ_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_OCCUR, occ_item)

            files_item = QTableWidgetItem(str(entry.file_count))
            files_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            files_item.setFlags(files_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_FILES, files_item)

            label_edit = QLineEdit(entry.name)
            self._table.setCellWidget(row, _COL_LABEL, label_edit)

            split_btn = QPushButton("Time splits…")
            split_btn.clicked.connect(
                lambda _checked=False, r=row: self._edit_splits(r)
            )
            self._table.setCellWidget(row, _COL_SPLIT, split_btn)

    def _set_all_checked(self, checked: bool) -> None:
        for row in range(self._table.rowCount()):
            cb = self._use_checkbox(row)
            if cb is not None:
                cb.setChecked(checked)

    def _restore_suggestions(self) -> None:
        for row, entry in enumerate(self._entries):
            cb = self._use_checkbox(row)
            if cb is not None:
                cb.setChecked(entry.auto_suggested)

    def _use_checkbox(self, row: int) -> QCheckBox | None:
        cell = self._table.cellWidget(row, _COL_USE)
        if cell is None:
            return None
        layout = cell.layout()
        if layout is None:
            return None
        item = layout.itemAt(0)
        return item.widget() if item is not None else None  # type: ignore[return-value]

    def _edit_splits(self, row: int) -> None:
        name_item = self._table.item(row, _COL_NAME)
        label_widget = self._table.cellWidget(row, _COL_LABEL)
        if name_item is None or label_widget is None:
            return
        name = name_item.text()
        default_label = label_widget.text() if hasattr(label_widget, "text") else name  # type: ignore[attr-defined]
        dialog = TimeSplitDialog(
            name, default_label, self._time_splits.get(name, []), self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._time_splits[name] = dialog.splits()

    def _emit_start(self) -> None:
        picks: list[FolderPick] = []
        for row in range(self._table.rowCount()):
            cb = self._use_checkbox(row)
            if cb is None or not cb.isChecked():
                continue
            name_item = self._table.item(row, _COL_NAME)
            label_widget = self._table.cellWidget(row, _COL_LABEL)
            if name_item is None or label_widget is None:
                continue
            name = name_item.text()
            label = label_widget.text().strip() if hasattr(label_widget, "text") else ""  # type: ignore[attr-defined]
            if not label:
                label = name
            picks.append(
                FolderPick(
                    name=name,
                    destination_label=label,
                    time_splits=list(self._time_splits.get(name, [])),
                )
            )
        if not picks:
            QMessageBox.information(
                self,
                "No folders picked",
                "Tick at least one folder to route files into, or go back "
                "and choose Flatten All.",
            )
            return
        self.start_processing.emit(picks)
