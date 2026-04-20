"""Cluster review page: table with editable labels, drag-drop merge, merge button."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import SIMILARITY_MAX, SIMILARITY_MIN
from app.engine.clusterer import Cluster


class _ClusterTable(QTableWidget):
    """Table with drag-and-drop row merging.

    Dragging row A onto row B merges A into B (B's label survives).
    """

    rows_merged = pyqtSignal(int, int)  # dragged_cluster_id, target_cluster_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(
            ["Cluster Label", "Members", "File Count", "Avg Similarity"]
        )
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        src_row = self.currentRow()
        target_row = self.rowAt(event.position().toPoint().y())
        if src_row < 0 or target_row < 0 or src_row == target_row:
            event.ignore()
            return
        src_id_item = self.item(src_row, 0)
        tgt_id_item = self.item(target_row, 0)
        if src_id_item is None or tgt_id_item is None:
            event.ignore()
            return
        src_id = src_id_item.data(Qt.ItemDataRole.UserRole)
        tgt_id = tgt_id_item.data(Qt.ItemDataRole.UserRole)
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        if isinstance(src_id, int) and isinstance(tgt_id, int):
            self.rows_merged.emit(src_id, tgt_id)


class MappingPage(QWidget):
    start_processing = pyqtSignal(dict)         # folder_name -> category_label
    recluster_requested = pyqtSignal(float)     # new threshold
    merge_requested = pyqtSignal(list, object)  # list[ids], target_id | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._clusters: list[Cluster] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Review discovered categories")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        sub = QLabel(
            "Edit any cluster label inline. Select 2+ rows and click Merge, "
            "or drag one row onto another to merge it in. Adjust the "
            "similarity threshold and click Re-cluster to regroup."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #555;")
        layout.addWidget(header)
        layout.addWidget(sub)

        self._table = _ClusterTable()
        self._table.rows_merged.connect(self._on_rows_merged)
        layout.addWidget(self._table, stretch=1)

        toolbar = QHBoxLayout()
        self._merge_btn = QPushButton("Merge Selected")
        self._merge_btn.clicked.connect(self._on_merge_clicked)
        toolbar.addWidget(self._merge_btn)

        toolbar.addSpacing(16)
        toolbar.addWidget(QLabel("Re-cluster at"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(int(SIMILARITY_MIN), int(SIMILARITY_MAX))
        self._slider.setFixedWidth(160)
        self._slider_value = QLabel("")
        self._slider.valueChanged.connect(
            lambda v: self._slider_value.setText(str(v))
        )
        toolbar.addWidget(self._slider)
        toolbar.addWidget(self._slider_value)
        recluster_btn = QPushButton("Re-cluster")
        recluster_btn.clicked.connect(
            lambda: self.recluster_requested.emit(float(self._slider.value()))
        )
        toolbar.addWidget(recluster_btn)

        toolbar.addStretch(1)
        start_btn = QPushButton("Start Processing")
        start_btn.setDefault(True)
        start_btn.setMinimumHeight(34)
        start_btn.clicked.connect(self._emit_start)
        toolbar.addWidget(start_btn)

        layout.addLayout(toolbar)

    def set_clusters(self, clusters: Iterable[Cluster], threshold: float) -> None:
        self._clusters = list(clusters)
        self._slider.setValue(int(threshold))
        self._slider_value.setText(str(int(threshold)))
        self._refresh_table()

    def _refresh_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for cluster in self._clusters:
            row = self._table.rowCount()
            self._table.insertRow(row)

            label_item = QTableWidgetItem(cluster.label)
            label_item.setData(Qt.ItemDataRole.UserRole, cluster.id)
            label_item.setFlags(
                label_item.flags() | Qt.ItemFlag.ItemIsEditable
            )

            members_item = QTableWidgetItem(", ".join(cluster.members))
            members_item.setFlags(
                members_item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            members_item.setToolTip("\n".join(cluster.members))

            count_item = QTableWidgetItem(str(cluster.file_count))
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            sim_item = QTableWidgetItem(f"{cluster.avg_internal_similarity:.1f}")
            sim_item.setFlags(sim_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            sim_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self._table.setItem(row, 0, label_item)
            self._table.setItem(row, 1, members_item)
            self._table.setItem(row, 2, count_item)
            self._table.setItem(row, 3, sim_item)
        self._table.blockSignals(False)

    def _selected_cluster_ids(self) -> list[int]:
        ids: list[int] = []
        seen: set[int] = set()
        for idx in self._table.selectedIndexes():
            row = idx.row()
            if row in seen:
                continue
            seen.add(row)
            item = self._table.item(row, 0)
            if item is not None:
                cid = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(cid, int):
                    ids.append(cid)
        return ids

    def _on_merge_clicked(self) -> None:
        ids = self._selected_cluster_ids()
        if len(ids) < 2:
            QMessageBox.information(
                self,
                "Select at least two clusters",
                "Highlight two or more rows to merge. The label of the "
                "first-selected (top-most) row will survive.",
            )
            return
        self.merge_requested.emit(ids, None)

    def _on_rows_merged(self, dragged_id: int, target_id: int) -> None:
        self.merge_requested.emit([target_id, dragged_id], target_id)

    def _collect_mapping(self) -> dict[str, str]:
        """Return final folder→label mapping from the current table state."""
        mapping: dict[str, str] = {}
        for row in range(self._table.rowCount()):
            label_item = self._table.item(row, 0)
            if label_item is None:
                continue
            label = label_item.text().strip() or f"Cluster_{row + 1}"
            cid = label_item.data(Qt.ItemDataRole.UserRole)
            cluster = next((c for c in self._clusters if c.id == cid), None)
            if cluster is None:
                continue
            for member in cluster.members:
                mapping[member] = label
        return mapping

    def _emit_start(self) -> None:
        self.start_processing.emit(self._collect_mapping())
