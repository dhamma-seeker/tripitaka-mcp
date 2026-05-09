"""Read-only DB queries for the bilingual reader.

Reuses db.connection (same pool as MCP server). All queries are SELECT-only —
suitable for `tripitaka_ro` role in production.
"""

from __future__ import annotations

from typing import Any

from db.connection import get_connection, release_connection


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
