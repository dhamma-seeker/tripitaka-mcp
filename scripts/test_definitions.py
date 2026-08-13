"""Regression test — define_from_suttas.

`test_full_sutta.py` แตะแค่ `get_sutta` ทุกครั้งที่แก้ `sutta_definitions.py`
จึงต้องนั่งเทียบผลด้วยตาเอง — รอบเดือน ส.ค. 2026 แก้ไฟล์นั้นเจ็ดครั้งและทุกครั้ง
ต้องรันเทียบใหม่ทั้งชุด ไฟล์นี้ทำแทน

ตรวจสามชั้น:

1. **Invariants** — กฎที่ *เคยพัง* จริงในโปรดักชัน แต่ละข้อผูกกับบั๊กที่เจอ
   และมี `why` บอกว่ามันมาจากไหน อ่านไฟล์นี้แล้วเห็นประวัติได้เลย
2. **Backend parity** — Postgres กับ SQLite ต้องคืนผลเหมือนกันเป๊ะ
   (เคยต่างกัน 4 คำ เพราะ tie-break ขึ้นกับลำดับที่ DB คืนมา)
3. **Snapshot** — ผลของทุกคำใน `TERMS` ถ้าเปลี่ยนต้องตั้งใจเปลี่ยน
   ทบทวน diff แล้วรันด้วย `--update` เพื่อรับผลใหม่

ใช้:
    TRIPITAKA_BACKEND=postgres .venv/bin/python scripts/test_definitions.py
    TRIPITAKA_BACKEND=sqlite   .venv/bin/python scripts/test_definitions.py
    .venv/bin/python scripts/test_definitions.py --both      # เทียบสอง backend ด้วย
    .venv/bin/python scripts/test_definitions.py --update    # รับ snapshot ใหม่

Exit code 0 ถ้าผ่านหมด, 1 ถ้ามี fail — ใช้ใน Test Gate ได้
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.normalize import fold_pali  # noqa: E402
from sutta_definitions import find_definitions  # noqa: E402

SNAPSHOT_PATH = Path(__file__).resolve().parent / "definitions_snapshot.json"
LIMIT = 5

# คำที่ล็อกไว้ใน snapshot — คลุมทั้งคำที่เคยพังและคำที่ต้องไม่ขยับ
TERMS = [
    "vinaya", "loka", "sila", "sasana", "dhamma", "dukkha", "citta", "tanha",
    "sati", "nibbana", "kaya", "magga", "panna", "kamma", "vinnana", "khandha",
    "phassa", "vedana", "avijja", "upadana", "samadhi", "viriya", "jhana",
    "saddha", "nivarana", "saddhindriya", "kimsuka",
]


def rows(term: str, limit: int = LIMIT) -> list[dict[str, Any]]:
    from db.backend import get_backend

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        return find_definitions(cur, backend.name, term, limit=limit)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        backend.release(conn)


def _pali(result: list[dict[str, Any]]) -> str:
    return " ".join(r["text_pali"] or "" for r in result).lower()


def _ids(result: list[dict[str, Any]]) -> list[str]:
    return [r["sutta_id"] for r in result]


def _has_term(row: dict[str, Any], term: str) -> bool:
    from sutta_definitions import _inflected_forms, _tokens

    folded = fold_pali(row["text_pali"] or "")
    return bool(set(_tokens(folded)) & _inflected_forms(fold_pali(term)))


# ---------------------------------------------------------------------------
# Invariants — ทุกข้อคือบั๊กที่เคยหลุดขึ้นโปรดักชันจริง
# ---------------------------------------------------------------------------

Check = tuple[str, str, str, Callable[[list[dict[str, Any]]], bool]]

INVARIANTS: list[Check] = [
    (
        "locative is not the subject",
        "vinaya",
        "`ariyassa vinaye vuccanti` = 'ในธรรมวินัยของพระอริยะ เรียกว่า…' — vinaye เป็น"
        " สัตตมี บอกฉาก สิ่งที่ถูกนิยามคือคำอื่น เคยตอบ 5 แถวเป็นสูตรนี้ทั้งหมด",
        lambda r: "ariyassa vinaye" not in _pali(r),
    ),
    (
        "kataṁ is not katama-",
        "sasana",
        "`kataṁ` ('ทำแล้ว') fold แล้วชนกับ prefix ของ katama- ('อันไหน') ทั้งคลังมี"
        " 10,915 ท่อน เคยตอบ `kataṁ buddhassa sāsanaṁ` 4 ใน 5 แถว",
        lambda r: "buddhassa sāsanaṁ" not in _pali(r),
    ),
    (
        "genitive needs adhivacana",
        "tanha",
        "`esa paccayo taṇhāya, yadidaṁ vedanā` บอกว่าเวทนาเป็นปัจจัยของตัณหา ไม่ได้"
        " นิยามตัณหา เคยอยู่เหนือ `Ayaṁ vuccati, bhikkhave, taṇhā` ของ sn12.2",
        lambda r: "paccayo taṇhāya" not in _pali(r) and "sn12.2" in _ids(r),
    ),
    (
        "stratum beats alphabet",
        "loka",
        "คัมภีร์ชั้นหลังใช้สูตร `ayaṁ vuccati X` บ่อยกว่ามาก เคยได้ cnd5 · vb12 · kv1.1"
        " เต็มหน้า ทั้งที่ sn35.116 พูดเรื่องเดียวกัน",
        lambda r: all(i.startswith(("dn", "mn", "sn", "an")) for i in _ids(r)),
    ),
    (
        "shared line cites the earlier book",
        "nibbana",
        "`nibbānaṁ iti vuccatī'ti.` มีเหมือนกันเป๊ะใน sn1.64 · snp5.14 · cnd17"
        " tie-break ตามตัวอักษรเคยยกให้ cnd17 เพราะ c มาก่อน s",
        lambda r: "cnd17" not in _ids(rows("nibbana", limit=10)),
    ),
    (
        "closing formula must close on the term",
        "magga",
        "`ayaṁ vuccati, bhikkhave, anariyo maggo` นิยาม*คำประสม* ไม่ใช่ maggo"
        " เคยขึ้นเป็นแถวแรกและ 4 ใน 5 แถวเป็นคำประสมทั้งหมด sn45.8 ตกไปอันดับ 5",
        lambda r: _ids(r)[:1] == ["sn45.8"],
    ),
    (
        "a simile is not a definition",
        "kimsuka",
        "sn35.245 วาดภาพต้นทองกวาว ไม่ได้นิยามมัน หน้าเว็บเคยขึ้นว่า '4 definitions'",
        lambda r: all(x["kind"] == "simile" for x in r),
    ),
    (
        "kattha + daṭṭhabba is a definition",
        "saddhindriya",
        "`Kattha ca, bhikkhave, saddhindriyaṁ daṭṭhabbaṁ?` ทำหน้าที่เหมือน Katamañca"
        " 22 ท่อนทั้งคลัง ไม่มีของปลอม",
        lambda r: "sn48.8" in _ids(r),
    ),
    (
        "bare daṭṭhabba stays out",
        "rupa",
        "`daṭṭhabba` ลำพังเป็นคำสอนให้ปฏิบัติ ('พึงเห็นรูปว่าไม่ใช่ตัวตน') 456 ท่อน"
        " ถ้ารั่วเข้ามา rupa จะโดนหนักที่สุดเพราะเต็มไปด้วยสูตรอนัตตา",
        lambda r: "daṭṭhabb" not in _pali(r),
    ),
    (
        "similes without the term are found",
        "jhana",
        "อุปมาฌานสี่อันไม่มีคำว่า jhāna อยู่ในตัวมันเลย เกาะกับสูตร `vivicceva kāmehi`"
        " ที่เปิดย่อหน้า — Pavel รายงานว่ามองไม่เห็น",
        lambda r: any(x.get("context") for x in r),
    ),
    (
        "context rows really lack the term",
        "jhana",
        "ถ้าแถว context มีคำที่ค้นอยู่แล้ว แปลว่าเส้นทางปกติควรจับได้ และป้ายกำกับ"
        " 'The term is not in this line' จะกลายเป็นคำโกหก",
        lambda r: not any(x.get("context") and _has_term(x, "jhana") for x in r),
    ),
    (
        "no context similes where there is no marker",
        "tanha",
        "`taṇhā sneho` เปรียบด้วยการวางคำคู่กัน ไม่มี seyyathāpi/evameva เลย"
        " ยืนยันกับ Pavel ไปว่าเคสแบบนี้ต้องใช้ลิสต์มือ",
        lambda r: not any(x.get("context") for x in r),
    ),
]


def run_invariants() -> int:
    print("── invariants")
    failed = 0
    for name, term, why, predicate in INVARIANTS:
        result = rows(term)
        ok = predicate(result)
        print(f"  {'✅' if ok else '❌'} {name}  ({term})")
        if not ok:
            failed += 1
            print(f"       why: {why}")
            for x in result:
                flag = " [ctx]" if x.get("context") else ""
                print(f"       got: {x['segment_id']}{flag}  {(x['text_pali'] or '')[:60]}")
    return failed


def snapshot_of() -> dict[str, list[str]]:
    out = {}
    for term in TERMS:
        out[term] = [
            f"{r['segment_id']}|{r['kind']}" + ("|ctx" if r.get("context") else "")
            for r in rows(term)
        ]
    return out


def run_snapshot(update: bool) -> int:
    current = snapshot_of()
    if update or not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.write_text(
            json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"── snapshot เขียนใหม่แล้ว ({len(current)} คำ) → {SNAPSHOT_PATH.name}")
        return 0
    saved = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    print("── snapshot")
    failed = 0
    for term in TERMS:
        want, got = saved.get(term, []), current[term]
        if want == got:
            continue
        failed += 1
        print(f"  ❌ {term}")
        for line in want:
            if line not in got:
                print(f"       หาย: {line}")
        for line in got:
            if line not in want:
                print(f"       เพิ่ม: {line}")
    if not failed:
        print(f"  ✅ ตรงกับ snapshot ทั้ง {len(TERMS)} คำ")
    else:
        print("     ถ้าตั้งใจเปลี่ยน ทบทวน diff แล้วรัน --update")
    return failed


def run_parity() -> int:
    """Postgres กับ SQLite ต้องคืนผลเหมือนกันเป๊ะ

    เคยต่างกัน 4 คำ เพราะตอนคะแนนเสมอ ตัวไหนถูกเก็บขึ้นกับลำดับที่ DB คืนมา
    ซึ่ง Postgres (regex) กับ SQLite (FTS) ไม่เหมือนกัน
    """
    import db.backend as backend_module

    print("── backend parity")
    both = {}
    for name in ("postgres", "sqlite"):
        os.environ["TRIPITAKA_BACKEND"] = name
        backend_module._backend = None
        both[name] = snapshot_of()
    backend_module._backend = None
    differ = [t for t in TERMS if both["postgres"][t] != both["sqlite"][t]]
    for term in differ:
        print(f"  ❌ {term}")
        print(f"       postgres: {both['postgres'][term]}")
        print(f"       sqlite  : {both['sqlite'][term]}")
    if not differ:
        print(f"  ✅ สองแบ็กเอนด์ตรงกันทั้ง {len(TERMS)} คำ")
    return len(differ)


def main() -> int:
    args = set(sys.argv[1:])
    backend = os.getenv("TRIPITAKA_BACKEND", "postgres")
    print(f"define_from_suttas regression — backend={backend}\n")
    failed = run_invariants()
    failed += run_snapshot(update="--update" in args)
    if "--both" in args:
        failed += run_parity()
    print()
    if failed:
        print(f"❌ fail {failed} ข้อ")
        return 1
    print("✅ ผ่านทั้งหมด")
    return 0


if __name__ == "__main__":
    sys.exit(main())
