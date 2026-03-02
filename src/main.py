import os
import sys

# EXE ve normal çalıştırma için: src klasörünü sys.path'e ekle
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt5.QtWidgets import QApplication
from app_shell import AppShell  # artık bulunur

def main():
    app = QApplication(sys.argv)
    w = AppShell()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
