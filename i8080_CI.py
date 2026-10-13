#!/usr/bin/env python3
"""i8080-5 CI - Intel 8080 emulator, debugger, and device interface."""
import os
import sys
from PySide6.QtWidgets import QApplication
from i8080_ci.main_window import MainWindow

def main():
    # PyInstaller: работать из каталога exe, чтобы внешние каталоги
    # profiles/ и roms/ находились рядом с исполняемым файлом
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(os.path.abspath(sys.executable)))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
