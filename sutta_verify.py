"""Tripitaka MCP — verify that a quoted passage actually exists in the canon.

**มหาปเทสในรูปเครื่องมือ.** AN 4.180 บอกว่าเมื่อมีผู้อ้างว่านี่คือพุทธพจน์
อย่ารับเพราะผู้พูด **ให้เอาไปเทียบกับสุตตะและวินัย** — โมดูลนี้ทำสิ่งนั้นให้ทำได้จริง:
วางข้อความที่ถูกอ้างเข้ามา แล้วตอบว่ามันอยู่ในคลังจริงไหม อยู่ตรงไหน หรือของจริง
เขียนว่าอย่างไร

สองกรณีที่มันตอบ:

1. **AI ยกพระสูตรมามั่ว** — ประโยคที่ฟังดูเหมือนพระไตรปิฎกแต่ไม่มีอยู่จริง
   เป็นความผิดพลาดที่ตรวจยากที่สุดเพราะมัน*ฟังถูก* (ท่าน Sujato เรียกว่า
   "plausible nonsense" ใน AI-1)
2. **ความคลาดเคลื่อนของการสืบทอด** — `kat-añjalī andhivaraṁ` ที่สวดกันในไทย
   เทียบกับ `Katañjalī anadhivaraṁ` ที่อยู่ในพุทธวงศ์จริง (bv1:2.2) ต่างกันแค่
   การแบ่งคำ แต่ความหมายเปลี่ยนจาก "ผู้ไม่มีใครยิ่งกว่า" เป็น "ผู้มืดบอด"
   AN 5.156 เรียกความคลาดแบบนี้ว่าเหตุแห่งความเสื่อมของพระสัทธรรม

**สถาปัตยกรรม** เหมือน `sutta_definitions.py` — SQL ทำแค่ stage-1 recall
ส่วนการให้คะแนนอยู่ใน Python ทั้งหมด แบ็กเอนด์จึงคืนผลตรงกันโดยไม่ต้องพึ่ง
`pg_trgm` ที่ SQLite ไม่มี
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from db.normalize import fold_pali

# token ที่สั้นกว่านี้ไม่ใช้เป็น recall key — `ca` `ti` `so` โผล่ทุกที่
_MIN_RECALL_LEN = 5
# จำนวน token ที่ยาวที่สุดที่เอาไปใช้ค้น — ยิ่งยาวยิ่งหายาก จึงคัดผลได้แคบ
_RECALL_TOKENS = 4
# เพดาน candidate ที่ยอมให้เข้ามาให้คะแนน กัน worst case ของวลีที่ใช้คำธรรมดาล้วน
_CANDIDATE_CAP = 400

# ตัดสินผล — similarity จาก SequenceMatcher บนข้อความที่ fold แล้ว
_EXACT = 0.995     # ต่างกันได้แค่ระดับ noise ของการ fold
_CLOSE = 0.80      # ใกล้พอที่จะเป็น "ของจริงเขียนว่าอย่างนี้"

_COLS = ("sutta_id", "segment_id", "text_pali", "text_english", "seg_id", "section_id")


def _tokens(folded: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", folded)


def _recall_tokens(folded: str) -> list[str]:
    """token ที่ยาวที่สุดไม่กี่ตัว — ใช้เป็นตะแกรงหยาบชั้นแรก

    ความยาวเป็นตัวแทนของความหายากที่ถูกพอใช้และไม่ต้องสร้างตาราง frequency:
    `anadhivaram` มีไม่กี่สิบท่อน ส่วน `ca` มีเป็นแสน
    """
    uniq = {t for t in _tokens(folded) if len(t) >= _MIN_RECALL_LEN}
    return sorted(uniq, key=len, reverse=True)[:_RECALL_TOKENS]


def _fetch_candidates(cur, backend_name: str, toks: list[str]) -> list[dict[str, Any]]:
    """ท่อนที่มี recall token **ครบทุกตัว** (AND) — ถ้าไม่เจอเลยค่อยผ่อนเป็น OR.

    AND ก่อนเพราะวลีที่ยกมาจริงจะมีคำหายากอยู่ด้วยกัน การผ่อนเป็น OR ไว้ทีหลัง
    ทำให้เคส "จำผิดไปหนึ่งคำ" ยังหาเจอ ซึ่งเป็นเคสที่เครื่องมือนี้มีไว้ตอบพอดี
    """
    if not toks:
        return []
    for mode in ("and", "or"):
        if backend_name == "sqlite":
            joiner = " AND " if mode == "and" else " OR "
            match = "{text_pali text_english} : (" + joiner.join(toks) + ")"
            cur.execute(
                """
                SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english,
                       seg.id, seg.section_id
                FROM segment_fts f
                JOIN segment seg ON seg.id = f.rowid
                JOIN section sec ON seg.section_id = sec.id
                WHERE f.segment_fts MATCH ?
                LIMIT ?
                """,
                (match, _CANDIDATE_CAP),
            )
        else:
            joiner = " AND " if mode == "and" else " OR "
            where = joiner.join(
                f"(f_unaccent(coalesce(seg.text_pali,'') || ' ' || "
                f"coalesce(seg.text_english,'')) ~* %(t{i})s)"
                for i in range(len(toks))
            )
            params = {f"t{i}": rf"\y{re.escape(t)}" for i, t in enumerate(toks)}
            params["cap"] = _CANDIDATE_CAP
            cur.execute(
                f"""
                SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english,
                       seg.id, seg.section_id
                FROM segment seg
                JOIN section sec ON seg.section_id = sec.id
                WHERE {where}
                LIMIT %(cap)s
                """,
                params,
            )
        rows = [dict(zip(_COLS, r)) for r in cur.fetchall()]
        if rows:
            return rows
    return []


def _score(folded_q: str, candidate: str | None) -> tuple[float, bool]:
    """(similarity, contained) — `contained` = ข้อความที่ถามอยู่ในท่อนนี้ครบทั้งวลี

    ท่อนหนึ่งมักยาวกว่าวลีที่ยกมา การเทียบ ratio ตรงๆ จึงลงโทษวลีสั้นอย่างไม่เป็นธรรม
    ถ้าเป็น substring ก็จบเลย = ตรงเป๊ะ
    """
    folded_c = fold_pali(candidate or "")
    if not folded_c:
        return 0.0, False
    if folded_q in folded_c:
        return 1.0, True
    return SequenceMatcher(None, folded_q, folded_c).ratio(), False


def verify_quote(
    cur, backend_name: str, text: str, limit: int = 3
) -> dict[str, Any]:
    """หาว่าข้อความที่ยกมามีอยู่ในคลังไหม.

    Args:
        cur: DB-API cursor · backend_name: "sqlite" | "postgres"
        text: ข้อความที่ถูกอ้าง — บาลีหรืออังกฤษก็ได้ ค้นทั้งสองฟิลด์เสมอ
        limit: จำนวนผลใกล้เคียงที่คืนเมื่อไม่ตรงเป๊ะ

    Returns:
        {verdict: "exact"|"close"|"not_found", matches: [...], searched_tokens: [...]}
        แต่ละ match มี `field` บอกว่าเจอในบาลีหรือคำแปล และ `similarity` 0–1
    """
    folded_q = fold_pali(text).strip()
    if not folded_q:
        return {"verdict": "not_found", "matches": [], "searched_tokens": []}

    toks = _recall_tokens(folded_q)
    rows = _fetch_candidates(cur, backend_name, toks)

    scored: list[dict[str, Any]] = []
    for row in rows:
        for field in ("text_pali", "text_english"):
            sim, contained = _score(folded_q, row[field])
            if sim <= 0.0:
                continue
            scored.append({
                "sutta_id": row["sutta_id"],
                "segment_id": row["segment_id"],
                "field": "pali" if field == "text_pali" else "english",
                "text": row[field],
                "similarity": round(sim, 4),
                "contained": contained,
            })

    scored.sort(key=lambda m: (-m["similarity"], m["segment_id"]))
    top = scored[:limit]

    if top and top[0]["similarity"] >= _EXACT:
        verdict = "exact"
    elif top and top[0]["similarity"] >= _CLOSE:
        verdict = "close"
    else:
        verdict = "not_found"
    return {"verdict": verdict, "matches": top, "searched_tokens": toks}
