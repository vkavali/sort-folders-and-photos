"""Global Qt stylesheet for a modern, clean, neat look."""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication


QSS = """
* {
    font-family: 'Segoe UI', 'SF Pro Text', 'Inter', 'Helvetica Neue', Arial, sans-serif;
    color: #0f172a;
}

QMainWindow, QDialog {
    background: #f5f6f8;
}
QStackedWidget > QWidget {
    background: transparent;
}

/* ---------- Sidebar ---------- */
QWidget[role="sidebar"] {
    background: #ffffff;
    border-right: 1px solid #eef0f3;
}
QLabel[role="brand"] {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.3px;
}
QLabel[role="tagline"] {
    color: #6b7280;
    font-size: 11px;
}
QWidget[role="stepItem"] {
    background: transparent;
}
QLabel[role="stepCircle"] {
    background: #f3f4f6;
    color: #9ca3af;
    border-radius: 14px;
    font-weight: 700;
    font-size: 12px;
    border: 1px solid #e5e7eb;
}
QLabel[role="stepCircle"][state="active"] {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #2563eb;
}
QLabel[role="stepCircle"][state="done"] {
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #bbf7d0;
}
QLabel[role="stepLabel"] {
    color: #6b7280;
    font-size: 13px;
    font-weight: 500;
}
QLabel[role="stepLabel"][state="active"] {
    color: #0f172a;
    font-weight: 600;
}
QLabel[role="stepLabel"][state="done"] {
    color: #0f172a;
    font-weight: 500;
}
QLabel[role="sidebarHint"] {
    color: #9ca3af;
    font-size: 11px;
    line-height: 1.4;
}

/* ---------- Headings ---------- */
QLabel[role="title"] {
    font-size: 26px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.4px;
}
QLabel[role="subtitle"] {
    color: #64748b;
    font-size: 13px;
}
QLabel[role="sectionTitle"] {
    font-weight: 600;
    color: #0f172a;
    font-size: 13px;
    letter-spacing: 0.3px;
}
QLabel#summaryTitle {
    font-size: 30px;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.5px;
}
QLabel[role="summaryStatNumber"] {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
}
QLabel[role="summaryStatLabel"] {
    color: #64748b;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.4px;
}

/* ---------- Cards ---------- */
QFrame[role="card"], QFrame#summaryPanel {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid #eef0f3;
}

/* ---------- Inputs ---------- */
QLineEdit, QDateTimeEdit {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #bfdbfe;
    font-size: 13px;
}
QLineEdit:focus, QDateTimeEdit:focus {
    border: 1px solid #2563eb;
}
QLineEdit:disabled {
    color: #9ca3af;
    background: #f3f4f6;
}

/* ---------- Buttons ---------- */
QPushButton {
    background: #ffffff;
    color: #111827;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: #f9fafb;
    border-color: #d1d5db;
}
QPushButton:pressed {
    background: #f3f4f6;
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

/* ---------- Segmented control ---------- */
QPushButton[role="segment"] {
    background: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
    border-radius: 0;
    padding: 9px 18px;
    font-weight: 500;
}
QPushButton[role="segment"][position="first"] {
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
}
QPushButton[role="segment"][position="last"] {
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
    border-left: none;
}
QPushButton[role="segment"][position="mid"] {
    border-left: none;
}
QPushButton[role="segment"][position="only"] {
    border-radius: 10px;
}
QPushButton[role="segment"]:hover {
    background: #f9fafb;
}
QPushButton[role="segment"]:checked {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
}
QPushButton[role="segment"]:checked:hover {
    background: #1d4ed8;
}

/* ---------- Drop zone ---------- */
QFrame[role="dropzone"] {
    background: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 14px;
    min-height: 96px;
}
QFrame[role="dropzone"][hover="true"] {
    border: 2px dashed #2563eb;
    background: #eff6ff;
}
QLabel[role="dropzoneCaption"] {
    color: #94a3b8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
}
QLabel[role="dropzonePath"] {
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
}
QLabel[role="dropzonePath"][filled="true"] {
    color: #0f172a;
}

/* ---------- Checkbox / radio ---------- */
QRadioButton, QCheckBox {
    spacing: 8px;
    color: #111827;
    padding: 4px 0;
    font-size: 13px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
QRadioButton::indicator:unchecked {
    border: 1.5px solid #cbd5e1;
    border-radius: 9px;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    border: 5px solid #2563eb;
    border-radius: 9px;
    background: #ffffff;
}
/* Native Fusion draws the checkmark for us when we don't fully override. */

/* ---------- TickButton (checkbox replacement in tables) ---------- */
QPushButton[role="tick"] {
    background: #ffffff;
    color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 6px;
    font-weight: 700;
    font-size: 13px;
    padding: 0;
}
QPushButton[role="tick"]:hover {
    border-color: #94a3b8;
}
QPushButton[role="tick"]:checked {
    background: #2563eb;
    border: 1.5px solid #2563eb;
    color: #ffffff;
}
QPushButton[role="tick"]:checked:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}

/* ---------- Tables ---------- */
QTableWidget, QTableView {
    background: #ffffff;
    border: 1px solid #eef0f3;
    border-radius: 12px;
    gridline-color: #f1f5f9;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
    alternate-background-color: #fafbfc;
}
QTableWidget::item, QTableView::item {
    padding: 10px 10px;
}
QHeaderView::section {
    background: #f9fafb;
    color: #64748b;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #eef0f3;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
QHeaderView::section:first {
    border-top-left-radius: 12px;
}
QHeaderView::section:last {
    border-top-right-radius: 12px;
}

/* ---------- Progress bar ---------- */
QProgressBar {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #eef2f7;
    height: 18px;
    text-align: center;
    color: #0f172a;
    font-size: 11px;
    font-weight: 600;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 10px;
}

/* ---------- Scrollbars ---------- */
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
QScrollBar::handle:vertical:hover { background: #9ca3af; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
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
QScrollBar::handle:horizontal:hover { background: #9ca3af; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ---------- Log panel ---------- */
QPlainTextEdit {
    background: #0b1220;
    color: #cbd5e1;
    border: 1px solid #0b1220;
    border-radius: 12px;
    font-family: 'Cascadia Mono', 'Consolas', 'SF Mono', 'Menlo', monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: #1d4ed8;
}

/* ---------- Status bar / tooltip ---------- */
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #eef0f3;
    color: #64748b;
    padding: 2px 8px;
    font-size: 11px;
}
QStatusBar::item { border: none; }
QToolTip {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 4px 6px;
    font-size: 11px;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    base_font = QFont()
    base_font.setFamily("Segoe UI")
    base_font.setPointSize(10)
    app.setFont(base_font)
    app.setStyleSheet(QSS)
