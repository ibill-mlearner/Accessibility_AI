from __future__ import annotations

from datetime import datetime
import hashlib
import os
import sqlite3

from flask import g

from bootstrap_data import SCHEMA_SQL, SEED_SQL

DB_PATH = os.path.join(os.path.dirname(__file__), "access_v2.db")


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    conn.commit()
    conn.close()


def ensure_ready():
    if not os.path.exists(DB_PATH):
        init_db()
