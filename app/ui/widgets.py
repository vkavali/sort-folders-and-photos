"""Reusable UI widgets shaping the app's modern visual language."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def attach_shadow(
    widget: QWidget,
    *,
    blur: int = 28,
    y_offset: int = 6,
    alpha: int = 22,
) -> None:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, y_offset)
    eff.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(eff)


def _repolish(*widgets: QWidget) -> None:
    for w in widgets:
        w.style().unpolish(w)
        w.style().polish(w)


class Card(QFrame):
    """Rounded white panel with a soft drop shadow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        attach_shadow(self)


class SegmentedControl(QWidget):
    """iOS-style exclusive segmented control.

    options is a list of (key, label) tuples; emits changed(key).
    """

    changed = pyqtSignal(str)

    def __init__(
        self,
        options: list[tuple[str, str]],
        default: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "segmented")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        last = len(options) - 1
        for i, (key, label) in enumerate(options):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("role", "segment")
            btn.setProperty(
                "position",
                "only" if len(options) == 1
                else "first" if i == 0
                else "last" if i == last
                else "mid",
            )
            btn.clicked.connect(lambda _c=False, k=key: self._select(k))
            self._buttons[key] = btn
            self._group.addButton(btn)
            row.addWidget(btn, stretch=1)
        if default is None and options:
            default = options[0][0]
        if default is not None:
            self.set_value(default)

    def _select(self, key: str) -> None:
        if key in self._buttons:
            self._buttons[key].setChecked(True)
            self.changed.emit(key)

    def set_value(self, key: str) -> None:
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)

    def value(self) -> str:
        for k, b in self._buttons.items():
            if b.isChecked():
                return k
        return ""


class DropZone(QFrame):
    """Large dashed drop zone accepting a folder drag-and-drop or click."""

    path_changed = pyqtSignal(str)

    _PLACEHOLDER = "Drop a folder here  ·  or click to browse"

    def __init__(self, caption: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "dropzone")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._caption_text = caption
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(4)
        self._caption = QLabel(caption.upper())
        self._caption.setProperty("role", "dropzoneCaption")
        self._path = QLabel(self._PLACEHOLDER)
        self._path.setProperty("role", "dropzonePath")
        self._path.setWordWrap(True)
        layout.addWidget(self._caption)
        layout.addWidget(self._path)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            path = QFileDialog.getExistingDirectory(
                self, f"Select {self._caption_text.lower()} folder"
            )
            if path:
                self.set_path(path)
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if any(u.isLocalFile() for u in urls):
            event.acceptProposedAction()
            self.setProperty("hover", True)
            _repolish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("hover", False)
        _repolish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("hover", False)
        _repolish(self)
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())
            if p.is_dir():
                self.set_path(str(p))
                event.acceptProposedAction()
                return
        event.ignore()

    def set_path(self, path: str) -> None:
        self._path.setText(path if path else self._PLACEHOLDER)
        self._path.setProperty("filled", bool(path))
        _repolish(self._path)
        self.path_changed.emit(path)

    def path(self) -> str:
        text = self._path.text()
        return "" if text == self._PLACEHOLDER else text


class _StepperItem(QWidget):
    def __init__(self, number: int, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "stepItem")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 6, 0, 6)
        row.setSpacing(12)
        self._circle = QLabel(str(number))
        self._circle.setFixedSize(28, 28)
        self._circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._circle.setProperty("role", "stepCircle")
        self._label = QLabel(label)
        self._label.setProperty("role", "stepLabel")
        row.addWidget(self._circle)
        row.addWidget(self._label, stretch=1)
        self.set_state("pending")

    def set_state(self, state: str) -> None:
        self.setProperty("state", state)
        self._circle.setProperty("state", state)
        self._label.setProperty("state", state)
        _repolish(self, self._circle, self._label)


class Sidebar(QWidget):
    """Left-hand vertical stepper with brand lockup."""

    def __init__(self, steps: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setProperty("role", "sidebar")
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 30, 24, 24)
        layout.setSpacing(4)

        brand = QLabel("Aggregator")
        brand.setProperty("role", "brand")
        layout.addWidget(brand)
        tagline = QLabel("Flatten & sort, losslessly.")
        tagline.setProperty("role", "tagline")
        layout.addWidget(tagline)
        layout.addSpacing(28)

        self._items: list[_StepperItem] = []
        for i, label in enumerate(steps, start=1):
            item = _StepperItem(i, label)
            self._items.append(item)
            layout.addWidget(item)

        layout.addStretch(1)
        hint = QLabel("Originals are preserved by default.\nDuplicates are isolated, not dropped.")
        hint.setProperty("role", "sidebarHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        if self._items:
            self._items[0].set_state("active")

    def set_current(self, index: int) -> None:
        for i, item in enumerate(self._items):
            if i < index:
                item.set_state("done")
            elif i == index:
                item.set_state("active")
            else:
                item.set_state("pending")
