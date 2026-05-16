"""
Tripitaka MCP Server — Database Connection Management

จัดการ connection pool สำหรับ PostgreSQL + pgvector

NOTE: psycopg2 / pgvector ถูก import แบบ lazy (ในฟังก์ชัน) — ดู Dual-Backend
Discipline ใน CLAUDE.md กฎข้อ 5. ทำให้ local install (SQLite backend) import
โมดูลนี้ได้โดยไม่ต้องติดตั้ง psycopg2.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------------------------------
# Connection Pool
# --------------------------------------------------------------------------

_connection_pool: pool.ThreadedConnectionPool | None = None


def get_pool() -> pool.ThreadedConnectionPool:
    """สร้างหรือคืน connection pool

    Returns:
        ThreadedConnectionPool: connection pool สำหรับ PostgreSQL
    """
    global _connection_pool
    if _connection_pool is None:
        from psycopg2 import pool

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is required. "
                "Copy .env.example to .env and set a secure password."
            )
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url,
        )
    return _connection_pool


def get_connection():
    """ดึง connection จาก pool และลงทะเบียน pgvector

    Returns:
        connection: PostgreSQL connection ที่พร้อมใช้งาน pgvector

    Example:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            conn.commit()
        finally:
            release_connection(conn)
    """
    from pgvector.psycopg2 import register_vector

    p = get_pool()
    conn = p.getconn()
    register_vector(conn)
    return conn


def release_connection(conn) -> None:
    """คืน connection กลับสู่ pool

    Args:
        conn: PostgreSQL connection ที่ต้องการคืน
    """
    p = get_pool()
    p.putconn(conn)


def close_all() -> None:
    """ปิด connection pool ทั้งหมด — เรียกตอน shutdown"""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None
