#!/usr/bin/env python
"""Точка входа приложения Converter."""

import shutil
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from converter.ui.main_window import MainWindow
from converter.ui.theme import STYLESHEET

ICON_PATH = Path(__file__).resolve().parent / "converter" / "ui" / "assets" / "icon.svg"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Converter")
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    # Совпадение с именем .desktop-файла — иконка в панели на Wayland.
    QGuiApplication.setDesktopFileName("converter")
    app.setStyleSheet(STYLESHEET)

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        QMessageBox.critical(
            None, "Converter",
            "Не найден ffmpeg. Установите его:\n\n  sudo pacman -S ffmpeg",
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
