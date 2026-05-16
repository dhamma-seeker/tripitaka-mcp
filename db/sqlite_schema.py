"""
Tripitaka MCP Server — SQLite Schema (local install)

SQLite equivalent ของ db/schema.py — ใช้ตอน build SQLite db ด้วย
scripts/build_sqlite_db.py. 7 ตารางเหมือน Postgres ยกเว้น:
  - SERIAL PRIMARY KEY        → INTEGER PRIMARY KEY
  - VARCHAR(n)                → TEXT
  - column `embedding` (pgvector) → ตัดทิ้ง (local mode ไม่มี semantic search)
  - GIN trigram index         → FTS5 virtual table แทน

ดู Dual-Backend Discipline ใน CLAUDE.md.
"""

from __future__ import annotations

import sqlite3

# FTS5 tokenizer — `remove_diacritics 2` ทำให้ค้นแบบไม่สนสระยาว/จุดบาลี
# (เช่นพิมพ์ "anapanassati" เจอ "ānāpānassati")
_FTS_TOKENIZE = "unicode61 remove_diacritics 2"

# 7 ตารางหลัก — โครงสร้างเทียบเท่า db/schema.py (Postgres)
_TABLES = """
CREATE TABLE pitaka (
    id           INTEGER PRIMARY KEY,
    code         TEXT UNIQUE NOT NULL,
    name_pali    TEXT NOT NULL,
    name_thai    TEXT NOT NULL,
    name_english TEXT NOT NULL,
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE nikaya (
    id           INTEGER PRIMARY KEY,
    pitaka_id    INTEGER NOT NULL REFERENCES pitaka(id) ON DELETE CASCADE,
    code         TEXT UNIQUE NOT NULL,
    name_pali    TEXT NOT NULL,
    name_thai    TEXT NOT NULL,
    name_english TEXT NOT NULL,
    sort_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE book (
    id            INTEGER PRIMARY KEY,
    nikaya_id     INTEGER NOT NULL REFERENCES nikaya(id) ON DELETE CASCADE,
    code          TEXT UNIQUE NOT NULL,
    name_pali     TEXT,
    name_thai     TEXT,
    name_english  TEXT,
    volume_number INTEGER,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE section (
    id            INTEGER PRIMARY KEY,
    book_id       INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
    sutta_id      TEXT UNIQUE NOT NULL,
    title_pali    TEXT,
    title_thai    TEXT,
    title_english TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE segment (
    id           INTEGER PRIMARY KEY,
    section_id   INTEGER NOT NULL REFERENCES section(id) ON DELETE CASCADE,
    segment_id   TEXT UNIQUE NOT NULL,
    text_pali    TEXT,
    text_thai    TEXT,
    text_english TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE translation (
    id         INTEGER PRIMARY KEY,
    segment_id INTEGER NOT NULL REFERENCES segment(id) ON DELETE CASCADE,
    language   TEXT NOT NULL,
    edition    TEXT NOT NULL,
    translator TEXT,
    text       TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (segment_id, language, edition)
);

CREATE TABLE dictionary (
    id         INTEGER PRIMARY KEY,
    word       TEXT NOT NULL,
    language   TEXT NOT NULL,
    text       TEXT NOT NULL,
    source     TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Index — เฉพาะ FK columns + lookup ที่ไม่มี UNIQUE ครอบ (UNIQUE สร้าง index ให้เอง)
_INDEXES = """
CREATE INDEX idx_segment_section_id ON segment(section_id);
CREATE INDEX idx_section_book_id ON section(book_id);
CREATE INDEX idx_book_nikaya_id ON book(nikaya_id);
CREATE INDEX idx_nikaya_pitaka_id ON nikaya(pitaka_id);
CREATE INDEX idx_translation_segment_id ON translation(segment_id);
CREATE INDEX idx_translation_lang_edition ON translation(language, edition);
CREATE INDEX idx_dictionary_word ON dictionary(word);
"""

# FTS5 virtual tables — แบบ external content (เก็บแค่ token ไม่ซ้ำ text)
# ใช้แทน pg_trgm GIN index สำหรับ keyword search
_FTS = f"""
CREATE VIRTUAL TABLE segment_fts USING fts5(
    text_pali, text_thai, text_english,
    content='segment', content_rowid='id',
    tokenize='{_FTS_TOKENIZE}'
);

CREATE VIRTUAL TABLE translation_fts USING fts5(
    text,
    content='translation', content_rowid='id',
    tokenize='{_FTS_TOKENIZE}'
);
"""


def create_sqlite_tables(conn: sqlite3.Connection) -> None:
    """สร้าง 7 ตาราง + index + FTS5 virtual table 2 ตัว ในไฟล์ SQLite ที่ว่าง.

    FTS5 ยังไม่ถูก populate — scripts/build_sqlite_db.py จะ INSERT ข้อมูลแล้ว
    สั่ง `INSERT INTO segment_fts(segment_fts) VALUES('rebuild')` ทีหลัง.
    """
    conn.executescript(_TABLES)
    conn.executescript(_INDEXES)
    conn.executescript(_FTS)
    conn.commit()


def rebuild_fts(conn: sqlite3.Connection) -> None:
    """Populate FTS5 index จากข้อมูลใน base table — เรียกหลัง INSERT เสร็จ."""
    conn.execute("INSERT INTO segment_fts(segment_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO translation_fts(translation_fts) VALUES('rebuild')")
    conn.commit()
