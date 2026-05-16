"""
Tripitaka MCP Server — SQLite Backend (local install)

ใช้เมื่อ TRIPITAKA_BACKEND=sqlite. database เป็นไฟล์เดียว เปิดแบบ read-only
(ไฟล์ที่ ship มาเป็น immutable). ไม่มี connection pool — stdio MCP = client เดียว,
แต่ละ tool call เปิด/ปิด connection เอง (sqlite3 connection ผูกกับ thread).

ดู Dual-Backend Discipline ใน CLAUDE.md.
"""

from __future__ import annotations

import os
import sqlite3

from db.backend import Backend


def resolve_db_path() -> str:
    """หา path ของไฟล์ SQLite db.

    ลำดับ: env TRIPITAKA_DB_PATH → platformdirs user-data dir → ~/.tripitaka-mcp/.
    `tripitaka-mcp init` จะดาวน์โหลดไฟล์ไปวางที่ default path.
    """
    path = os.getenv("TRIPITAKA_DB_PATH")
    if path:
        return os.path.expanduser(path)
    try:
        from platformdirs import user_data_dir

        base = user_data_dir("tripitaka-mcp")
    except ImportError:
        base = os.path.join(os.path.expanduser("~"), ".tripitaka-mcp")
    return os.path.join(base, "tripitaka.db")


class _TranslatingCursor:
    """ห่อ sqlite3 cursor — แปลง placeholder `%s` (psycopg2 pyformat) → `?`
    (sqlite qmark) อัตโนมัติตอน execute.

    ปลอดภัยเพราะ tool ที่ใช้ positional `%s` ไม่มี `%(name)s`, `%%`, หรือ literal
    `%` ใน SQL string (ตรวจแล้ว — wildcard ของ LIKE อยู่ใน params ไม่ใช่ SQL).
    tool ที่มีกิ่ง SQLite แยก (search_by_keyword, get_word_definition) เขียน SQL
    ด้วย `?` อยู่แล้ว → ไม่มี `%s` ให้แปลง = no-op.
    """

    def __init__(self, cur: sqlite3.Cursor):
        self._cur = cur

    def execute(self, sql, params=None):
        sql = sql.replace("%s", "?")
        if params is None:
            return self._cur.execute(sql)
        return self._cur.execute(sql, params)

    def __getattr__(self, name):
        # fetchall / fetchone / description / close / rowcount ... → ส่งต่อ cursor จริง
        return getattr(self._cur, name)


class SqliteBackend(Backend):
    """SQLite backend — local install. ไฟล์เดียว, read-only, ไม่มี pool."""

    name = "sqlite"

    def __init__(self):
        self._db_path = resolve_db_path()

    def connect(self):
        if not os.path.exists(self._db_path):
            raise RuntimeError(
                f"SQLite database not found at {self._db_path}. "
                "Run `tripitaka-mcp init` to download it first."
            )
        # mode=ro — ไฟล์ที่ ship มาเป็น immutable
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def cursor(self, conn):
        return _TranslatingCursor(conn.cursor())

    def release(self, conn) -> None:
        conn.close()
