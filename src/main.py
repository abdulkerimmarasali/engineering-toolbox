# src/main.py
import sys
from PyQt5.QtWidgets import QApplication

from app_shell import AppShell  # <-- noktasız (relative değil)

def main():
    app = QApplication(sys.argv)
    w = AppShell()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
