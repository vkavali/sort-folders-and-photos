"""Semantic File Aggregator — application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Semantic File Aggregator")
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
