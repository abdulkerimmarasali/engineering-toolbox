# src/utils.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PyQt5.QtWidgets import QMessageBox


@dataclass
class CalcResult:
    values: Dict[str, float] = field(default_factory=dict)
    checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    info: Optional[str] = None


def to_float(text: str, field_name: str) -> float:
    """Strict numeric parse (accepts comma decimal)."""
    s = (text or "").strip().replace(",", ".")
    try:
        return float(s)
    except Exception as e:
        raise ValueError(f"{field_name} sayısal olmalıdır.") from e


def msg_error(parent, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)


def msg_info(parent, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)
