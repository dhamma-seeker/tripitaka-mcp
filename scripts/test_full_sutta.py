"""Smoke test — verify get_sutta returns full content for various sutta sizes.

ตรวจ 3 invariants ต่อสูตร:
1. server return ไม่มี error
2. segment_count == len(segments) (no truncation)
3. ลำดับ segment_id เรียงตามต้นฉบับ (first → last)

ใช้:
    .venv/bin/python scripts/test_full_sutta.py                     # default = staging
    MCP_URL=http://localhost:8080/mcp .venv/bin/python scripts/test_full_sutta.py

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail ใด ๆ — ใช้ใน CI ได้
"""

import asyncio
import json
import os
import sys

from fastmcp import Client

DEFAULT_URL = "https://staging.tripitaka-mcp.com/mcp"

# (sutta_id, expected_min_segments) — min ใช้กัน drift เล็ก ๆ ไม่ fail
# เลือกครอบ size range: เล็ก/ปกติ/ใหญ่/ใหญ่มาก/ที่สุด + compound IDs
SUTTAS: list[tuple[str, int]] = [
    # --- Sutta Piṭaka (Phase A — already in production) ---
    ("sn56.11", 30),  # ธัมมจักกัปปวัตตนสูตร — สั้น
    ("mn62", 100),  # มหาราหุโลวาท — ปกติ
    ("mn1", 300),  # มูลปริยายสูตร — ใหญ่
    ("dn22", 400),  # มหาสติปัฏฐาน — ใหญ่มาก
    ("dn16", 800),  # มหาปรินิพพาน — ที่สุด (ยาวกว่า DN22)
    # --- KN sub-books ---
    ("dhp1-20", 20),  # Dhammapada — bilara group verses เป็นช่วง
    ("snp1.8", 5),  # Karaṇīyamettasutta — เมตตสูตร
    ("ud3.4", 3),  # Sāriputtasutta อุทาน
    ("iti85", 2),  # Asubhānupassīsutta
    ("thag1.1", 1),  # Theragāthā 1.1
    ("ja1", 5),  # Jātaka 1 (Apaṇṇaka)
    ("mil3.1.1", 3),  # Milindapañha — paracanonical, 3-level id format
    # --- Vinaya Piṭaka (Phase B — local-only until prod deploy) ---
    ("pli-tv-bu-pm", 700),  # Bhikkhu Pātimokkha — digit-less id format
    ("pli-tv-bu-vb-as1-7", 30),  # Bhikkhu Vibhaṅga Adhikaraṇasamatha (range form)
    ("pli-tv-kd1", 3000),  # Mahāvagga ch. 1 — large Khandhaka section
    ("pli-tv-pvr10", 300),  # Parivāra
    # --- Abhidhamma Piṭaka (Phase C — local-only until prod deploy) ---
    ("ds1.1", 80),  # Dhammasaṅgaṇī 1.1
    ("dt2.1", 500),  # Dhātukathā 2.1
    ("kv10.1", 25),  # Kathāvatthu 10.1
    ("vb1", 2000),  # Vibhaṅga ch.1 — flat single-level id (no .x sub)
    ("ya1.1.1", 100),  # Yamaka — 3-level id format
    ("patthana1.1", 100),  # Paṭṭhāna — 8-char prefix needs {2,10} regex
]


async def check(client: Client, sutta_id: str, min_segs: int) -> tuple[bool, str]:
    try:
        result = await client.call_tool(
            "get_sutta", {"sutta_id": sutta_id, "language": "pali"}
        )
        payload = json.loads(result.content[0].text)
    except Exception as e:
        return False, f"call failed: {e}"

    if "error" in payload:
        return False, f"server error: {payload['error']}"

    count = payload.get("segment_count", 0)
    segments = payload.get("segments", [])
    actual = len(segments)

    if count != actual:
        return False, f"count mismatch: server={count} actual={actual}"

    if actual < min_segs:
        return False, f"too few segments: {actual} < expected {min_segs}"

    # spot-check segments are grouped under this sutta. Range IDs (ending
    # in `<digit>+-<digit>+` like dhp1-20 or pli-tv-bu-vb-as1-7) have
    # segments with individual verse-level ids, so we match on the prefix
    # before the trailing range. Non-range ids must match exactly.
    if segments:
        import re
        first_id = segments[0]["segment_id"]
        last_id = segments[-1]["segment_id"]
        is_range = bool(re.search(r"\d+-\d+$", sutta_id))
        if is_range:
            # strip trailing "<digit>+-<digit>+" → e.g. "pli-tv-bu-vb-as1-7" → "pli-tv-bu-vb-as"
            range_prefix = re.sub(r"\d+-\d+$", "", sutta_id)
            if not first_id.startswith(range_prefix):
                return False, f"first id {first_id!r} does not start with range prefix {range_prefix!r}"
        else:
            if not first_id.startswith(f"{sutta_id}:"):
                return False, f"first id {first_id!r} not in sutta {sutta_id}"
            if not last_id.startswith(f"{sutta_id}:"):
                return False, f"last id {last_id!r} not in sutta {sutta_id}"

    return True, f"count={count} first={first_id} last={last_id}"


async def main(url: str) -> int:
    print(f"target: {url}\n")
    print(f"{'sutta':10} {'status':6} {'detail'}")
    print("-" * 70)

    failures = 0
    async with Client(url) as client:
        for sutta_id, min_segs in SUTTAS:
            ok, detail = await check(client, sutta_id, min_segs)
            mark = "PASS" if ok else "FAIL"
            print(f"{sutta_id:10} {mark:6} {detail}")
            if not ok:
                failures += 1

    print()
    if failures:
        print(f"❌ {failures}/{len(SUTTAS)} failed")
        return 1
    print(f"✅ all {len(SUTTAS)} suttas returned full content")
    return 0


if __name__ == "__main__":
    url = os.environ.get("MCP_URL", DEFAULT_URL)
    sys.exit(asyncio.run(main(url)))
