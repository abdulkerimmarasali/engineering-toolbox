# src/db.py
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, List, Optional, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sstm_veritabani.db"


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    return con


def fetch_all(query: str, params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
    with connect() as con:
        cur = con.cursor()
        cur.execute(query, params)
        return cur.fetchall()


def fetch_one(query: str, params: Tuple[Any, ...] = ()) -> Optional[Tuple[Any, ...]]:
    with connect() as con:
        cur = con.cursor()
        cur.execute(query, params)
        return cur.fetchone()


def get_oring_w_list() -> List[float]:
    rows = fetch_all("SELECT W FROM oring_W_tol")
    return [float(r[0]) for r in rows]


def get_civata_designations() -> List[str]:
    rows = fetch_all("SELECT Designation FROM civata")
    return [str(r[0]) for r in rows]
