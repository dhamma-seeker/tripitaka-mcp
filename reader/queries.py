"""Read-only DB queries for the bilingual reader.

Reuses db.connection (same pool as MCP server). All queries are SELECT-only —
suitable for `tripitaka_ro` role in production.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from markupsafe import Markup, escape

from db.connection import get_connection, release_connection


def _strip_diacritics(text: str) -> str:
    """NFD-decompose then drop combining marks. Matches Postgres `f_unaccent`
    semantics closely enough for the highlighter (both lowercase + strip)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text or "")
        if not unicodedata.combining(c)
    ).lower()


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Lowercase + strip diacritics, but track which char in the result came
    from which original index. Lets the highlighter find a match in the
    normalized form, then slice the *original* text (with diacritics intact)
    at the matched range so user sees their search term in context."""
    out: list[str] = []
    idx_map: list[int] = []
    for orig_i, ch in enumerate(text or ""):
        nfd = unicodedata.normalize("NFD", ch)
        for c in nfd:
            if not unicodedata.combining(c):
                out.append(c.lower())
                idx_map.append(orig_i)
    return "".join(out), idx_map


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


def lookup_word(word: str) -> list[dict[str, Any]]:
    """Plain dictionary lookup for a single word. Returns one row per source.

    Backs the /read/api/word endpoint that powers the double-click tooltip.
    No context examples or lemma fallback (kept light — payload should be
    fast and small for tooltip latency).
    """
    w = (word or "").lower().strip()
    if not w or len(w) > 60:
        return []
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT source, language, text
            FROM dictionary
            WHERE word = %s
            ORDER BY source
            """,
            (w,),
        )
        return [
            {"source": r[0], "language": r[1], "text": r[2]}
            for r in cur.fetchall()
        ]
    finally:
        cur.close()
        release_connection(conn)


def fetch_neighbors(sutta_id: str) -> dict[str, dict[str, Any] | None]:
    """หาสูตรก่อน/ถัดไปในเล่มเดียวกัน (book) — เพื่อ prev/next nav.

    เรียงด้วย natural sort ของ `sutta_id` (เพราะ section.sort_order ไม่
    เชื่อถือได้สำหรับแถว early-loaded). Returns {"prev": {...}|None,
    "next": {...}|None}. None ถ้าเป็นต้นเล่มหรือท้ายเล่ม
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT sec2.sutta_id, sec2.title_pali, sec2.title_english
            FROM section sec1
            JOIN section sec2 ON sec1.book_id = sec2.book_id
            JOIN segment seg ON seg.section_id = sec2.id
            WHERE sec1.sutta_id = %s AND sec2.sutta_id != sec1.sutta_id
            GROUP BY sec2.sutta_id, sec2.title_pali, sec2.title_english
            HAVING COUNT(seg.id) > 0
            """,
            (sutta_id,),
        )
        siblings = [
            {"sutta_id": r[0], "title_pali": r[1], "title_english": r[2]}
            for r in cur.fetchall()
        ]
        if not siblings:
            return {"prev": None, "next": None}

        all_ids = sorted(
            [{"sutta_id": sutta_id}] + siblings,
            key=lambda s: _natural_key(s["sutta_id"]),
        )
        idx = next(
            (i for i, s in enumerate(all_ids) if s["sutta_id"] == sutta_id), -1
        )
        sibling_by_id = {s["sutta_id"]: s for s in siblings}
        prev_id = all_ids[idx - 1]["sutta_id"] if idx > 0 else None
        next_id = all_ids[idx + 1]["sutta_id"] if 0 <= idx < len(all_ids) - 1 else None
        return {
            "prev": sibling_by_id.get(prev_id) if prev_id else None,
            "next": sibling_by_id.get(next_id) if next_id else None,
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


def _highlight(text: str | None, query: str) -> Markup | None:
    """HTML-escape `text` and wrap diacritic-insensitive matches of `query` in <mark>.

    User types "kosambi" → highlights "kosambī" (with diacritics) in the
    rendered text. Walks the NFD-normalized form to find positions, then
    slices the original text via an index map so the visible highlight is
    the canonical-spelling substring, not the typed query.

    Returns Markup so Jinja renders the tags directly (escape happens here).
    """
    if not text:
        return None
    if not query:
        return Markup(escape(text))

    norm_text, idx_map = _normalize_with_map(text)
    norm_query = _strip_diacritics(query)
    if not norm_query:
        return Markup(escape(text))

    out: list[Markup | str] = []
    cursor_norm = 0
    cursor_orig = 0
    qlen = len(norm_query)
    while cursor_norm < len(norm_text):
        hit = norm_text.find(norm_query, cursor_norm)
        if hit < 0:
            out.append(escape(text[cursor_orig:]))
            break
        orig_start = idx_map[hit]
        orig_end = idx_map[hit + qlen - 1] + 1
        out.append(escape(text[cursor_orig:orig_start]))
        out.append(Markup("<mark>") + escape(text[orig_start:orig_end]) + Markup("</mark>"))
        cursor_norm = hit + qlen
        cursor_orig = orig_end
    return Markup("").join(out)


def search_text(query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Plain substring search on Pāli + English texts.

    Uses ILIKE which can leverage the existing pg_trgm GIN indexes
    (`idx_segment_text_pali_trgm`, `idx_segment_text_english_trgm`) when
    the pattern has enough characters. We require >=3 chars to keep
    queries reasonably indexable.

    Returns up to `limit` matched segments with sutta metadata + snippets
    that have <mark> tags around the matched substring (Markup-safe).
    """
    q = (query or "").strip()
    if len(q) < 3:
        return []
    # Send the diacritic-stripped form into f_unaccent(...) ILIKE — Postgres
    # function strips and lowercases the indexed text, so user typing
    # "kosambi" matches the canonical "kosambī" (and similar). Functional
    # GIN trigram index `idx_segment_pali_unaccent_trgm` covers this.
    pattern = f"%{_strip_diacritics(q)}%"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                sec.sutta_id,
                sec.title_pali,
                sec.title_english,
                n.code AS nikaya_code,
                n.name_pali AS nikaya_pali,
                seg.segment_id,
                seg.text_pali,
                seg.text_english,
                CASE
                    WHEN f_unaccent(seg.text_pali) ILIKE %s THEN 'pali'
                    ELSE 'english'
                END AS matched_lang
            FROM segment seg
            JOIN section sec ON sec.id = seg.section_id
            JOIN book b ON b.id = sec.book_id
            JOIN nikaya n ON n.id = b.nikaya_id
            WHERE f_unaccent(seg.text_pali) ILIKE %s
               OR f_unaccent(seg.text_english) ILIKE %s
            ORDER BY seg.id
            LIMIT %s
            """,
            (pattern, pattern, pattern, limit),
        )
        rows = cur.fetchall()
        return [
            {
                "sutta_id": r[0],
                "title_pali": r[1],
                "title_english": r[2],
                "nikaya_code": r[3],
                "nikaya_pali": r[4],
                "segment_id": r[5],
                "text_pali": _highlight(r[6], q),
                "text_english": _highlight(r[7], q),
                "matched_lang": r[8],
            }
            for r in rows
        ]
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
