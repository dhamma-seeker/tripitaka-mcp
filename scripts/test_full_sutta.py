"""Smoke test — verify get_sutta returns full content for various sutta sizes.

ตรวจ 4 invariants ต่อสูตร:
1. server return ไม่มี error
2. segment_count == len(segments) (no truncation)
3. ลำดับ segment_id อยู่ในสูตรนั้นจริง (first → last)
4. segment_count ตรงกับค่าที่ pin ไว้ใน `full_sutta_snapshot.json` **เป๊ะ**

ข้อ 4 มาแทนเกณฑ์ "ขั้นต่ำ" เดิม ซึ่งเป็นช่องโหว่ของ gate นี้เอง — ทั้ง 22 เคส
ตั้งขั้นต่ำรวมไว้ 8,504 ท่อน ของจริง 10,841 (หลวม 22%) และ 9 เคสยอมให้หาย
ครึ่งสูตรขึ้นไปแล้วยังขึ้น PASS: `mil3.1.1` ตั้ง 3 ของจริง 108 · `thag1.1`
ตั้ง 1 ของจริง 24 · `dn16` ตั้ง 800 ของจริง 1,664. ความครบถ้วนของตัวบทคือจุดขาย
ของโปรเจคนี้ เทสจึงต้องแดงตอนสูตรหายไปท่อนเดียว ไม่ใช่รอให้หายครึ่งสูตร

จำนวน segment ของสูตรไม่ขึ้นกับ backend — ค่าที่ pin ไว้ต้องใช้ได้ทั้ง Postgres
และ SQLite. ถ้าสองฝั่งให้เลขไม่เท่ากันแม้สูตรเดียว นั่นคือข้อมูลสองฝั่งไม่ตรงกัน
ไม่ใช่เรื่องของเทส — อย่าแก้ snapshot ให้ผ่าน ให้ไปหาสาเหตุที่ข้อมูล

ใช้:
    .venv/bin/python scripts/test_full_sutta.py                     # default = production
    MCP_URL=http://localhost:8080/mcp .venv/bin/python scripts/test_full_sutta.py
    MCP_URL=http://localhost:8080/mcp .venv/bin/python scripts/test_full_sutta.py --update

`--update` วัดใหม่จากปลายทางที่ชี้ไว้ รายงาน diff เทียบค่าเดิมก่อน แล้วจึงเขียนทับ
ทบทวน diff ให้แน่ใจว่าเปลี่ยนเพราะตั้งใจ แล้ว commit snapshot ไปด้วย

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail ใด ๆ — ใช้ใน CI ได้
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

from fastmcp import Client

DEFAULT_URL = "https://mcp.tripitaka-mcp.com/mcp"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "full_sutta_snapshot.json"

# จำนวน segment ที่คาดของแต่ละสูตรอยู่ใน snapshot ข้างสคริปต์ ไม่ใช่ในลิสต์นี้
# ลิสต์นี้คุมว่า "ตรวจสูตรไหน" — เลือกครอบ size range: เล็ก/ปกติ/ใหญ่/ใหญ่มาก/
# ที่สุด + รูปแบบ id ที่ parser เคยพลาด
SUTTAS: list[str] = [
    # --- Sutta Piṭaka (Phase A — already in production) ---
    "sn56.11",  # ธัมมจักกัปปวัตตนสูตร — สั้น
    "mn62",  # มหาราหุโลวาท — ปกติ
    "mn1",  # มูลปริยายสูตร — ใหญ่
    "dn22",  # มหาสติปัฏฐาน — ใหญ่มาก
    "dn16",  # มหาปรินิพพาน — ที่สุด (ยาวกว่า DN22)
    # --- KN sub-books ---
    "dhp1-20",  # Dhammapada — bilara group verses เป็นช่วง
    "snp1.8",  # Karaṇīyamettasutta — เมตตสูตร
    "ud3.4",  # Sāriputtasutta อุทาน
    "iti85",  # Asubhānupassīsutta
    "thag1.1",  # Theragāthā 1.1
    "ja1",  # Jātaka 1 (Apaṇṇaka)
    "mil3.1.1",  # Milindapañha — paracanonical, 3-level id format
    # --- Vinaya Piṭaka (Phase B — local-only until prod deploy) ---
    "pli-tv-bu-pm",  # Bhikkhu Pātimokkha — digit-less id format
    "pli-tv-bu-vb-as1-7",  # Bhikkhu Vibhaṅga Adhikaraṇasamatha (range form)
    "pli-tv-kd1",  # Mahāvagga ch. 1 — large Khandhaka section
    "pli-tv-pvr10",  # Parivāra
    # --- Abhidhamma Piṭaka (Phase C — local-only until prod deploy) ---
    "ds1.1",  # Dhammasaṅgaṇī 1.1
    "dt2.1",  # Dhātukathā 2.1
    "kv10.1",  # Kathāvatthu 10.1
    "vb1",  # Vibhaṅga ch.1 — flat single-level id (no .x sub)
    "ya1.1.1",  # Yamaka — 3-level id format
    "patthana1.1",  # Paṭṭhāna — 8-char prefix needs {2,10} regex
]


async def measure(client: Client, sutta_id: str) -> tuple[int | None, str]:
    """ตรวจ invariant 1–3 แล้วคืนจำนวน segment ที่วัดได้

    คืน `None` เมื่อวัดไม่ได้ — ค่าที่วัดจากการเรียกที่พังไปแล้วเอาไป pin ไม่ได้
    """
    try:
        result = await client.call_tool(
            "get_sutta", {"sutta_id": sutta_id, "language": "pali"}
        )
        payload = json.loads(result.content[0].text)
    except Exception as e:
        return None, f"call failed: {e}"

    if "error" in payload:
        return None, f"server error: {payload['error']}"

    count = payload.get("segment_count", 0)
    segments = payload.get("segments", [])
    actual = len(segments)

    if count != actual:
        return None, f"count mismatch: server={count} actual={actual}"

    if not segments:
        return None, "no segments returned"

    # spot-check segments are grouped under this sutta. Range IDs (ending
    # in `<digit>+-<digit>+` like dhp1-20 or pli-tv-bu-vb-as1-7) have
    # segments with individual verse-level ids, so we match on the prefix
    # before the trailing range. Non-range ids must match exactly.
    first_id = segments[0]["segment_id"]
    last_id = segments[-1]["segment_id"]
    if re.search(r"\d+-\d+$", sutta_id):
        # strip trailing "<digit>+-<digit>+" → e.g. "pli-tv-bu-vb-as1-7" → "pli-tv-bu-vb-as"
        range_prefix = re.sub(r"\d+-\d+$", "", sutta_id)
        if not first_id.startswith(range_prefix):
            return None, f"first id {first_id!r} does not start with range prefix {range_prefix!r}"
    else:
        if not first_id.startswith(f"{sutta_id}:"):
            return None, f"first id {first_id!r} not in sutta {sutta_id}"
        if not last_id.startswith(f"{sutta_id}:"):
            return None, f"last id {last_id!r} not in sutta {sutta_id}"

    return count, f"first={first_id} last={last_id}"


def load_pins() -> dict[str, int] | None:
    if not SNAPSHOT_PATH.exists():
        return None
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def report_diff(old: dict[str, int] | None, new: dict[str, int]) -> None:
    """บอกว่าอะไรจะเปลี่ยนก่อนเขียนทับ — ไม่เขียนเงียบ ๆ ให้คนทบทวน diff ได้"""
    if old is None:
        print(f"── snapshot ใหม่ ({len(new)} สูตร) ไม่มีค่าเดิมให้เทียบ")
        for sutta_id, count in new.items():
            print(f"     + {sutta_id:20} {count}")
        print(f"   รวม {sum(new.values()):,} segment")
        return

    changed = [(s, old[s], new[s]) for s in new if s in old and old[s] != new[s]]
    added = [s for s in new if s not in old]
    removed = [s for s in old if s not in new]

    if not (changed or added or removed):
        print(f"── snapshot ไม่มีอะไรเปลี่ยน ({len(new)} สูตร, รวม {sum(new.values()):,} segment)")
        return

    print("── snapshot จะเปลี่ยน — ทบทวนก่อนรับ")
    for sutta_id, was, now in changed:
        print(f"     ~ {sutta_id:20} {was} → {now}  (delta {now - was:+d})")
    for sutta_id in added:
        print(f"     + {sutta_id:20} {new[sutta_id]}  (เคสใหม่)")
    for sutta_id in removed:
        print(f"     - {sutta_id:20} {old[sutta_id]}  (ไม่อยู่ใน SUTTAS แล้ว)")
    print(f"   รวม {sum(old.values()):,} → {sum(new.values()):,} segment")


async def main(url: str, update: bool) -> int:
    print(f"target: {url}")
    pinned = load_pins()
    if pinned is None and not update:
        print(f"\n❌ ไม่มี {SNAPSHOT_PATH.name} — เทสนี้เทียบค่าเป๊ะ ไม่มีค่าที่ pin ไว้ก็ตรวจไม่ได้")
        print("   วัดใหม่จากปลายทางที่เชื่อถือได้แล้วทบทวน diff:")
        print(f"   MCP_URL={url} .venv/bin/python scripts/{Path(__file__).name} --update")
        return 1
    if update:
        print(f"snapshot: {SNAPSHOT_PATH.name} — วัดใหม่ แล้วรายงาน diff ก่อนเขียนทับ")
    else:
        print(f"snapshot: {SNAPSHOT_PATH.name} — pin ไว้ {len(pinned)} สูตร")
    print()
    print(f"{'sutta':20} {'status':9} {'detail'}")
    print("-" * 78)

    measured: dict[str, int] = {}
    failures = 0
    async with Client(url) as client:
        for sutta_id in SUTTAS:
            count, detail = await measure(client, sutta_id)

            if count is None:
                print(f"{sutta_id:20} {'FAIL':9} {detail}")
                failures += 1
                continue

            measured[sutta_id] = count

            if update:
                print(f"{sutta_id:20} {'MEASURED':9} count={count} {detail}")
                continue

            want = pinned.get(sutta_id)
            if want is None:
                print(
                    f"{sutta_id:20} {'FAIL':9} ไม่มีค่า pin ใน snapshot — วัดได้ {count}"
                    " ถ้าถูกต้องให้รับด้วย --update"
                )
                failures += 1
            elif count != want:
                print(
                    f"{sutta_id:20} {'FAIL':9} segment_count={count} expected={want}"
                    f" delta={count - want:+d}  {detail}"
                )
                failures += 1
            else:
                print(f"{sutta_id:20} {'PASS':9} count={count} {detail}")

    print()
    if failures:
        print(f"❌ {failures}/{len(SUTTAS)} failed")
        if update:
            print(f"   ไม่เขียน {SNAPSHOT_PATH.name} — วัดไม่ครบ จะ pin ค่าที่วัดพลาดไว้ไม่ได้")
        return 1

    if update:
        report_diff(pinned, measured)
        SNAPSHOT_PATH.write_text(
            json.dumps(measured, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"── เขียน {SNAPSHOT_PATH.name} แล้ว ({len(measured)} สูตร)")
        return 0

    stale = [s for s in pinned if s not in SUTTAS]
    if stale:
        print(f"⚠️  snapshot มีสูตรที่ไม่อยู่ใน SUTTAS แล้ว: {', '.join(stale)} — ล้างด้วย --update")
    total = sum(measured.values())
    print(f"✅ all {len(SUTTAS)} suttas matched their pinned segment_count ({total:,} segments)")
    return 0


if __name__ == "__main__":
    args = set(sys.argv[1:])
    url = os.environ.get("MCP_URL", DEFAULT_URL)
    sys.exit(asyncio.run(main(url, update="--update" in args)))
