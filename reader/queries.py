"""Read-only DB queries for the bilingual reader.

Reuses db.connection (same pool as MCP server). All queries are SELECT-only —
suitable for `tripitaka_ro` role in production.
"""

from __future__ import annotations

import re
from typing import Any

from db.connection import get_connection, release_connection


def _natural_key(s: str) -> list[Any]:
    """Sort key that orders dn1, dn2, ..., dn9, dn10, dn22 naturally.

    Splits the string at digit/non-digit boundaries and casts numeric
    chunks to int so "dn22" sorts after "dn9" instead of before it.
    Reason: section.sort_order in the DB was set inconsistently by old
    loaders (early-loaded rows all default to 0); we cannot rely on it.
    """
    return [int(c) if c.isdigit() else c for c in re.split(r"(\d+)", s)]


def fetch_sutta(sutta_id: str) -> dict[str, Any] | None:
    """ดึงข้อมูลสูตรเต็ม (metadata + ทุก segment Pāli + English) ตาม sutta_id.

    Returns None ถ้าไม่พบ.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                sec.id,
                sec.sutta_id,
                sec.title_pali,
                sec.title_english,
                n.code AS nikaya_code,
                n.name_pali AS nikaya_pali,
                n.name_english AS nikaya_english,
                p.code AS pitaka_code,
                p.name_pali AS pitaka_pali,
                p.name_english AS pitaka_english
            FROM section sec
            JOIN book b ON sec.book_id = b.id
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE sec.sutta_id = %s
            """,
            (sutta_id,),
        )
        section_row = cur.fetchone()
        if not section_row:
            return None

        section_id = section_row[0]

        cur.execute(
            """
            SELECT segment_id, text_pali, text_english
            FROM segment
            WHERE section_id = %s
            ORDER BY id
            """,
            (section_id,),
        )
        segments = [
            {"segment_id": r[0], "text_pali": r[1], "text_english": r[2]}
            for r in cur.fetchall()
        ]

        title_pali = section_row[2]
        title_english = section_row[3]
        if not title_pali or not title_english:
            for seg in segments:
                if seg["segment_id"].endswith(":0.2"):
                    title_pali = title_pali or seg["text_pali"]
                    title_english = title_english or seg["text_english"]
                    break

        return {
            "sutta_id": section_row[1],
            "title_pali": title_pali,
            "title_english": title_english,
            "nikaya": {
                "code": section_row[4],
                "name_pali": section_row[5],
                "name_english": section_row[6],
            },
            "pitaka": {
                "code": section_row[7],
                "name_pali": section_row[8],
                "name_english": section_row[9],
            },
            "segments": segments,
        }
    finally:
        cur.close()
        release_connection(conn)


def fetch_structure() -> list[dict[str, Any]]:
    """ดึงโครงสร้าง pitakas → nikayas พร้อม sutta count.

    Filter: เอาเฉพาะ nikāya ที่มี segments จริง — ตัด legacy placeholder
    nikāyas ที่มี section rows แต่ไม่มี segment data (เช่น `vin-v/vin-m/
    vin-c/vin-p` ที่เหลือจาก migration เก่าก่อน Phase B โหลด `pli-tv-*`).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                p.code AS pitaka_code,
                p.name_pali AS pitaka_pali,
                p.name_english AS pitaka_english,
                p.sort_order AS pitaka_sort,
                n.code AS nikaya_code,
                n.name_pali AS nikaya_pali,
                n.name_english AS nikaya_english,
                COUNT(DISTINCT CASE WHEN seg.id IS NOT NULL THEN sec.id END) AS sutta_count
            FROM pitaka p
            LEFT JOIN nikaya n ON n.pitaka_id = p.id
            LEFT JOIN book b ON b.nikaya_id = n.id
            LEFT JOIN section sec ON sec.book_id = b.id
            LEFT JOIN segment seg ON seg.section_id = sec.id
            GROUP BY p.id, p.code, p.name_pali, p.name_english, p.sort_order,
                     n.id, n.code, n.name_pali, n.name_english, n.sort_order
            HAVING COUNT(seg.id) > 0
            ORDER BY p.sort_order, n.sort_order
            """
        )
        rows = cur.fetchall()

        pitakas: dict[str, dict[str, Any]] = {}
        for r in rows:
            pcode = r[0]
            if pcode not in pitakas:
                pitakas[pcode] = {
                    "code": pcode,
                    "name_pali": r[1],
                    "name_english": r[2],
                    "sort": r[3],
                    "nikayas": [],
                }
            pitakas[pcode]["nikayas"].append(
                {
                    "code": r[4],
                    "name_pali": r[5],
                    "name_english": r[6],
                    "sutta_count": r[7],
                }
            )

        return sorted(pitakas.values(), key=lambda x: x["sort"])
    finally:
        cur.close()
        release_connection(conn)


def fetch_nikaya(nikaya_code: str) -> dict[str, Any] | None:
    """ดึง nikāya + รายชื่อ books + suttas ทั้งหมดในนิกาย.

    Returns None ถ้า nikaya_code ไม่มี (หรือไม่มี sutta).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                n.code, n.name_pali, n.name_english,
                p.code, p.name_pali, p.name_english
            FROM nikaya n
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE n.code = %s
            """,
            (nikaya_code,),
        )
        nrow = cur.fetchone()
        if not nrow:
            return None

        cur.execute(
            """
            SELECT
                b.code, b.name_pali, b.name_english, b.sort_order,
                sec.sutta_id, sec.title_pali, sec.title_english, sec.sort_order
            FROM book b
            LEFT JOIN section sec ON sec.book_id = b.id
            WHERE b.nikaya_id = (SELECT id FROM nikaya WHERE code = %s)
            ORDER BY b.sort_order, sec.sort_order
            """,
            (nikaya_code,),
        )
        rows = cur.fetchall()

        books: dict[str, dict[str, Any]] = {}
        for r in rows:
            book_code = r[0]
            if book_code not in books:
                books[book_code] = {
                    "code": book_code,
                    "name_pali": r[1],
                    "name_english": r[2],
                    "sort": r[3],
                    "suttas": [],
                }
            if r[4]:  # sutta_id (LEFT JOIN may produce null)
                books[book_code]["suttas"].append(
                    {
                        "sutta_id": r[4],
                        "title_pali": r[5],
                        "title_english": r[6],
                    }
                )

        # filter empty books, sort books by sort_order, then sort suttas
        # within each book by natural sutta_id order (sort_order in DB is
        # unreliable for sections — see _natural_key docstring)
        ordered_books = [b for b in books.values() if b["suttas"]]
        ordered_books.sort(key=lambda b: b["sort"])
        for b in ordered_books:
            b["suttas"].sort(key=lambda s: _natural_key(s["sutta_id"]))

        total = sum(len(b["suttas"]) for b in ordered_books)

        return {
            "code": nrow[0],
            "name_pali": nrow[1],
            "name_english": nrow[2],
            "pitaka": {
                "code": nrow[3],
                "name_pali": nrow[4],
                "name_english": nrow[5],
            },
            "books": ordered_books,
            "total_suttas": total,
        }
    finally:
        cur.close()
        release_connection(conn)
