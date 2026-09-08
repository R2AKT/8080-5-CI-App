#!/usr/bin/env python3
"""i8080-5 CI - Intel 8080 emulator, debugger, and device interface."""
import sys
from PySide6.QtWidgets import QApplication
from i8080_ci.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
