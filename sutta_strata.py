"""Tripitaka MCP — which stratum of the canon a passage comes from.

This lives on its own because more than one tool needs the same answer and
they must not drift apart. `define_from_suttas` weighs the stratum in its
ranking and labels every row it returns. `verify_quote` has to be able to say
the same thing about a line it just confirmed, because a line can be in the
canon and still not be the Buddha's word: the Milindapañha is in the corpus,
and a bare `exact` against one of its narrator's sentences reads as though it
were buddhavacana.

AN 2.24 (nītattha / neyyattha) is the reason the label is not optional. What
needs interpreting must not be handed over as though it were explicit, and the
reader cannot tell the difference unless we say which layer a passage sits in.
"""

from __future__ import annotations

import re

# ลำดับชั้น: เลขน้อย = ใกล้พระโอษฐ์กว่า · ใช้เป็นดัชนีของทั้งป้ายและค่าถ่วงน้ำหนัก
# (ค่าถ่วงอยู่ที่ฝั่งจัดอันดับใน sutta_definitions.py — ที่นี่เก็บแต่การจำแนก)
_STRATUM = {
    **{b: 0 for b in ("dn", "mn", "sn", "an")},                    # สี่นิกาย
    **{b: 1 for b in ("dhp", "ud", "iti", "snp", "thag", "thig")},  # ขุททกะชั้นต้น
}
_STRATUM_VINAYA = 2
_STRATUM_OTHER = 3  # นิทเทส ปฏิสัมภิทา อภิธรรม มิลินท์ ชาดก อปทาน ฯลฯ

SOURCE_LAYER = {
    0: "four-nikayas",     # DN MN SN AN
    1: "early-khuddaka",   # Dhp Ud Iti Snp Thag Thig
    2: "vinaya",
    3: "later-texts",      # นิทเทส ปฏิสัมภิทา อภิธรรม มิลินท์ ชาดก อปทาน ฯลฯ
}

LAYERS = frozenset(SOURCE_LAYER.values())


def book_prefix(sutta_id: str) -> str:
    """`mn141` → `mn`, `mil7.2.2` → `mil`, `pli-tv-bu-vb-ss11` → `pli-tv-bu-vb-ss`.

    The leading non-digit run of a sutta_id is its book, one-to-one with
    `book.code` across the whole corpus (verified against the DB).
    """
    head = re.split(r"\d", sutta_id, maxsplit=1)[0].rstrip("-.")
    return head or sutta_id


def stratum(sutta_id: str) -> int:
    """ชั้นคัมภีร์เป็นตัวเลข — ใช้ตอนให้คะแนน"""
    book = book_prefix(sutta_id)
    if book in _STRATUM:
        return _STRATUM[book]
    return _STRATUM_VINAYA if book.startswith("pli-tv") else _STRATUM_OTHER


def source_layer(sutta_id: str) -> str:
    """ชั้นคัมภีร์เป็นป้ายที่ส่งถึงผู้ใช้ — หนึ่งในค่าใน `LAYERS`"""
    return SOURCE_LAYER[stratum(sutta_id)]
