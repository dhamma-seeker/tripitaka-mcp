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


# Pāli noun inflection table — covers common case endings only (no verbs,
# no compounds, no sandhi). Each entry: (suffix, stem_vowel, case_label).
# Sorted longest-suffix-first at module load to ensure the longest match wins
# during ranking (e.g. `dhammānaṃ` strips `-ānaṃ` not `-ā`).
#
# Coverage rationale: ~70-80% of inflected nouns in canonical Pāli use these
# 18 forms. Verbs, past participles (-ita/-ta), and compounds intentionally
# excluded — they'd produce more false positives than they'd resolve. The
# `try the stem` UX hint in the popup still catches what this table misses.
_PALI_INFLECTIONS: list[tuple[str, str, str]] = sorted(
    [
        # (suffix, stem_vowel, case_label) — case_label is shown in the popup
        ("ānaṃ", "a", "gen./dat. pl."),
        ("āsu",  "ā", "loc. pl. (f.)"),
        ("assa", "a", "gen./dat. sg."),
        ("āhi",  "ā", "inst./abl. pl. (f.)"),
        ("āya",  "ā", "dat./gen. sg. (f.)"),
        ("āyaṃ", "ā", "loc. sg. (f.)"),
        ("āyo",  "ā", "nom./acc. pl. (f.)"),
        ("ehi",  "a", "inst./abl. pl."),
        ("esu",  "a", "loc. pl."),
        ("ena",  "a", "inst. sg."),
        ("iyā",  "i", "inst./gen. sg. (f.)"),
        ("iyo",  "i", "nom./acc. pl. (f.)"),
        ("īhi",  "ī", "inst./abl. pl. (f.)"),
        ("īnaṃ", "ī", "gen./dat. pl. (f.)"),
        ("īsu",  "ī", "loc. pl. (f.)"),
        ("aṃ",   "a", "acc. sg."),
        ("ā",    "a", "nom. pl. / inst. sg."),
        ("e",    "a", "loc. sg. / nom. pl."),
        ("o",    "a", "nom. sg."),
    ],
    key=lambda x: -len(x[0]),
)


# bilara-data uses `ṁ` (U+1E41, dot-above) for anusvara; the dictionary
# table inherits multiple sources and stores `ṃ` (U+1E43, dot-below).
# Normalise the dot-above variant to dot-below at every entry point so the
# user can dblclick text from either tradition and still hit the DB.
def _normalize_pali(word: str) -> str:
    return (word or "").replace("ṁ", "ṃ")


def _candidate_lemmas(word: str) -> list[tuple[str, str, str]]:
    """Generate plausible lemmas for an inflected word, ranked longest-suffix-first.

    Each returned tuple is (lemma, suffix, case_label). Caller queries the
    DB once for `word IN (lemmas)` then picks the longest-suffix match from
    the rows it gets back. Minimum stem length of 2 chars to avoid generating
    single-letter false positives like stripping `o` from `do`.
    """
    out: list[tuple[str, str, str]] = []
    for suffix, stem_vowel, case_label in _PALI_INFLECTIONS:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            lemma = word[: -len(suffix)] + stem_vowel
            out.append((lemma, suffix, case_label))
    return out


def lookup_word(word: str) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
    """Dictionary lookup with rule-based Pāli noun-lemma fallback.

    Returns (definitions, lemma_info). `lemma_info` is None on exact match
    or no-match; populated when fallback resolved an inflected form.
    Backs the /read/api/word endpoint that powers the double-click tooltip.
    """
    w = _normalize_pali((word or "").lower().strip())
    if not w or len(w) > 60:
        return [], None

    conn = get_connection()
    try:
        cur = conn.cursor()

        # 1. Exact match — fast path, identical cost to the pre-fallback impl
        cur.execute(
            """
            SELECT source, language, text
            FROM dictionary
            WHERE word = %s
            ORDER BY source
            """,
            (w,),
        )
        rows = cur.fetchall()
        if rows:
            return (
                [{"source": r[0], "language": r[1], "text": r[2]} for r in rows],
                None,
            )

        # 2. Lemma fallback — generate candidate stems, query in one shot
        candidates = _candidate_lemmas(w)
        if not candidates:
            return [], None

        # ANY(%s) uses the same b-tree idx_dictionary_word as exact match;
        # PG turns this into a bitmap-OR of index scans — ~1ms even with
        # ~15 candidates. One round-trip, no per-candidate latency cost.
        lemma_list = [c[0] for c in candidates]
        cur.execute(
            """
            SELECT word, source, language, text
            FROM dictionary
            WHERE word = ANY(%s)
            ORDER BY source
            """,
            (lemma_list,),
        )
        matched_rows = cur.fetchall()
        if not matched_rows:
            return [], None

        # Pick the longest-suffix candidate that actually has rows.
        # `candidates` is already sorted longest-first via _PALI_INFLECTIONS.
        matched_lemmas = {r[0] for r in matched_rows}
        for lemma, suffix, case_label in candidates:
            if lemma in matched_lemmas:
                return (
                    [
                        {"source": r[1], "language": r[2], "text": r[3]}
                        for r in matched_rows
                        if r[0] == lemma
                    ],
                    {
                        "lemma": lemma,
                        "original": w,
                        "stripped_suffix": suffix,
                        "case": case_label,
                    },
                )
        return [], None
    finally:
        cur.close()
        release_connection(conn)


def fetch_segment_pali(segment_id: str) -> str | None:
    """Just the Pāli text of one segment — used by the segment-focus
    indicator pre-flight. Tight + cacheable: segment text is immutable."""
    sid = (segment_id or "").lower().strip()
    if not sid or len(sid) > 80:
        return None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT text_pali FROM segment WHERE segment_id = %s LIMIT 1",
            (sid,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        cur.close()
        release_connection(conn)


# Punctuation/symbols stripped from token edges. Keep diacritics — they're
# part of the Pāli alphabet. Includes the curly quotes / em-dash that appear
# in some translations and the question/em marks used by editorial commas.
_TOKEN_TRIM_RE = re.compile(r"^[\W_]+|[\W_]+$", flags=re.UNICODE)


def tokenize_pali(text: str) -> list[str]:
    """Split Pāli text into lowercased word tokens. Strips edge punctuation
    but preserves all letter chars (including ā ī ū ṃ ṅ ñ ṭ ḍ ṇ ḷ etc.).
    Returns unique tokens preserving first-occurrence order — duplicates
    waste DB roundtrip space."""
    seen: dict[str, None] = {}
    for raw in (text or "").split():
        word = _normalize_pali(_TOKEN_TRIM_RE.sub("", raw).lower())
        if word and len(word) >= 2 and word not in seen:
            seen[word] = None
    return list(seen.keys())


def check_words_have_entries(words: list[str]) -> dict[str, dict[str, Any]]:
    """Batch lemma-check for many words at once. ONE DB query regardless
    of input size (~10ms for a 30-word segment) — the API endpoint that
    backs the per-segment indicator can hit this without worrying about
    N+1 patterns.

    Returns `{word: {has_entry: bool, lemma: str|None}}`. `lemma` is set
    only when the resolution went through stem-fallback (same semantics
    as `lookup_word`). Empty input → empty dict.
    """
    if not words:
        return {}
    # Cap inputs — defensive against malformed segment text that might
    # tokenize into thousands of fragments. 200 tokens covers any real
    # segment (longest sutta segments observed are ~120 words).
    words = [w for w in words if w and len(w) <= 60][:200]
    if not words:
        return {}

    # Build candidate set: each input word itself + its lemma candidates.
    # `word_candidates` keeps insertion order (longest-suffix-first per word)
    # so the resolver below picks the strongest match.
    all_candidates: set[str] = set()
    word_candidates: dict[str, list[tuple[str, str | None, str | None]]] = {}
    for w in words:
        cands: list[tuple[str, str | None, str | None]] = [(w, None, None)]
        cands.extend(_candidate_lemmas(w))
        word_candidates[w] = cands
        for c, _, _ in cands:
            all_candidates.add(c)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT word FROM dictionary WHERE word = ANY(%s)",
            (list(all_candidates),),
        )
        existing = {r[0] for r in cur.fetchall()}
    finally:
        cur.close()
        release_connection(conn)

    out: dict[str, dict[str, Any]] = {}
    for w, cands in word_candidates.items():
        resolved = None
        for candidate, suffix, _case in cands:
            if candidate in existing:
                resolved = candidate if suffix else None
                out[w] = {"has_entry": True, "lemma": resolved}
                break
        else:
            out[w] = {"has_entry": False, "lemma": None}
    return out


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
