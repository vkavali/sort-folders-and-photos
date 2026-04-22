"""Folder picker: every unique folder name in the tree is tickable.

Ticked rows form the baseline routing. A global "Time-based routing"
button lets the user define EXIF-time windows that override the folder
label for any matching file, regardless of which folder it came from.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

from PyQt6.QtCore import QDateTime, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat
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
from app.engine.scanner import MediaItem
from app.ui.widgets import TickButton


_COL_USE = 0
_COL_NAME = 1
_COL_OCCUR = 2
_COL_FILES = 3
_COL_LABEL = 4


def _wrap_cell(widget: QWidget) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(0)
    layout.addWidget(widget)
    return container


class TimeRoutingDialog(QDialog):
    """Global EXIF-time routing windows.

    Windows apply across every ticked folder. A matching window overrides
    a file's folder-assigned destination label.
    """

    def __init__(
        self,
        splits: list[TimeSplit],
        scan_min: Optional[datetime] = None,
        scan_max: Optional[datetime] = None,
        total_files: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Time-based routing")
        self.resize(760, 440)
        self._scan_min = scan_min
        self._scan_max = scan_max
        self._total_files = total_files
        self._build_ui()
        if splits:
            for split in splits:
                self._add_row(split)
        elif scan_min is not None and scan_max is not None:
            self._add_row(
                TimeSplit(
                    start=scan_min,
                    end=scan_max + timedelta(minutes=1),
                    destination_label="Morning",
                )
            )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        lead = QLabel(
            "Define one or more time windows. Any file whose capture time "
            "falls inside a window is routed to that window's destination "
            "— regardless of which folder it came from. Files that don't "
            "match any window keep the folder-assigned destination."
        )
        lead.setProperty("role", "subtitle")
        lead.setWordWrap(True)
        layout.addWidget(lead)

        if self._scan_min is not None and self._scan_max is not None:
            count_txt = f"{self._total_files} file" + (
                "s" if self._total_files != 1 else ""
            )
            range_txt = (
                f"{self._scan_min.strftime('%Y-%m-%d %H:%M')}  →  "
                f"{self._scan_max.strftime('%Y-%m-%d %H:%M')}"
            )
            range_label = QLabel(
                f"Scan contains {count_txt}.   Capture range: {range_txt}"
            )
            range_label.setProperty("role", "subtitle")
            range_label.setStyleSheet("color: #0f172a; font-weight: 600;")
            layout.addWidget(range_label)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["Start (inclusive)", "End (exclusive)", "Destination label"]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(52)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add window")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(lambda: self._add_row())
        remove_btn = QPushButton("Remove selected")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn = QPushButton("Clear all")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self._table.setRowCount(0))
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_dt_edit(self, initial: Optional[datetime]) -> QDateTimeEdit:
        dt = QDateTimeEdit()
        dt.setDisplayFormat("yyyy-MM-dd  HH:mm")
        dt.setCalendarPopup(True)
        dt.setMinimumHeight(34)
        dt.setButtonSymbols(QDateTimeEdit.ButtonSymbols.UpDownArrows)
        cal = dt.calendarWidget()
        if cal is not None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#0f172a"))
            cal.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, fmt)
            cal.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, fmt)
        if initial is not None:
            dt.setDateTime(QDateTime(initial))
        elif self._scan_min is not None:
            dt.setDateTime(QDateTime(self._scan_min))
        else:
            dt.setDateTime(QDateTime.currentDateTime())
        return dt

    def _add_row(self, split: TimeSplit | None = None) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        start = self._make_dt_edit(split.start if split else self._scan_min)
        self._table.setCellWidget(row, 0, _wrap_cell(start))

        end_default = None
        if split and split.end is not None:
            end_default = split.end
        elif self._scan_max is not None:
            end_default = self._scan_max + timedelta(minutes=1)
        end = self._make_dt_edit(end_default)
        self._table.setCellWidget(row, 1, _wrap_cell(end))

        label = QLineEdit(split.destination_label if split else "Category")
        label.setMinimumHeight(34)
        self._table.setCellWidget(row, 2, _wrap_cell(label))

    def _remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self._table.selectedIndexes()}, reverse=True
        )
        for r in rows:
            self._table.removeRow(r)

    @staticmethod
    def _inner_widget(cell: QWidget | None):
        if cell is None:
            return None
        layout = cell.layout()
        if layout is None or layout.count() == 0:
            return None
        item = layout.itemAt(0)
        return item.widget() if item is not None else None

    def splits(self) -> list[TimeSplit]:
        result: list[TimeSplit] = []
        for row in range(self._table.rowCount()):
            start_widget = self._inner_widget(self._table.cellWidget(row, 0))
            end_widget = self._inner_widget(self._table.cellWidget(row, 1))
            label_widget = self._inner_widget(self._table.cellWidget(row, 2))
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
    # Emitted with (picks, time_splits).
    start_processing = pyqtSignal(list, list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[FolderEntry] = []
        self._items: list[MediaItem] = []
        self._scan_min: Optional[datetime] = None
        self._scan_max: Optional[datetime] = None
        self._row_ticks: list[TickButton] = []
        self._time_splits: list[TimeSplit] = []
        self._time_btn: QPushButton = QPushButton()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 32)
        layout.setSpacing(14)

        header = QLabel("Review discovered folders")
        header.setProperty("role", "title")
        sub = QLabel(
            "Every unique folder name in your source is listed below. Tick "
            "the ones to keep as categories; files route to the deepest "
            "ticked ancestor. Use Time-based routing to group files across "
            "all folders by capture time."
        )
        sub.setProperty("role", "subtitle")
        sub.setWordWrap(True)
        layout.addWidget(header)
        layout.addWidget(sub)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(
            ["Use", "Folder name", "Occurrences", "Photos", "Destination label"]
        )
        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(_COL_LABEL, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(_COL_USE, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_COL_USE, 72)
        header_view.setSectionResizeMode(
            _COL_OCCUR, QHeaderView.ResizeMode.ResizeToContents
        )
        header_view.setSectionResizeMode(
            _COL_FILES, QHeaderView.ResizeMode.ResizeToContents
        )
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

        self._time_btn = QPushButton("Time-based routing…")
        self._time_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._time_btn.clicked.connect(self._edit_time_splits)
        toolbar.addWidget(self._time_btn)

        toolbar.addStretch(1)
        start_btn = QPushButton("Start Processing")
        start_btn.setDefault(True)
        start_btn.setMinimumHeight(40)
        start_btn.setMinimumWidth(160)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.clicked.connect(self._emit_start)
        toolbar.addWidget(start_btn)
        layout.addLayout(toolbar)

        self._refresh_time_btn_label()

    def set_entries(
        self,
        entries: Iterable[FolderEntry],
        items: Iterable[MediaItem] | None = None,
    ) -> None:
        self._entries = list(entries)
        self._items = list(items) if items is not None else []
        self._scan_min, self._scan_max = self._scan_range(self._items)
        self._row_ticks.clear()
        self._time_splits.clear()
        self._refresh_table()
        self._refresh_time_btn_label()

    @staticmethod
    def _scan_range(
        items: list[MediaItem],
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        ts = [i.mtime_ts for i in items if i.mtime_ts > 0]
        if not ts:
            return None, None
        return datetime.fromtimestamp(min(ts)), datetime.fromtimestamp(max(ts))

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        self._row_ticks.clear()
        for entry in self._entries:
            row = self._table.rowCount()
            self._table.insertRow(row)

            tick_cell = QWidget()
            tick_layout = QHBoxLayout(tick_cell)
            tick_layout.setContentsMargins(0, 0, 0, 0)
            tick_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tick = TickButton()
            tick.setChecked(entry.auto_suggested)
            tick_layout.addWidget(tick)
            self._table.setCellWidget(row, _COL_USE, tick_cell)
            self._row_ticks.append(tick)

            name_item = QTableWidgetItem(entry.name)
            name_item.setFlags(
                (name_item.flags() | Qt.ItemFlag.ItemIsEnabled)
                & ~Qt.ItemFlag.ItemIsEditable
            )
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

            label_item = QTableWidgetItem(entry.name)
            label_item.setFlags(label_item.flags() | Qt.ItemFlag.ItemIsEditable)
            label_item.setToolTip("Double-click to rename")
            self._table.setItem(row, _COL_LABEL, label_item)

    def _refresh_time_btn_label(self) -> None:
        n = len(self._time_splits)
        if n == 0:
            self._time_btn.setText("Time-based routing…")
        else:
            self._time_btn.setText(
                f"Time-based routing  ·  {n} window" + ("s" if n != 1 else "")
            )

    def _edit_time_splits(self) -> None:
        dialog = TimeRoutingDialog(
            splits=self._time_splits,
            scan_min=self._scan_min,
            scan_max=self._scan_max,
            total_files=len(self._items),
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._time_splits = dialog.splits()
            self._refresh_time_btn_label()

    def _set_all_checked(self, checked: bool) -> None:
        for tick in self._row_ticks:
            tick.setChecked(checked)

    def _restore_suggestions(self) -> None:
        for tick, entry in zip(self._row_ticks, self._entries):
            tick.setChecked(entry.auto_suggested)

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
            picks.append(FolderPick(name=name, destination_label=label))
        if not picks:
            QMessageBox.information(
                self,
                "No folders picked",
                "Tick at least one folder to route files into, or go back "
                "and choose Flatten All.",
            )
            return
        self.start_processing.emit(picks, list(self._time_splits))
