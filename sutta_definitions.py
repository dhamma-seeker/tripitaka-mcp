"""
Tripitaka MCP — Sutta-based definition detection (issue #4).

Reusable detection layer: หา "ท่อนนิยาม" ในพระไตรปิฎกสำหรับศัพท์บาลีหนึ่งคำ โดย
อาศัย *สูตรนิยาม* ที่คัมภีร์ใช้นิยามศัพท์ของตัวเอง (Pavel K's pattern set, issue #4).

ต่างจาก get_word_definition (พจนานุกรม/lexical) — ตัวนี้คืน "นิยามเชิงธรรมจากในสูตร"
เช่น `dukkha`:
  opener  →  "Katamañca, bhikkhave, dukkhaṁ ariyasaccaṁ?"
  closer  →  "Idaṁ vuccati, bhikkhave, dukkhaṁ ariyasaccaṁ."

**Design (2-stage, ตรงกับที่ Pavel ทำใน Dhamma Gift):**
  1. หา anchor segment: term (รูปผัน) + definitional marker อยู่ใน segment เดียวกัน
  2. Python: classify (direct/simile · descriptive/enumerative) + score + dedup + rank

**Verifiability:** ทุกผลลัพธ์ผูกกับ segment_id จริง — layer นี้ไม่ "สรุป" เอง (นั่นเป็น
หน้าที่ AI client). คืน passage ที่ cite ได้ + คะแนน ให้ client เลือกนำเสนอ essence.

**Reusable:** ไม่พึ่ง MCP — รับ DB-API cursor + backend name เข้ามาตรงๆ จึง expose
เป็นได้ทั้ง MCP tool และ data-export (สำหรับ consumer ที่ไม่มี AI เช่น Dhamma Gift).

ดู Dual-Backend Discipline ใน CLAUDE.md.
"""

from __future__ import annotations

import re
from typing import Any

from db.normalize import fold_pali

# ---------------------------------------------------------------------------
# Definitional markers (folded — ตรงกับ FTS5 `remove_diacritics 2` + fold_pali)
# ที่มา: pattern set ของ Pavel (issue #4). ใช้เป็น FTS prefix + Python regex.
# ---------------------------------------------------------------------------

# คำถามเปิดนิยาม — "X คืออะไร/อย่างไร", "Kiñca X vadetha?" (จะเรียก X ว่าอะไร)
_INTERROGATIVE = ("katam", "katham", "vadeth")  # katamañca/katamo/…, kathaṁ, vadetha
# คำชี้ขาด — "เรียกว่า X / X เป็นชื่อเรียกของ / กล่าวคือ"
_PREDICATE = ("vucc", "adhivacan", "yadidam")   # vuccati/vuccanti, adhivacana, yadidaṁ
# วินัย padabhājaniya — "<term> nāma" (ต้องติดกับ term → เช็ค adjacency ใน Python)
_NAMA = "nama"
# อุปมา/นิยามทางอ้อม (ชั้นรอง)
_SIMILE = ("seyyathapi", "upam", "opam", "opamm", "evameva")

# FTS prefix tokens สำหรับ stage-1 recall (marker ตัวใดตัวหนึ่งอยู่ใน segment)
_MARKER_PREFIXES = tuple(
    f"{m}*" for m in (*_INTERROGATIVE, *_PREDICATE, _NAMA, *_SIMILE)
)

# ตัวเลขหมู่ (folded) — สัญญาณว่านิยามเป็นแบบ "แจกแจงประเภท" (enumerative)
# เช่น "cha viññāṇakāyā" (วิญญาณ 6). Pavel: descriptive ควรมีน้ำหนักเหนือ enumerative.
_NUMERAL_WORDS = frozenset({
    "dve", "dvi", "tayo", "tini", "cattaro", "cattari", "panca",
    "cha", "satta", "attha", "nava", "dasa",
    "seyyathidam",  # "กล่าวคือ:" — มักตามด้วยลิสต์
})

# สูตรวิเคราะห์/วิภังค์ (whitelist boost) — จาก pattern set ของ Pavel.
# สูตรที่ "นิยามศัพท์" เป็นหน้าที่หลัก → ท่อนที่เจอในนี้น่าเชื่อถือกว่า.
_VIBHANGA_SUTTAS = frozenset({
    "mn135", "mn136", "mn137", "mn138", "mn139", "mn140", "mn141", "mn142",
    "sn12.2", "sn22.79", "sn45.8", "sn47.40", "sn48.9", "sn48.10", "sn48.36",
    "sn48.37", "sn48.38", "sn51.20", "dn15", "dn22", "dn33", "dn34",
    "an3.34", "an3.111", "an3.112", "an6.39", "an10.174", "sn12.60", "sn14.12",
})

# case endings ของ a-stem (folded) — สร้างรูปผิวจาก stem เพื่อ recall แบบ token
# (แม่นกว่า prefix `dukkh*` ที่ไปติด compound เช่น dukkhudrayo/dukkhavipāka)
_A_STEM_ENDINGS = (
    "a", "o", "am", "ena", "assa", "aya", "amhi", "asmim",
    "e", "ani", "ehi", "ebhi", "anam", "esu", "ato", "asma",
)
# endings ทั่วไปสำหรับ stem ที่ไม่ลงท้าย -a (i/u/พยัญชนะ)
_GENERIC_ENDINGS = ("", "m", "ssa", "ya", "no", "ni", "na", "smim", "su", "nam")

# สัตตมี/ตติยา/ปัญจมี — วิภัตติที่บอก "ที่ไหน/ด้วยอะไร/จากอะไร" ไม่ใช่ "อะไรคืออะไร".
# นิยามจริงวางศัพท์เป็นประธาน (`ayaṁ vuccati loko`) หรือสัมพันธการกคู่ adhivacana
# (`kāyassa adhivacanaṁ` = ชื่อเรียกของกาย) ทั้งสองอย่างไม่อยู่ในลิสต์นี้ จึงไม่ถูกตัด
_OBLIQUE_A_ENDINGS = ("e", "amhi", "asmim", "esu", "ena", "ehi", "ebhi", "ato", "asma")
_OBLIQUE_GENERIC_ENDINGS = ("smim", "su")

# สัมพันธการก — ก้ำกึ่ง. `adhivacana` เรียกร้องมันตามไวยากรณ์ (`kāyassa adhivacanaṁ`
# = "เป็นชื่อเรียกของกาย") จึงเป็นนิยามเต็มตัว. แต่ลำพังมันขยายคำอื่นในประโยค
# `Katamesānaṁ dhammānaṁ nirodho 'nirodho'ti vuccati` นิยาม *nirodha* ไม่ใช่ *dhamma*
_GENITIVE_A_ENDINGS = ("assa", "anam")
_GENITIVE_GENERIC_ENDINGS = ("ssa", "nam", "no")
_ADHIVACANA = "adhivacan"

# `kataṁ` = "ทำแล้ว" fold แล้วได้ `katam` พอดี ชนกับ prefix ของ katama- ("อันไหน")
# ทั้งคลังมี 10,915 ท่อนที่มี kataṁ แบบนี้ ทำให้ `kataṁ buddhassa sāsanaṁ`
# ("กิจแห่งพระพุทธเจ้าสำเร็จแล้ว") ถูกอ่านเป็นคำถามนิยาม.
# ตัดด้วยการยกเว้น token ที่ยาวเท่ากับ `katam` เป๊ะ ไม่ใช่เปลี่ยน prefix เป็น `katama`
# เพราะ katamo/katame ไม่ได้ขึ้นต้นด้วย katama — ลองแล้ว คำถามจริงหายไปด้วย
_FALSE_MARKER_TOKENS = frozenset({"katam"})

# ให้ระยะห่าง token ระหว่าง term กับ marker ที่ยังถือว่า "ใกล้พอจะนิยาม"
_PROXIMITY_TOKENS = 14

# คอลัมน์ที่ candidate query คืน (id + section_id ใช้ทำ block-windowing)
_CANDIDATE_COLS = (
    "sutta_id", "segment_id", "text_pali", "text_english", "seg_id", "section_id",
)


def _inflected_forms(folded_term: str) -> set[str]:
    """สร้างรูปผัน (folded) ของศัพท์ เพื่อ match แบบ whole-token (เลี่ยง compound).

    a-stem (`dukkha`) → {dukkha, dukkho, dukkham, dukkhena, dukkhassa, …}
    อื่นๆ (`viññāṇa`→`vinnana`) → a-stem ด้วย (ลงท้าย a); `sati`→ generic.
    """
    forms = {folded_term}
    if folded_term.endswith("a") and len(folded_term) > 2:
        stem = folded_term[:-1]
        forms.update(stem + e for e in _A_STEM_ENDINGS)
        # quotative 'ti (นิยามแบบ "Vijānātīti … 'viññāṇan'ti vuccati") — apostrophe
        # แยก token ใน FTS → "'viññāṇan'ti" = "vinnanan"+"ti" → ต้องมี stem+"an";
        # "viññāṇanti" (fused ไม่มี ') → stem+"anti". (รูป -ā'ti/-o'ti = folded term/stem+"o" อยู่แล้ว)
        forms.update(stem + e for e in ("an", "anti"))
    else:
        forms.update(folded_term + e for e in _GENERIC_ENDINGS)
    return {f for f in forms if f}


def _oblique_forms(folded_term: str) -> set[str]:
    """รูปที่ศัพท์ทำหน้าที่ "ฉาก" ไม่ใช่สิ่งที่ถูกนิยาม (ดู _OBLIQUE_A_ENDINGS)"""
    if folded_term.endswith("a") and len(folded_term) > 2:
        stem = folded_term[:-1]
        return {stem + e for e in _OBLIQUE_A_ENDINGS}
    return {folded_term + e for e in _OBLIQUE_GENERIC_ENDINGS}


def _genitive_forms(folded_term: str) -> set[str]:
    """รูปสัมพันธการก — นับเป็นนิยามเฉพาะตอนคู่กับ adhivacana (ดู _GENITIVE_A_ENDINGS)"""
    if folded_term.endswith("a") and len(folded_term) > 2:
        stem = folded_term[:-1]
        return {stem + e for e in _GENITIVE_A_ENDINGS}
    return {folded_term + e for e in _GENITIVE_GENERIC_ENDINGS}


def _fetch_candidates_sqlite(cur, forms: set[str]) -> list[dict[str, Any]]:
    """SQLite (FTS5): anchor segment = (รูปผันของ term) AND (marker ใดๆ) ใน text_pali."""
    form_clause = " OR ".join(sorted(forms))
    marker_clause = " OR ".join(_MARKER_PREFIXES)
    match = f"text_pali : (({form_clause}) AND ({marker_clause}))"
    cur.execute(
        """
        SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english,
               seg.id, seg.section_id
        FROM segment_fts f
        JOIN segment seg ON seg.id = f.rowid
        JOIN section sec ON seg.section_id = sec.id
        WHERE f.segment_fts MATCH ?
        """,
        (match,),
    )
    return [dict(zip(_CANDIDATE_COLS, r)) for r in cur.fetchall()]


def _fetch_candidates_postgres(cur, forms: set[str]) -> list[dict[str, Any]]:
    """Postgres: anchor segment ผ่าน f_unaccent + word-boundary regex.

    ⚠️ ยังไม่ได้ verify บน server จริง (ไม่มี PG local) — ต้องผ่าน Test Gate ก่อน merge.
    โครงตาม dual-backend: stage-1 recall เท่านั้น, scoring ทำใน Python เหมือน SQLite.
    """
    # รูปผัน → alternation, marker → alternation ; match บน f_unaccent(text_pali)
    form_alt = "|".join(re.escape(f) for f in sorted(forms))
    marker_alt = "|".join((*_INTERROGATIVE, *_PREDICATE, _NAMA, *_SIMILE))
    cur.execute(
        """
        SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english,
               seg.id, seg.section_id
        FROM segment seg
        JOIN section sec ON seg.section_id = sec.id
        WHERE f_unaccent(seg.text_pali) ~* %(term)s
          AND f_unaccent(seg.text_pali) ~* %(marker)s
        """,
        {"term": rf"\y({form_alt})\y", "marker": rf"\y({marker_alt})"},
    )
    return [dict(zip(_CANDIDATE_COLS, r)) for r in cur.fetchall()]


def _tokens(folded_text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", folded_text)


def _min_distance(tokens: list[str], forms: set[str], prefixes: tuple[str, ...]) -> int | None:
    """ระยะ token ที่สั้นที่สุดระหว่าง term (whole word) กับ marker (prefix). None = ไม่พบคู่."""
    term_idx = [i for i, t in enumerate(tokens) if t in forms]
    mark_idx = [i for i, t in enumerate(tokens)
                if t not in _FALSE_MARKER_TOKENS
                and any(t.startswith(p) for p in prefixes)]
    if not term_idx or not mark_idx:
        return None
    return min(abs(a - b) for a in term_idx for b in mark_idx)


def _classify(
    folded_text: str,
    forms: set[str],
    oblique: set[str] | None = None,
    genitive: set[str] | None = None,
) -> dict[str, Any] | None:
    """Classify anchor: หา marker ที่ใกล้ term ที่สุด + kind (descriptive/enumerative).

    คืน None ถ้า term ไม่ปรากฏเป็น "คำเต็ม" (กัน compound-prefix false positive) หรือ
    ไม่มี marker ใกล้พอ.
    """
    tokens = _tokens(folded_text)
    tokset = set(tokens)
    present = tokset & forms
    if not present:
        return None  # term ไม่ใช่คำเต็มในท่อนนี้ → ตัดทิ้ง (เช่น dukkhudrayo)

    # ศัพท์ปรากฏแต่ในรูปสัตตมี/ตติยา/ปัญจมี → มันเป็นฉากของประโยค ไม่ใช่สิ่งที่ถูกนิยาม.
    # `ariyassa vinaye vuccanti` = "ในธรรมวินัยของพระอริยะ เรียกสิ่งนั้นว่า…" นิยามคำอื่น
    # ไม่ใช่นิยาม vinaya. เช่นเดียวกับ `ayaṁ vuccati puggalo sīlesu ca paripūrakārī`
    # ที่นิยาม*บุคคล* ไม่ใช่*ศีล*. ระยะห่างแยกสองกรณีนี้ไม่ได้ — `vinaye` อยู่ติด
    # `vuccanti` เลย — วิภัตติเท่านั้นที่แยกได้
    if oblique and present <= oblique:
        return None

    # สัมพันธการกล้วนๆ ผ่านได้เฉพาะตอนมี adhivacana ในท่อนเดียวกัน
    if genitive and present <= (genitive | (oblique or set())):
        if not any(t.startswith(_ADHIVACANA) for t in tokset):
            return None

    # marker ที่ใกล้ term ที่สุดในแต่ละกลุ่ม (ภายในระยะ proximity)
    def near(prefixes):
        d = _min_distance(tokens, forms, prefixes)
        return d if d is not None and d <= _PROXIMITY_TOKENS else None

    d_interro = near(_INTERROGATIVE)
    d_pred = near(_PREDICATE)
    d_simile = near(_SIMILE)
    # Vinaya "X nāma" — "nama" ต้องเป็น *คำเต็ม* และตามหลัง term ทันที.
    # (ห้ามใช้ startswith — ไม่งั้นไปแมตช์ nāmarūpa/nāmapaccayā = name-and-form ผิด)
    has_nama = any(
        t == _NAMA and i > 0 and tokens[i - 1] in forms
        for i, t in enumerate(tokens)
    )

    markers: list[str] = []
    if d_interro is not None:
        markers.append("interrogative")
    if d_pred is not None:
        markers.append("predicate")
    if has_nama:
        markers.append("nama")
    if d_simile is not None:
        markers.append("simile")
    if not markers:
        return None

    is_direct = bool({"interrogative", "predicate", "nama"} & set(markers))
    kind = "direct" if is_direct else "simile"

    # descriptive vs enumerative — enumerative = มีตัวเลขหมู่/seyyathidaṁ ในท่อน
    enumerative = bool(tokset & _NUMERAL_WORDS)
    detail = "enumerative" if enumerative else "descriptive"

    # ระยะที่ดีที่สุด (ยิ่งใกล้ยิ่ง anchor แน่น)
    dists = [d for d in (d_interro, d_pred, d_simile) if d is not None]
    if has_nama:
        dists.append(1)
    return {
        "markers": markers,
        "kind": kind,
        "detail": detail,
        "min_distance": min(dists) if dists else _PROXIMITY_TOKENS,
    }


def _score(row: dict[str, Any], cls: dict[str, Any]) -> int:
    """ให้คะแนน anchor. direct > simile ; descriptive > enumerative ; วิภังค์ boost."""
    score = 0
    if "predicate" in cls["markers"]:
        score += 100          # "idaṁ vuccati X" / "X adhivacana" = ชี้ขาดที่สุด
    if "interrogative" in cls["markers"]:
        score += 90           # "Katamañca X?" = เปิดนิยาม
    if "nama" in cls["markers"]:
        score += 85           # วินัย "<term> nāma"
    if cls["kind"] == "simile":
        score += 40           # อุปมา = ชั้นรอง
    # Pavel: descriptive ต้องไม่จมใต้ enumerative — แต่สำหรับบางศัพท์ (āsava,
    # viññāṇa) "การแจกแจงประเภท = ตัวนิยาม" → penalty เบา ๆ พอให้ descriptive
    # อยู่เหนือ แต่ enumeration ไม่หายไปจากผลลัพธ์.
    score += 25 if cls["detail"] == "descriptive" else -5
    # boost ถ้าอยู่ในสูตรวิภังค์
    base_sutta = re.split(r"[:#]", row["segment_id"], 1)[0]
    if base_sutta in _VIBHANGA_SUTTAS:
        score += 15  # tiebreaker เบา ๆ — ไม่ให้ whitelist กลบ signal marker/detail
    # ยิ่ง marker ใกล้ term ยิ่งดี (สูงสุด +14)
    score += max(0, _PROXIMITY_TOKENS - cls["min_distance"])
    return score


def _window_for(markers: list[str]) -> tuple[int, int]:
    """(before, after) segment รอบ anchor — เอนไปทางที่ "ตัวนิยาม" อยู่.

    closer (predicate "idaṁ vuccati X") → นิยามอยู่ *ก่อน* → ดึงก่อนเยอะ.
    opener (interrogative "Katama X?") → นิยามอยู่ *หลัง* → ดึงหลังเยอะ.
    """
    if "predicate" in markers:
        return (10, 2)
    if "nama" in markers:
        return (1, 8)
    if "interrogative" in markers:
        return (2, 10)
    return (4, 4)


def _fetch_block(cur, backend_name: str, section_id: int, anchor_id: int,
                 before: int, after: int) -> list[dict[str, Any]]:
    """ดึงท่อนนิยามเต็ม = segment รอบ anchor ใน section เดียวกัน (document order).

    id ต่อเนื่องเป๊ะใน section (ยืนยันบนคลังจริง) → window ด้วย id-range ได้ตรง
    โดยไม่ต้องโหลดทั้งสูตร.
    """
    lo, hi = anchor_id - before, anchor_id + after
    if backend_name == "sqlite":
        cur.execute(
            "SELECT segment_id, text_pali, text_english FROM segment "
            "WHERE section_id = ? AND id BETWEEN ? AND ? ORDER BY id",
            (section_id, lo, hi),
        )
    else:
        cur.execute(
            "SELECT segment_id, text_pali, text_english FROM segment "
            "WHERE section_id = %s AND id BETWEEN %s AND %s ORDER BY id",
            (section_id, lo, hi),
        )
    return [
        {"segment_id": r[0], "pali": r[1], "english": r[2]}
        for r in cur.fetchall()
    ]


def _detail_from_block(block: list[dict[str, Any]]) -> str:
    """descriptive vs enumerative จาก *ทั้ง block* (แม่นกว่าดูแค่ anchor — การ
    แจกแจงมักอยู่ใน segment ข้างเคียง เช่น "Katame tayo? kāmāsavo …")."""
    toks: set[str] = set()
    for seg in block:
        toks.update(_tokens(fold_pali(seg["pali"])))
    return "enumerative" if (toks & _NUMERAL_WORDS) else "descriptive"


def book_prefix(sutta_id: str) -> str:
    """`mn141` → `mn`, `mil7.2.2` → `mil`, `pli-tv-bu-vb-ss11` → `pli-tv-bu-vb-ss`.

    The leading non-digit run of a sutta_id is its book, one-to-one with
    `book.code` across the whole corpus (verified against the DB).
    """
    head = re.split(r"\d", sutta_id, maxsplit=1)[0].rstrip("-.")
    return head or sutta_id


def _in_sources(sutta_id: str, sources: set[str]) -> bool:
    """Exact book match, or a family prefix followed by a hyphen.

    The hyphen matters: a bare `startswith` would let `mn` swallow `mnd`
    (Majjhima vs Mahāniddesa — different texts, different authority). The
    family form exists for `pli-tv`, which covers every Vinaya book.
    """
    book = book_prefix(sutta_id)
    return book in sources or any(book.startswith(s + "-") for s in sources)


def find_definitions(
    cur,
    backend_name: str,
    term: str,
    limit: int = 5,
    include_similes: bool = True,
    sources: set[str] | None = None,
) -> list[dict[str, Any]]:
    """หา anchor นิยามของ `term` จากในสูตร/วินัย เรียงตามความเป็นนิยามที่แท้จริง.

    Args:
        cur: DB-API cursor (จาก backend.cursor()).
        backend_name: "sqlite" | "postgres".
        term: ศัพท์บาลี (รูป dictionary/stem เช่น "dukkha", "viññāṇa").
        limit: จำนวนผลลัพธ์สูงสุด.
        include_similes: รวมนิยามแบบอุปมา (ชั้นรอง) ไหม.
        sources: จำกัดเล่มที่ค้น เช่น {"dn","mn","sn","an"} — None = ทุกเล่ม.
            ใช้ book code (ดู `book_prefix`); `pli-tv` = วินัยทั้งหมด.

    Returns:
        list เรียงคะแนนมาก→น้อย, แต่ละตัว:
          {sutta_id, segment_id (= anchor), text_pali, text_english,
           markers[], kind (direct/simile), detail (descriptive/enumerative),
           score, duplicates (จำนวนท่อนซ้ำที่ยุบรวม),
           block[] (ท่อนนิยามเต็มรอบ anchor: {segment_id, pali, english})}
    """
    folded = fold_pali(term)
    if not folded:
        return []
    forms = _inflected_forms(folded)
    oblique = _oblique_forms(folded)
    genitive = _genitive_forms(folded)

    if backend_name == "sqlite":
        rows = _fetch_candidates_sqlite(cur, forms)
    else:
        rows = _fetch_candidates_postgres(cur, forms)

    # Filtered in Python, deliberately, not in the SQL. The candidate queries
    # carry no LIMIT — every match already comes back and is scored here — so
    # narrowing at this point costs nothing, and both backend queries stay
    # byte-for-byte as they were. Applied before scoring so `limit` counts
    # results the caller actually asked for.
    if sources:
        rows = [r for r in rows if _in_sources(r["sutta_id"], sources)]

    scored: list[dict[str, Any]] = []
    for row in rows:
        cls = _classify(fold_pali(row["text_pali"]), forms, oblique, genitive)
        if cls is None:
            continue
        if cls["kind"] == "simile" and not include_similes:
            continue
        scored.append({**row, **cls, "score": _score(row, cls)})

    # dedup — ยุบท่อนที่ข้อความ (folded) เหมือนกัน (เช่น "cha viññāṇakāyā" ซ้ำหลายสูตร)
    # Pavel: uniqueness ช่วยกันไม่ให้ descriptive 1 ท่อนจมใต้ enumerative 10 ท่อน
    #
    # ตัวตัดสินตอนคะแนนเท่ากันคือ segment_id ไม่ใช่ลำดับที่แถวเข้ามา: `ayaṁ vuccati sati.`
    # มีทั้งใน cnd10 และ mnd14 คะแนนเท่ากันเป๊ะ ตัวไหนถูกเก็บจึงเคยขึ้นกับลำดับที่ DB
    # คืนมา ซึ่ง Postgres (regex) กับ SQLite (FTS) ไม่เหมือนกัน คำเดียวกันเลยได้คำตอบ
    # คนละสูตรในสองแบ็กเอนด์ ทั้งที่ผลรวมทั้งหมดเท่ากันเป๊ะ
    def _rank(item: dict[str, Any]) -> tuple[float, str, str]:
        return (-item["score"], item["sutta_id"], item["segment_id"])

    best: dict[str, dict[str, Any]] = {}
    for item in scored:
        key = fold_pali(item["text_pali"])
        if key not in best or _rank(item) < _rank(best[key]):
            keep = dict(item)
            keep["duplicates"] = best.get(key, {}).get("duplicates", 0)
            best[key] = keep
        else:
            best[key]["duplicates"] = best[key].get("duplicates", 0) + 1

    top = sorted(best.values(), key=_rank)[:limit]

    # block-windowing — ดึงท่อนนิยามเต็มรอบ anchor + refine descriptive/enumerative
    # จาก context ทั้ง block (ทำเฉพาะ top `limit` เพื่อคุมจำนวน query)
    for item in top:
        before, after = _window_for(item["markers"])
        item["block"] = _fetch_block(
            cur, backend_name, item["section_id"], item["seg_id"], before, after
        )
        item["detail"] = _detail_from_block(item["block"])
    return top
