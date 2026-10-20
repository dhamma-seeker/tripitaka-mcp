"""Regression test — verify_quote.

เครื่องมือนี้มีหน้าที่เดียว: **บอกว่าข้อความที่ยกมามีอยู่ในคลังจริงไหม** ถ้ามันตอบผิด
มันจะผิดในทางที่แย่ที่สุดสองแบบ — รับรองประโยคที่ไม่มีอยู่ว่ามีอยู่ (false exact)
หรือบอกว่าไม่มีทั้งที่มี (false not_found) เคสในไฟล์นี้จึงคุมทั้งสองทาง

ใช้:
    TRIPITAKA_BACKEND=sqlite TRIPITAKA_DB_PATH=tripitaka.db \\
        .venv/bin/python scripts/test_verify_quote.py
    TRIPITAKA_BACKEND=postgres .venv/bin/python scripts/test_verify_quote.py
    .venv/bin/python scripts/test_verify_quote.py --both     # เทียบสอง backend
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sutta_verify import verify_quote  # noqa: E402

# (ข้อความ, verdict ที่ต้องได้, segment ที่ต้องเป็นอันดับหนึ่ง | None, ทำไมถึงคุมข้อนี้)
CASES = [
    (
        "Katañjalī anadhivaraṁ ayācatha",
        "exact", "bv1:2.2",
        "ของจริงจากพุทธวงศ์ — ถ้าอันนี้ไม่ exact แปลว่าเครื่องมือใช้ไม่ได้เลย",
    ),
    (
        "Kat-añjalī andhivaraṁ ayācatha",
        "close", "bv1:2.2",
        "รูปที่สวดคลาดในไทย ต้องไม่ผ่านเป็น exact และต้องชี้ของจริงให้เห็น"
        " (อาจารย์ดนัย: อ่านผิดแล้วความหมายกลายเป็น 'ผู้มืดบอด')",
    ),
    (
        "Ayaṁ vuccati, bhikkhave, sammādiṭṭhi",
        "exact", None,
        "สูตรมาตรฐานที่ซ้ำหลายสูตร — ต้อง exact ไม่ว่าจะไปโดนสูตรไหน",
    ),
    (
        "Blind is the world",
        "exact", "dhp174:1",
        "ฝั่งอังกฤษต้องใช้ได้ด้วย ไม่ใช่บาลีอย่างเดียว",
    ),
    (
        "Manopubbangama dhamma manosettha manomaya",
        "exact", "dhp1:1",
        "ธรรมบทคาถาแรก — คาถาถูกแบ่งเป็นท่อนละบาท ท่อนเดียวไม่มีทางมีครบทั้งวลี"
        " ต้องต่อท่อนถัดไปถึงจะเจอ และต้องไม่ตกเพราะเครื่องหมายวรรคตอน",
    ),
    (
        "Cattaro mahapadese desessami",
        "close", None,
        "ยกมาโดยขาดคำว่า bhikkhave ไปคำเดียว — ของจริงวางอยู่ตรงหน้า"
        " เคยตอบ not_found เพราะเกณฑ์ดูแต่ ratio ไม่ดู coverage",
    ),
    (
        "The Buddha said that all beings possess Buddha nature",
        "not_found", None,
        "ประโยคมหายานที่ฟังดูเป็นพุทธ — เคสที่ AI ยกมาผิดบ่อยที่สุด",
    ),
    (
        "Mendicants, meditate in the golden temple of infinite compassion",
        "not_found", None,
        "แต่งขึ้นล้วนแต่ใช้คำศัพท์ของพระสูตร — false exact ที่นี่คือความล้มเหลวที่แพงที่สุด",
    ),
]


# เคสที่ **ควรผ่านแต่วันนี้ยังไม่ผ่าน** — รายงานออกมาให้เห็นทุกครั้ง แต่ *ไม่นับเข้า exit code*
# (Decision 2026-10-18: ไม่ปล่อยให้ Test Gate แดงค้าง เพราะของที่แดงนานๆ คนจะชินแล้วมองข้าม
#  ซึ่งอันตรายกว่าไม่มีเทสเลย) — **ลบรายการออกจากลิสต์นี้แล้วย้ายขึ้นไปใน CASES ทันทีที่เหตุถูกแก้**
# ถ้ารายการไหนกลับมาผ่านเองโดยธงยังอยู่ สคริปต์จะส่งเสียงบอกให้เก็บธง
# (ข้อความ, verdict ที่ควรได้, segment ที่ควรเป็นอันดับหนึ่ง | None, ทำไมถึงคุม, รออะไรอยู่)
KNOWN_FAIL = [
    (
        "Hetuyā tīṇi, ārammaṇe pañca, adhipatiyā ekaṁ …pe… avigate pañca.",
        "exact", "patthana9.6:12.1",
        "ยกข้อความของ patthana9.6:12.1 มาเป๊ะทุกตัวอักษร แต่เครื่องมือตอบ close แล้วชี้ไป"
        " patthana3.10:40.1 ซึ่งเป็นคนละบรรทัดและตัวเลขไม่เหมือนกัน (pañca แทน tīṇi กับ ekaṁ)"
        " = ปฏิเสธบรรทัดที่มีอยู่จริง ซึ่งเป็นความผิดด้านที่แพงกว่าของเครื่องมือนี้"
        " (AN 2.23 กล่าวตู่สองแบบ — ใส่คำที่ไม่ได้ตรัส กับปฏิเสธคำที่ตรัส)",
        "C3 — `_CANDIDATE_CAP = 400` ใน sutta_verify.py ดึง candidate ด้วย `ORDER BY seg.id`"
        " วลีนี้มี candidate 756 แถว และ seg.id ของอภิธรรมสูงสุดในคลังเพราะโหลดท้ายสุด"
        " แถวที่ใช่จึงถูกตัดทิ้งตั้งแต่ก่อนให้คะแนน · คอมเมนต์ใน sutta_verify.py เองยอมรับไว้แล้ว"
        " ว่าผลแบบนี้อาจเกิดจากการตัดแถว ไม่ใช่เพราะข้อความไม่มีจริง",
    ),
]


def rows(term: str):
    from db.backend import get_backend

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        return verify_quote(cur, backend.name, term, limit=3)
    finally:
        try:
            cur.close()
        except Exception:
            pass
        backend.release(conn)


_PENDING = [0]  # known-fail ที่ยังไม่ผ่าน — ใช้ให้บรรทัดสรุปพูดตรงกับความจริง


def run_cases(cases, *, known_fail: bool = False) -> tuple[int, int]:
    """รันชุดเคส คืน (จำนวนที่ไม่ผ่าน, จำนวนที่ผ่านทั้งที่ขึ้นบัญชี known-fail ไว้)"""
    failed = surprises = 0
    for case in cases:
        text, want_verdict, want_seg, why = case[:4]
        r = rows(text)
        got = r["verdict"]
        top = r["matches"][0]["segment_id"] if r["matches"] else None
        ok = got == want_verdict and (want_seg is None or top == want_seg)
        mark = ("🎉" if ok else "⏳") if known_fail else ("✅" if ok else "❌")
        print(f"  {mark} {want_verdict:<9} {text[:46]}")
        if ok and known_fail:
            surprises += 1
            print("       🎉 known-fail ข้อนี้ผ่านแล้ว — ลบออกจาก KNOWN_FAIL"
                  " แล้วย้ายขึ้นไปใน CASES")
            continue
        if ok:
            continue
        if known_fail:
            _PENDING[0] += 1
            print(f"       ยังไม่ผ่าน ไม่นับเข้า exit code · รอ: {case[4]}")
        else:
            failed += 1
        print(f"       why: {why}")
        print(f"       got: verdict={got} top={top}")
        for m in r["matches"]:
            print(f"            {m['similarity']:.3f} {m['segment_id']} {(m['text'] or '')[:50]}")
    return failed, surprises


def run() -> int:
    failed, _ = run_cases(CASES)
    if KNOWN_FAIL:
        print("  ── known-fail (รายงานอย่างเดียว ไม่นับเข้า exit code)")
        _, surprises = run_cases(KNOWN_FAIL, known_fail=True)
        if surprises:
            print(f"  🎉 known-fail ที่ผ่านแล้ว {surprises} ข้อ — เก็บธงออกได้")
    return failed


def main() -> int:
    args = set(sys.argv[1:])
    if "--both" in args:
        import db.backend as backend_module

        failed = 0
        for name in ("postgres", "sqlite"):
            os.environ["TRIPITAKA_BACKEND"] = name
            backend_module._backend = None
            print(f"── {name}")
            failed += run()
        backend_module._backend = None
    else:
        print(f"── {os.getenv('TRIPITAKA_BACKEND', 'postgres')}")
        failed = run()
    print()
    if failed:
        print(f"❌ fail {failed} ข้อ")
        return 1
    pending = _PENDING[0]
    print("✅ เคสบังคับผ่านทั้งหมด"
          + (f" · known-fail ค้าง {pending} ข้อ (ดูรายละเอียดด้านบน)" if pending else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
