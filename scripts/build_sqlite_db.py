#!/usr/bin/env python3
"""
Build the local SQLite database from the production PostgreSQL.

อ่านข้อมูลทั้งหมดจาก Postgres (ผ่าน env DATABASE_URL) แล้วเขียนเป็นไฟล์ SQLite
ไฟล์เดียว — ตัด column `embedding` (pgvector) ทิ้ง เพราะ local mode ไม่มี semantic
search. ไฟล์ผลลัพธ์ใช้กับ `tripitaka-mcp` (local install) + upload ขึ้น HuggingFace.

เป็น maintainer tool — รันบนเครื่องที่มี Postgres + psycopg2 (ไม่ได้อยู่ใน pip package).

Usage:
    DATABASE_URL=... .venv/bin/python scripts/build_sqlite_db.py [--out tripitaka.db]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

# repo root เข้า sys.path เพื่อ import db.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.sqlite_schema import create_sqlite_tables, rebuild_fts

# (table, [columns ที่ copy]) — เรียงตาม FK dependency.
# segment ตัด embedding + created_at; translation/dictionary ตัด created_at
# (tools ไม่ใช้ created_at — ปล่อยให้ SQLite default เติมเอง)
_TABLE_COLUMNS = [
    ("pitaka", ["id", "code", "name_pali", "name_thai", "name_english", "sort_order"]),
    ("nikaya", ["id", "pitaka_id", "code", "name_pali", "name_thai", "name_english", "sort_order"]),
    ("book", ["id", "nikaya_id", "code", "name_pali", "name_thai", "name_english", "volume_number", "sort_order"]),
    ("section", ["id", "book_id", "sutta_id", "title_pali", "title_thai", "title_english", "sort_order"]),
    ("segment", ["id", "section_id", "segment_id", "text_pali", "text_thai", "text_english"]),
    ("translation", ["id", "segment_id", "language", "edition", "translator", "text"]),
    ("dictionary", ["id", "word", "language", "text", "source"]),
]

_BATCH = 5000


def main() -> int:
    ap = argparse.ArgumentParser(description="Build local SQLite db from Postgres")
    ap.add_argument("--out", default="tripitaka.db", help="output SQLite file path")
    args = ap.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1

    import psycopg2  # maintainer tool — psycopg2 พร้อมใช้บนเครื่องที่มี Postgres

    out = args.out
    if os.path.exists(out):
        os.remove(out)
        print(f"removed existing {out}")

    pg = psycopg2.connect(database_url)
    sl = sqlite3.connect(out)
    t0 = time.time()
    try:
        print("creating SQLite schema (7 tables + 2 FTS5)...")
        create_sqlite_tables(sl)

        for table, cols in _TABLE_COLUMNS:
            collist = ", ".join(cols)
            placeholders = ", ".join(["?"] * len(cols))
            pgcur = pg.cursor()
            pgcur.execute(f"SELECT {collist} FROM {table} ORDER BY id")
            n = 0
            while True:
                rows = pgcur.fetchmany(_BATCH)
                if not rows:
                    break
                sl.executemany(
                    f"INSERT INTO {table} ({collist}) VALUES ({placeholders})", rows
                )
                n += len(rows)
            pgcur.close()
            sl.commit()
            print(f"  {table:12s} {n:>9,} rows")

        print("building FTS5 index (rebuild)...")
        rebuild_fts(sl)

        print("ANALYZE + VACUUM...")
        sl.execute("ANALYZE")
        sl.commit()
        sl.execute("VACUUM")
    finally:
        pg.close()
        sl.close()

    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"\n✅ built {out} — {size_mb:.1f} MB in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
