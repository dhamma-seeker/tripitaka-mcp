"""
Tripitaka MCP Server — Database Backend Factory

เลือก database backend ตาม env var TRIPITAKA_BACKEND:
  - "postgres" (default) — hosted server, PostgreSQL + pgvector
  - "sqlite"             — local install, SQLite (ดู Dual-Backend Discipline
                           ใน CLAUDE.md)

หลักการ: PostgresBackend delegate ไปยัง db/connection.py เดิมทั้งหมด — pool
ไม่ถูก reimplement, SQL string ทำงาน as-is → Postgres path เหมือนเดิมเป๊ะ.
SqliteBackend อยู่ในไฟล์แยก db/sqlite_connection.py (import แบบ lazy).
"""

from __future__ import annotations

import os


class Backend:
    """Database backend interface.

    Tool code ใช้ pattern นี้แทนการเรียก get_connection() ตรงๆ:

        backend = get_backend()
        conn = backend.connect()
        try:
            cur = backend.cursor(conn)
            cur.execute(sql, params)
            rows = cur.fetchall()
        finally:
            cur.close()
            backend.release(conn)
    """

    name: str = ""

    def connect(self):
        """ดึง connection (Postgres: จาก pool / SQLite: เปิดไฟล์ db)."""
        raise NotImplementedError

    def cursor(self, conn):
        """คืน DB-API cursor จาก connection."""
        raise NotImplementedError

    def release(self, conn) -> None:
        """คืน connection (Postgres: กลับเข้า pool / SQLite: no-op)."""
        raise NotImplementedError


class PostgresBackend(Backend):
    """PostgreSQL backend — hosted server.

    Delegate ไปยัง db/connection.py เดิมทั้งหมด: pool, register_vector ฯลฯ
    ไม่ถูกแตะ. SQL string ที่ tool ส่งมา execute แบบ as-is.
    """

    name = "postgres"

    def connect(self):
        from db.connection import get_connection

        return get_connection()

    def cursor(self, conn):
        return conn.cursor()

    def release(self, conn) -> None:
        from db.connection import release_connection

        release_connection(conn)


_backend: Backend | None = None


def get_backend() -> Backend:
    """คืน Backend instance ตาม env TRIPITAKA_BACKEND (default "postgres").

    เป็น "ที่เดียว" ที่อ่าน env นี้ (Dual-Backend Discipline กฎข้อ 1).
    Singleton ต่อ process.
    """
    global _backend
    if _backend is None:
        name = os.getenv("TRIPITAKA_BACKEND", "postgres").strip().lower()
        if name == "postgres":
            _backend = PostgresBackend()
        elif name == "sqlite":
            # lazy import — hosted server ไม่โหลดโค้ด SQLite (กฎข้อ 5)
            from db.sqlite_connection import SqliteBackend

            _backend = SqliteBackend()
        else:
            raise RuntimeError(
                f"Unknown TRIPITAKA_BACKEND={name!r} — use 'postgres' or 'sqlite'"
            )
    return _backend
