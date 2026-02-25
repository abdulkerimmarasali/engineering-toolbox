# src/main.py
import sys
from PyQt5.QtWidgets import QApplication

from .app_shell import AppShell


def main() -> None:
    app = QApplication(sys.argv)
    win = AppShell()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
