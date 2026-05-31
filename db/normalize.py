"""
Tripitaka MCP Server — Pāli text normalization (folding)

หน้าที่เดียว: fold ข้อความบาลีโรมันสำหรับการค้นแบบ "ไม่สนสระยาว/จุดบาลี".

ใช้ใน `main.py` (survey_corpus) ทางเดียว — สำหรับสร้าง `matched_forms` (ดึงรูปคำ
จริงที่ match จาก text) และทำ folded needle ของ LIKE/regex. การ "match" จริงในแต่ละ
แบ็คเอนด์ไม่ได้พึ่งฟังก์ชันนี้: Postgres ใช้ `f_unaccent(text_*)` (functional GIN
index), SQLite ใช้ FTS5 tokenizer — ไม่มี folded column เก็บใน DB.

โดยตั้งใจให้ fold "เทียบเท่า" กับทั้ง SQLite FTS5 tokenizer
`unicode61 remove_diacritics 2` และ Postgres `f_unaccent` (= unaccent + lower):
ทั้งหมด = ตัด diacritic + lowercase. (ยืนยันบนคลังจริง: kusinārā → 11 word /
67 stem ตรงกันทั้งสามทาง.)
"""

from __future__ import annotations

import unicodedata


def fold_pali(text: str | None) -> str:
    """Fold Romanised Pāli: NFKD → strip combining marks → lowercase.

    `kusinārā`/`kusinara`, `ānāpānassati`/`anapanassati`, `ṁ→m`, `ñ→n` ฯลฯ
    fold เป็น key เดียวกัน. คืน "" ถ้า input เป็น None/ว่าง.

        >>> fold_pali("Kusinārāyaṁ")
        'kusinarayam'
    """
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()
