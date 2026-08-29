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

# ตัดสินผล — ใช้สองค่าคู่กัน
# `ratio` (SequenceMatcher) สมมาตร จึงลงโทษความยาวที่ต่างกัน
# `coverage` = สัดส่วนตัวอักษรของ *วลีที่ถาม* ที่ไปปรากฏในท่อนนั้นตามลำดับ
#   → ตอบคำถามที่เราสนใจจริงๆ คือ "สิ่งที่ผมยกมา อยู่ในบรรทัดนี้แค่ไหน"
# เคสที่บังคับให้ต้องมี coverage: `Cattaro mahapadese desessami` ขาดคำว่า
# `bhikkhave` ไปคำเดียว ratio ตก 0.778 แต่ coverage เกือบเต็ม — ของจริงอยู่ตรงหน้า
# แต่เดิมตอบ not_found
_EXACT = 0.995
_CLOSE_COVERAGE = 0.85
_CLOSE_RATIO = 0.55   # กันวลีสั้นที่ตัวอักษรบังเอิญไปโผล่ในท่อนยาวๆ

# คาถาถูกแบ่งเป็นท่อนละบาท (`dhp1:1` = "Manopubbaṅgamā dhammā," สองคำ) วลีที่ยกมา
# จึงมักคร่อมหลายท่อน ต้องลองต่อท่อนถัดไปแล้ววัดใหม่ — id ต่อเนื่องใน section
# (ยืนยันแล้ว ดู `_fetch_block` ใน sutta_definitions.py)
_JOIN_AHEAD = 3        # ต่อได้มากสุดกี่ท่อน
_JOIN_RESCORE = 25     # เอา candidate อันดับต้นแค่นี้มาลองต่อ กันงานบาน

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


def _token_exists(cur, backend_name: str, tok: str) -> bool:
    """token นี้มีอยู่ในคลังไหม — ใช้คัดคำที่ยกมาผิดออกจากตะแกรง"""
    if backend_name == "sqlite":
        cur.execute(
            "SELECT 1 FROM segment_fts WHERE segment_fts MATCH ? LIMIT 1",
            ("{text_pali text_english} : " + tok,),
        )
    else:
        cur.execute(
            "SELECT 1 FROM segment WHERE f_unaccent(coalesce(text_pali,'') || ' ' || "
            "coalesce(text_english,'')) ~* %s LIMIT 1",
            (rf"\y{re.escape(tok)}",),
        )
    return cur.fetchone() is not None


def _fetch_candidates(cur, backend_name: str, toks: list[str]) -> list[dict[str, Any]]:
    """ไล่ตะแกรงจากแคบไปกว้าง หยุดทันทีที่เจอ

        AND ทุก token  →  AND สอง token ที่ยาวที่สุด  →  token ที่ยาวที่สุดตัวเดียว

    **ห้ามใช้ OR รวมทุก token** เพราะ token ธรรมดาอย่าง `dhamma` มี 11,539 ท่อน
    พอชน LIMIT แล้วแถวที่ต้องการก็ถูกตัดทิ้งแบบสุ่ม — ธรรมบทคาถาแรกหายไปทั้งที่
    `manopubbangama` มีแค่ 19 ท่อน. ความยาวใช้แทนความหายากได้ดีพอ จึงไล่ลงมา
    ทีละขั้นแทนที่จะเหวี่ยงแห
    """
    if not toks:
        return []
    # คัด token ที่ไม่มีอยู่ในคลังทิ้งก่อน **สำคัญมาก** เพราะเวลาคนยกข้อความมาผิด
    # คำที่ผิดมักเป็นคำที่หายากที่สุด ซึ่งเป็นขั้นสุดท้ายของ ladder พอดี
    # `andhivaram` ไม่มีในพระไตรปิฎกเลย ถ้าไม่คัดออก ทั้งวลีจะหาอะไรไม่เจอสักแถว
    # ทั้งที่ `ayacatha` ในวลีเดียวกันพาไปถึง bv1:2.2 ได้
    # การที่ token หนึ่งคืนศูนย์แถว **คือหลักฐานว่าตรงนั้นแหละที่ยกมาผิด**
    def _run(ts: list[str]) -> list[dict[str, Any]]:
        return _ladder(cur, backend_name, ts)

    rows = _run(toks)
    if rows:
        return rows
    # ยังไม่เจอ → ตอนนี้ค่อยจ่ายค่า existence check ซึ่งเป็น full scan บน Postgres
    # **เวลาคนยกข้อความมาผิด คำที่ผิดมักเป็นคำที่หายากที่สุด** ซึ่งเป็นขั้นสุดท้าย
    # ของตะแกรงพอดี `andhivaram` ไม่มีในคลังเลย ถ้าไม่คัดออกทั้งวลีจะหาไม่เจอสักแถว
    # ทั้งที่ `ayacatha` ในวลีเดียวกันพาไปถึง bv1:2.2 ได้
    # **การที่ token คืนศูนย์แถวคือหลักฐานว่าตรงนั้นแหละที่ยกมาผิด**
    live = [t for t in toks if _token_exists(cur, backend_name, t)]
    if not live or live == toks:
        return []
    return _run(live)


def _ladder(cur, backend_name: str, live: list[str]) -> list[dict[str, Any]]:
    """ไล่ตะแกรงจากแคบไปกว้างบน token ชุดที่ให้มา"""
    ladders = [(live, "AND"), (live[:2], "AND"), (live[:1], "AND"), (live, "OR")]
    seen: list[tuple[tuple[str, ...], str]] = []
    for lad, op in ladders:
        key = (tuple(lad), op)
        if not lad or key in seen:
            continue
        seen.append(key)
        if backend_name == "sqlite":
            match = "{text_pali text_english} : (" + f" {op} ".join(lad) + ")"
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
            where = f" {op} ".join(
                f"(f_unaccent(coalesce(seg.text_pali,'') || ' ' || "
                f"coalesce(seg.text_english,'')) ~* %(t{i})s)"
                for i in range(len(lad))
            )
            params: dict[str, Any] = {
                f"t{i}": rf"\y{re.escape(t)}" for i, t in enumerate(lad)
            }
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


def _fetch_join_windows(
    cur, backend_name: str, anchors: list[dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    """{seg_id ของ anchor: [ท่อนถัดไปตามลำดับ]} — ใช้ต่อคาถาที่ถูกแบ่งเป็นบาท"""
    if not anchors:
        return {}
    out: dict[int, list[dict[str, Any]]] = {}
    for a in anchors:
        lo, hi = a["seg_id"] + 1, a["seg_id"] + _JOIN_AHEAD
        if backend_name == "sqlite":
            cur.execute(
                "SELECT text_pali, text_english FROM segment "
                "WHERE section_id = ? AND id BETWEEN ? AND ? ORDER BY id",
                (a["section_id"], lo, hi),
            )
        else:
            cur.execute(
                "SELECT text_pali, text_english FROM segment "
                "WHERE section_id = %s AND id BETWEEN %s AND %s ORDER BY id",
                (a["section_id"], lo, hi),
            )
        out[a["seg_id"]] = [
            {"text_pali": r[0], "text_english": r[1]} for r in cur.fetchall()
        ]
    return out


def _score(folded_q: str, candidate: str | None) -> tuple[float, float, bool]:
    """(ratio, coverage, contained)

    `contained` = วลีที่ถามอยู่ในท่อนนี้ครบทุกตัวอักษรติดกัน → ตรงเป๊ะ จบเลย
    `coverage` = ตัวอักษรของวลีที่ถามกี่ส่วนที่ไปตรงกับท่อนนี้ตามลำดับ
    """
    folded_c = fold_pali(candidate or "")
    if not folded_c or not folded_q:
        return 0.0, 0.0, False
    if folded_q in folded_c:
        return 1.0, 1.0, True
    # เทียบเป็นลำดับ *คำ* ด้วย — คนยกข้อความมาไม่ลอกจุลภาคกับอัฒภาคมาด้วย
    # ธรรมบทคาถาแรกถูกทุกคำแต่ได้แค่ 0.976 เพราะ `dhammā,` มีลูกน้ำติดมา
    qt, ct = _tokens(folded_q), _tokens(folded_c)
    if qt and len(qt) <= len(ct):
        for i in range(len(ct) - len(qt) + 1):
            if ct[i:i + len(qt)] == qt:
                return 1.0, 1.0, True
    sm = SequenceMatcher(None, folded_q, folded_c)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return sm.ratio(), matched / len(folded_q), False


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
            ratio, cov, contained = _score(folded_q, row[field])
            if ratio <= 0.0:
                continue
            scored.append({
                "sutta_id": row["sutta_id"],
                "segment_id": row["segment_id"],
                "field": "pali" if field == "text_pali" else "english",
                "text": row[field],
                "similarity": round(ratio, 4),
                "coverage": round(cov, 4),
                "contained": contained,
                "spans": 1,
                "_seg_id": row["seg_id"],
                "_section_id": row["section_id"],
            })

    # เลือก candidate ที่จะเอาไปลองต่อ **ด้วย ratio ไม่ใช่ coverage**: coverage
    # เข้าข้างท่อนยาวโดยอัตโนมัติ (ท่อนยาวมีตัวอักษรของวลีเราบังเอิญครบง่ายกว่า)
    # ส่วน ratio สมมาตร จึงดัน `dhp1:1` ("Manopubbaṅgamā dhammā," สองคำ) ขึ้นมา
    # เหนือท่อนยาวที่ไม่เกี่ยว ซึ่งเป็นท่อนที่เราต้องได้เพื่อจะต่อบาทถัดไป
    scored.sort(key=lambda m: -m["similarity"])

    # คาถาคร่อมหลายท่อน — ลองต่อท่อนถัดไปให้ candidate อันดับต้น แล้ววัดใหม่
    heads = scored[:_JOIN_RESCORE]
    anchors = [{"seg_id": m["_seg_id"], "section_id": m["_section_id"]} for m in heads]
    windows = _fetch_join_windows(cur, backend_name, anchors)
    for m in heads:
        field = "text_pali" if m["field"] == "pali" else "text_english"
        joined = m["text"] or ""
        for i, nxt in enumerate(windows.get(m["_seg_id"], []), start=2):
            joined = f"{joined} {nxt[field] or ''}".strip()
            ratio, cov, contained = _score(folded_q, joined)
            if cov > m["coverage"] or (cov == m["coverage"] and ratio > m["similarity"]):
                m.update(similarity=round(ratio, 4), coverage=round(cov, 4),
                         contained=contained, text=joined, spans=i)

    # เรียงสุดท้ายด้วย coverage + ratio: ต้องดีทั้งคู่ถึงจะขึ้น ท่อนยาวที่ไม่เกี่ยว
    # ได้ coverage สูงแต่ ratio ต่ำ (0.5 + 0.28) จึงแพ้ของจริงที่ได้ทั้งสองทาง
    scored.sort(key=lambda m: (not m["contained"],
                               -(m["coverage"] + m["similarity"]),
                               m["segment_id"]))
    top = [{k: v for k, v in m.items() if not k.startswith("_")} for m in scored[:limit]]

    if top and (top[0]["contained"] or top[0]["similarity"] >= _EXACT):
        verdict = "exact"
    elif top and top[0]["coverage"] >= _CLOSE_COVERAGE and top[0]["similarity"] >= _CLOSE_RATIO:
        verdict = "close"
    else:
        verdict = "not_found"
    return {"verdict": verdict, "matches": top, "searched_tokens": toks}
