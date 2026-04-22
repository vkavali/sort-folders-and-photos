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
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
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
from app.ui.widgets import TickButton


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
        self._table.verticalHeader().setDefaultSectionSize(40)
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
        self._row_ticks: list[TickButton] = []
        self._row_splits: dict[int, list[TimeSplit]] = {}   # by row index
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
            ["Use", "Folder name", "Occurrences", "Photos", "Destination label",
             "Time splits"]
        )
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(_COL_LABEL, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(_COL_USE, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_USE, 64)
        header_view.setSectionResizeMode(_COL_OCCUR, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(_COL_FILES, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(_COL_SPLIT, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_SPLIT, 130)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(48)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
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
        start_btn.setMinimumHeight(40)
        start_btn.setMinimumWidth(160)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(self._emit_start)
        toolbar.addWidget(start_btn)
        layout.addLayout(toolbar)

    def set_entries(self, entries: Iterable[FolderEntry]) -> None:
        self._entries = list(entries)
        self._row_ticks.clear()
        self._row_splits.clear()
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        self._row_ticks.clear()
        for entry in self._entries:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # Tick button in a centered cell container
            tick_cell = QWidget()
            tick_layout = QHBoxLayout(tick_cell)
            tick_layout.setContentsMargins(0, 0, 0, 0)
            tick_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tick = TickButton()
            tick.setChecked(entry.auto_suggested)
            tick_layout.addWidget(tick)
            self._table.setCellWidget(row, _COL_USE, tick_cell)
            self._row_ticks.append(tick)

            # Folder name — non-editable
            name_item = QTableWidgetItem(entry.name)
            name_item.setFlags(
                (name_item.flags() | Qt.ItemFlag.ItemIsEnabled)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            name_item.setData(Qt.ItemDataRole.UserRole, entry.name)
            self._table.setItem(row, _COL_NAME, name_item)

            # Counts — non-editable
            occ_item = QTableWidgetItem(str(entry.occurrences))
            occ_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            occ_item.setFlags(occ_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_OCCUR, occ_item)

            files_item = QTableWidgetItem(str(entry.file_count))
            files_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            files_item.setFlags(files_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, _COL_FILES, files_item)

            # Destination label — NATIVE editable table item. Cleanest look.
            label_item = QTableWidgetItem(entry.name)
            label_item.setFlags(label_item.flags() | Qt.ItemFlag.ItemIsEditable)
            label_item.setToolTip("Double-click to rename")
            self._table.setItem(row, _COL_LABEL, label_item)

            # Time splits button — explicitly sized so it renders in-cell
            split_cell = QWidget()
            split_layout = QHBoxLayout(split_cell)
            split_layout.setContentsMargins(8, 6, 8, 6)
            split_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            split_btn = QPushButton("Time splits…")
            split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            split_btn.setMinimumHeight(28)
            split_btn.clicked.connect(
                lambda _checked=False, r=row: self._edit_splits(r)
            )
            split_layout.addWidget(split_btn)
            self._table.setCellWidget(row, _COL_SPLIT, split_cell)

    def _set_all_checked(self, checked: bool) -> None:
        for tick in self._row_ticks:
            tick.setChecked(checked)

    def _restore_suggestions(self) -> None:
        for tick, entry in zip(self._row_ticks, self._entries):
            tick.setChecked(entry.auto_suggested)

    def _edit_splits(self, row: int) -> None:
        name_item = self._table.item(row, _COL_NAME)
        label_item = self._table.item(row, _COL_LABEL)
        if name_item is None or label_item is None:
            return
        name = name_item.text()
        default_label = label_item.text().strip() or name
        dialog = TimeSplitDialog(
            name, default_label, self._row_splits.get(row, []), self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._row_splits[row] = dialog.splits()

    def _emit_start(self) -> None:
        picks: list[FolderPick] = []
        for row in range(self._table.rowCount()):
            tick = self._row_ticks[row] if row < len(self._row_ticks) else None
            if tick is None or not tick.isChecked():
                continue
            name_item = self._table.item(row, _COL_NAME)
            label_item = self._table.item(row, _COL_LABEL)
            if name_item is None or label_item is None:
                continue
            name = name_item.text()
            label = label_item.text().strip() or name
            picks.append(
                FolderPick(
                    name=name,
                    destination_label=label,
                    time_splits=list(self._row_splits.get(row, [])),
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
