"""หาชื่อสูตรจาก heading segments (SuttaCentral convention).

`section.title_pali` ใน DB ว่างเกือบทั้งหมด (32 จาก 7,361 แถว) โค้ดจึงต้อง
fallback ไปอ่านจาก segment. เดิมทุกจุดใช้ `:0.2` ตรงๆ ซึ่ง**ผิด** เพราะจำนวน
heading ต่างกันตามชุดคัมภีร์ และชื่อสูตรอยู่ **ตัวสุดท้าย** เสมอ ส่วนตัวก่อนหน้า
คือชื่อคอลเลกชัน / นิบาต / วรรค:

    mn141:0.1    Majjhima Nikāya 141
    mn141:0.2    Saccavibhaṅgasutta        ← ชื่อสูตร (:0.2 บังเอิญถูกเฉพาะ DN/MN)

    sn35.245:0.1 Saṁyutta Nikāya 35.245
    sn35.245:0.2 19. Āsīvisavagga          ← :0.2 = ชื่อ**วรรค** ไม่ใช่ชื่อสูตร
    sn35.245:0.3 Kiṁsukopamasutta          ← ชื่อสูตรจริง

    iti44:0.1    Itivuttaka 44
    iti44:0.2    Dukanipāta
    iti44:0.3    Dutiyavagga
    iti44:0.4    Nibbānadhātusutta         ← ลึกถึง :0.4

กฎ "heading ตัวสุดท้าย" ตรวจกับทั้ง corpus แล้วไม่ขัดกับกฎ "ตัวที่ลงท้าย
-sutta" แม้แต่สูตรเดียว (7,288 sutta_id, ต่างกัน 0) และครอบคลุมชุดที่ชื่อไม่ได้
ลงท้ายด้วย -sutta ด้วย เช่น `Uragasutta` ของ Snp, `Subhūtittheragāthā` ของ Thag,
`1. Apaṇṇakajātaka` ของ Ja และ `1. Paṭhamapārājikasikkhāpada` ของ Vinaya
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, TypeVar

# `dhp1-20` ใช้ segment_id ขึ้นต้นว่า `dhp1:` ไม่ตรงกับ sutta_id ของตัวเอง
# จึง match ที่ท้ายสตริงอย่างเดียว ไม่ผูกกับ sutta_id
_HEADING_RE = re.compile(r":0\.\d+$")

# รูปแบบเดียวกันสำหรับใช้ใน SQL (POSIX regex ของ Postgres) — เก็บไว้ที่เดียวกัน
# เพื่อไม่ให้ฝั่ง SQL กับฝั่ง Python เลื่อนออกจากกันเงียบๆ
HEADING_SQL_RE = r":0\.[0-9]+$"

# bilara ใส่ `~` ไว้ตรงที่ไม่มีชื่อบาลี (59 สูตร ส่วนใหญ่เป็นสูตรช่วงแบบ
# `an11.502-981`) คำแปลอังกฤษยังมีอยู่ จึงตัดเฉพาะฝั่งบาลี ไม่ทิ้งทั้งแถว
_UNTITLED = "~"

T = TypeVar("T")


def is_heading(segment_id: str | None) -> bool:
    return bool(segment_id) and bool(_HEADING_RE.search(segment_id))


def last_heading(
    rows: Iterable[T], segment_id_of: Callable[[T], str | None]
) -> T | None:
    """แถว heading ตัวสุดท้ายตามลำดับในเอกสาร = ชื่อสูตร (None ถ้าไม่มี)

    รับ callable แทนที่จะบังคับรูปแบบแถว เพราะแต่ละ call site มีคอลัมน์ไม่เหมือนกัน
    (main.py มี pali/thai/english, reader มีแค่ pali/english)
    """
    found: T | None = None
    for row in rows:
        if is_heading(segment_id_of(row)):
            found = row
    return found


def clean_title(text: Any) -> str | None:
    """None สำหรับค่าว่างและ `~` เพื่อให้ caller fallback ต่อได้ตามปกติ"""
    if not text:
        return None
    text = str(text).strip()
    if not text or text == _UNTITLED:
        return None
    return text
