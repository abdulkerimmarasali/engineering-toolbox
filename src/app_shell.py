# src/app_shell.py
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame
)

from .routes import CATEGORIES


@dataclass(frozen=True)
class ModuleSpec:
    display_name: str
    import_path: str
    class_name: str


class HeaderBar(QFrame):
    """Simple header with back button (optional) and title."""
    def __init__(self, title: str, on_back=None):
        super().__init__()
        self.setObjectName("HeaderBar")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)

        self.btn_back = QPushButton("← Geri")
        self.btn_back.setVisible(on_back is not None)
        if on_back is not None:
            self.btn_back.clicked.connect(on_back)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("HeaderTitle")

        lay.addWidget(self.btn_back, 0, Qt.AlignLeft)
        lay.addWidget(self.lbl_title, 1, Qt.AlignLeft)
        lay.addStretch(1)


class MenuScreen(QWidget):
    """Top-level categories."""
    def __init__(self, on_open_category):
        super().__init__()
        self._on_open_category = on_open_category

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(HeaderBar("Ana Menü"))

        hint = QLabel("Bir kategori seçin.")
        hint.setObjectName("Hint")
        root.addWidget(hint)

        self.list = QListWidget()
        for cat in CATEGORIES.keys():
            self.list.addItem(cat)
        self.list.itemClicked.connect(self._clicked)

        root.addWidget(self.list, 1)

    def _clicked(self, item: QListWidgetItem):
        self._on_open_category(item.text())


class ModuleListScreen(QWidget):
    """List modules under a category."""
    def __init__(self, on_back, on_open_module):
        super().__init__()
        self._on_back = on_back
        self._on_open_module = on_open_module
        self._category: Optional[str] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.header = HeaderBar("Modüller", on_back=self._on_back)
        root.addWidget(self.header)

        self.lbl = QLabel("")
        self.lbl.setObjectName("Hint")
        root.addWidget(self.lbl)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._clicked)
        root.addWidget(self.list, 1)

    def set_category(self, category: str):
        self._category = category
        self.header.lbl_title.setText(category)
        self.lbl.setText("Bir modül seçin.")
        self.list.clear()

        for display_name, import_path, class_name in CATEGORIES.get(category, []):
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, ModuleSpec(display_name, import_path, class_name))
            self.list.addItem(item)

    def _clicked(self, item: QListWidgetItem):
        spec: ModuleSpec = item.data(Qt.UserRole)
        self._on_open_module(spec)


class ModuleHostScreen(QWidget):
    """Hosts a selected module widget + back button."""
    def __init__(self, on_back):
        super().__init__()
        self._on_back = on_back
        self._current: Optional[QWidget] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.header = HeaderBar("Modül", on_back=self._on_back)
        root.addWidget(self.header)

        self.body = QFrame()
        self.body.setObjectName("ModuleBody")
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(12, 12, 12, 12)
        self.body_lay.setSpacing(10)
        root.addWidget(self.body, 1)

    def load_module(self, spec: ModuleSpec):
        self.header.lbl_title.setText(spec.display_name)

        # clear old
        if self._current is not None:
            self._current.setParent(None)
            self._current.deleteLater()
            self._current = None

        # dynamic import
        module = importlib.import_module(spec.import_path)
        cls = getattr(module, spec.class_name)

        # allow modules to accept an optional back callback (recommended)
        try:
            widget = cls(on_back=self._on_back)
        except TypeError:
            widget = cls()

        self._current = widget
        self.body_lay.addWidget(widget)


class AppShell(QMainWindow):
    """Navigation: Menu -> Module List -> Module Screen, each with a simple Back."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engineering Toolbox")
        self.setMinimumSize(1100, 750)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.menu = MenuScreen(on_open_category=self.open_category)
        self.mod_list = ModuleListScreen(on_back=self.back_to_menu, on_open_module=self.open_module)
        self.mod_host = ModuleHostScreen(on_back=self.back_to_category)

        self.stack.addWidget(self.menu)      # index 0
        self.stack.addWidget(self.mod_list)  # index 1
        self.stack.addWidget(self.mod_host)  # index 2

        self.stack.setCurrentIndex(0)
        self._current_category: Optional[str] = None

        self._apply_basic_style()

    def _apply_basic_style(self):
        # Minimal clean style (can be moved to assets/theme.qss later)
        self.setStyleSheet("""
            QMainWindow { background: #f3f4f6; }
            QFrame#HeaderBar { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }
            QLabel#HeaderTitle { font-size: 16px; font-weight: 700; color: #111827; }
            QLabel#Hint { color: #374151; }
            QFrame#ModuleBody { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }
            QListWidget { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 6px; }
            QPushButton { padding: 8px 12px; border-radius: 8px; border: 1px solid #e5e7eb; background: #ffffff; }
            QPushButton:hover { background: #f9fafb; }
        """)

    # ---- navigation ----

    def open_category(self, category: str):
        self._current_category = category
        self.mod_list.set_category(category)
        self.stack.setCurrentWidget(self.mod_list)

    def open_module(self, spec: ModuleSpec):
        self.mod_host.load_module(spec)
        self.stack.setCurrentWidget(self.mod_host)

    def back_to_menu(self):
        self._current_category = None
        self.stack.setCurrentWidget(self.menu)

    def back_to_category(self):
        if self._current_category is None:
            self.back_to_menu()
            return
        self.stack.setCurrentWidget(self.mod_list)
