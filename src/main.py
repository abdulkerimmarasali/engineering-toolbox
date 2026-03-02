import sys
from PyQt5.QtWidgets import QApplication

from src.app_shell import AppShell

def main():
    app = QApplication(sys.argv)
    w = AppShell()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
