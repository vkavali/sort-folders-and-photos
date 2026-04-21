"""Global Qt stylesheet.

Applied once at QApplication start via apply_theme(). Targets a modern,
flat, slightly-rounded look that works on Windows, macOS and Linux
without relying on any third-party dependencies.
"""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication


QSS = """
* {
    font-family: 'Segoe UI', 'SF Pro Text', 'Inter', 'Helvetica Neue', Arial, sans-serif;
    color: #1f2937;
}

QMainWindow, QDialog {
    background: #f6f7fb;
}

QStackedWidget > QWidget {
    background: #f6f7fb;
}

/* Headings + body */
QLabel {
    color: #1f2937;
}
QLabel[role="title"] {
    font-size: 22px;
    font-weight: 600;
    color: #0f172a;
}
QLabel[role="subtitle"] {
    color: #475569;
    font-size: 13px;
}
QLabel[role="sectionTitle"] {
    font-weight: 600;
    color: #0f172a;
}
QLabel[role="mono"] {
    font-family: 'Cascadia Mono', 'Consolas', 'SF Mono', 'Menlo', monospace;
}
QLabel#summaryTitle {
    font-size: 26px;
    font-weight: 700;
    color: #0f172a;
}

/* Card-style panels */
QFrame[role="card"], QFrame#summaryPanel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
}

/* Inputs */
QLineEdit, QDateTimeEdit {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #bfdbfe;
}
QLineEdit:focus, QDateTimeEdit:focus {
    border: 1px solid #2563eb;
    background: #ffffff;
}
QLineEdit:disabled {
    color: #9ca3af;
    background: #f3f4f6;
}

/* Buttons */
QPushButton {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
}
QPushButton:pressed {
    background: #e5e7eb;
}
QPushButton:default {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
}
QPushButton:default:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
QPushButton:default:pressed {
    background: #1e40af;
}
QPushButton:disabled {
    color: #9ca3af;
    background: #f3f4f6;
    border-color: #e5e7eb;
}

/* Radio + checkbox */
QRadioButton, QCheckBox {
    spacing: 8px;
    color: #1f2937;
    padding: 4px 0;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QRadioButton::indicator:unchecked {
    border: 1.5px solid #9ca3af;
    border-radius: 8px;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    border: 1.5px solid #2563eb;
    border-radius: 8px;
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                                stop:0 #2563eb, stop:0.5 #2563eb,
                                stop:0.55 #ffffff, stop:1 #ffffff);
}
QCheckBox::indicator:unchecked {
    border: 1.5px solid #9ca3af;
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    border: 1.5px solid #2563eb;
    border-radius: 4px;
    background: #2563eb;
    image: none;
}

/* Tables */
QTableWidget, QTableView {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    gridline-color: #eef0f3;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}
QHeaderView::section {
    background: #f9fafb;
    color: #374151;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #e5e7eb;
    font-weight: 600;
}
QTableWidget::item, QTableView::item {
    padding: 6px 8px;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #eef2f7;
    height: 14px;
    text-align: center;
    color: #0f172a;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3b82f6, stop:1 #2563eb);
    border-radius: 8px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #d1d5db;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #9ca3af;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 4px;
}
QScrollBar::handle:horizontal {
    background: #d1d5db;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #9ca3af;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* Plain text log area */
QPlainTextEdit {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 10px;
    font-family: 'Cascadia Mono', 'Consolas', 'SF Mono', 'Menlo', monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #1d4ed8;
}

/* Status bar */
QStatusBar {
    background: #f3f4f6;
    border-top: 1px solid #e5e7eb;
    color: #4b5563;
    padding: 2px 8px;
}
QStatusBar::item {
    border: none;
}

/* Tooltip */
QToolTip {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 4px 6px;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    base_font = QFont()
    base_font.setFamily("Segoe UI")
    base_font.setPointSize(10)
    app.setFont(base_font)
    app.setStyleSheet(QSS)
