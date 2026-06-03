"""Test — get_sutta pagination (outline / around+window / segment_range / offset+limit).

ตรวจ contract ของ pagination ที่เพิ่มเข้า get_sutta:
1. default (ไม่ใส่ selector) = ทั้งสูตร, backward-compat (segment_count == len == total)
2. mode="outline" = TOC ไม่มี text, Σ section_count == total_segments
3. around+window = window รอบ segment_id (search→read)
4. segment_range = inclusive slice ระหว่าง 2 segment_id
5. offset+limit = ordinal paging ต่อเนื่อง (next_offset)
6. error cases (around มั่ว / selector ซ้อน / range ไม่มี '..')

slicing/outline เป็น pure-Python หลัง fetch (ORDER BY seg.id เหมือนกันทั้ง 2 backend)
→ ผลตรงกันเป๊ะข้าม Postgres/SQLite. ตั้ง MCP_URL_B เพื่อ deep-equal เทียบ 2 backend.

ใช้:
    MCP_URL=http://localhost:8080/mcp .venv/bin/python scripts/test_pagination.py
    # cross-backend parity (optional):
    MCP_URL=<pg-url> MCP_URL_B=<sqlite-url> .venv/bin/python scripts/test_pagination.py

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail ใด ๆ
"""

import asyncio
import json
import os
import sys

from fastmcp import Client

DEFAULT_URL = "https://mcp.tripitaka-mcp.com/mcp"

# สูตรที่ใช้ทดสอบ — ครอบ 2-level (dn22), 3-level (dn16), range-format (dhp1-20),
# และสูตรใหญ่มาก (pli-tv-kd1)
DN16 = "dn16"
DN22 = "dn22"
DHP = "dhp1-20"
KD1 = "pli-tv-kd1"


async def call(client: Client, **kwargs) -> dict:
    """เรียก get_sutta คืน payload (dict). kwargs ส่งตรงเป็น tool args."""
    result = await client.call_tool("get_sutta", kwargs)
    return json.loads(result.content[0].text)


def _seg_ids(payload: dict) -> list[str]:
    return [s["segment_id"] for s in payload.get("segments", [])]


async def run_suite(client: Client) -> list[tuple[str, bool, str]]:
    """รัน assertion ทั้งหมดกับ 1 backend. คืน list ของ (name, ok, detail)."""
    out: list[tuple[str, bool, str]] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        out.append((name, bool(cond), detail))

    # --- baselines (full sutta) — ใช้คำนวณ index เทียบ ---
    full16 = await call(client, sutta_id=DN16, language="pali")
    full22 = await call(client, sutta_id=DN22, language="pali")
    ids22 = _seg_ids(full22)

    # 1) default = backward-compat
    total16 = full16.get("total_segments")
    check(
        "default: segment_count==len==total, has_more=False",
        total16 is not None
        and full16.get("segment_count") == len(full16.get("segments", [])) == total16
        and full16.get("page", {}).get("has_more") is False
        and full16.get("page", {}).get("next_offset") is None
        and full16.get("page", {}).get("offset") == 0,
        f"total={total16}",
    )

    # 2) outline dn16 — section per '.0' header (40 subtopics), TOC ไม่มี text
    out16 = await call(client, sutta_id=DN16, mode="outline")
    sections = out16.get("sections", [])
    sum_counts = sum(s["segment_count"] for s in sections)
    no_text = all(
        "text_pali" not in s and "text_english" not in s and "segments" not in s
        for s in sections
    )
    # ทุก section ใน '.0' mode มี title (จาก header) + header_segment_id ลงท้าย '.0'
    all_titled = all(s["title"].get("pali") or s["title"].get("english") for s in sections)
    headers_dot0 = all(s.get("header_segment_id", "").endswith(".0") for s in sections)
    check(
        "outline dn16: 40 '.0' sections, Σcount==total, no text, all titled",
        out16.get("mode") == "outline"
        and out16.get("total_segments") == total16
        and sum_counts == total16
        and out16.get("section_count") == len(sections) == 40
        and no_text
        and all_titled
        and headers_dot0,
        f"sections={len(sections)} Σ={sum_counts} titled={all_titled}",
    )
    # section แรกขยายกลับไป index 0 (กลืน preamble) — first_segment_id == full[0]
    check(
        "outline dn16: section[0] absorbs preamble (offset 0, first==full[0])",
        sections and sections[0]["offset"] == 0
        and sections[0]["first_segment_id"] == _seg_ids(full16)[0]
        and sections[0]["title"].get("pali", "").startswith("1."),
        f"first={sections[0]['first_segment_id'] if sections else None} "
        f"title={sections[0]['title'].get('pali') if sections else None}",
    )

    # 3) outline dhp1-20 (range-format → group by colon-prefix)
    outdhp = await call(client, sutta_id=DHP, mode="outline")
    dhp_sections = outdhp.get("sections", [])
    keys = [s["key"] for s in dhp_sections]
    check(
        "outline dhp1-20: grouped by member prefix (dhpN), 20 verses",
        len(dhp_sections) == 20
        and all(k.startswith("dhp") for k in keys)
        and sum(s["segment_count"] for s in dhp_sections) == outdhp.get("total_segments"),
        f"sections={len(dhp_sections)} keys[:3]={keys[:3]}",
    )

    # 4) around + window (search→read)
    anchor = "dn22:18.1"
    if anchor in ids22:
        idx = ids22.index(anchor)
        w = 5
        around22 = await call(client, sutta_id=DN22, around=anchor, window=w)
        got = _seg_ids(around22)
        expect = ids22[max(0, idx - w): idx + w + 1]
        page = around22.get("page", {})
        check(
            "around dn22:18.1 window=5: centered slice matches full[idx-5:idx+6]",
            got == expect
            and around22.get("total_segments") == len(ids22)
            and page.get("offset") == max(0, idx - w)
            and page.get("returned") == len(expect)
            and page.get("has_more") is (idx + w + 1 < len(ids22)),
            f"anchor_idx={idx} returned={len(got)}",
        )
    else:
        check("around dn22:18.1", False, f"anchor {anchor} not in dn22")

    # 5) segment_range (inclusive)
    a, b = "dn16:2.1.0", "dn16:2.2.8"
    ids16 = _seg_ids(full16)
    if a in ids16 and b in ids16:
        rng = await call(client, sutta_id=DN16, segment_range=f"{a}..{b}")
        got = _seg_ids(rng)
        expect = ids16[ids16.index(a): ids16.index(b) + 1]
        check(
            "segment_range dn16:2.1.0..dn16:2.2.8: inclusive slice",
            got == expect and got and got[0] == a and got[-1] == b,
            f"returned={len(got)} first={got[0] if got else None} last={got[-1] if got else None}",
        )
    else:
        check("segment_range dn16", False, f"endpoints {a}/{b} not in dn16")

    # 6) offset + limit paging ต่อเนื่อง
    p1 = await call(client, sutta_id=KD1, offset=0, limit=100)
    page1 = p1.get("page", {})
    total_kd = p1.get("total_segments", 0)
    p2 = await call(client, sutta_id=KD1, offset=100, limit=100)
    full_kd_ids_head = _seg_ids(p1) + _seg_ids(p2)
    check(
        "offset/limit kd1: page1=100 has_more, next_offset=100, page2 continues",
        page1.get("returned") == 100
        and page1.get("has_more") is True
        and page1.get("next_offset") == 100
        and _seg_ids(p2)[0] != _seg_ids(p1)[0]
        and len(full_kd_ids_head) == 200
        and len(set(full_kd_ids_head)) == 200,  # ไม่ทับซ้อน
        f"total={total_kd}",
    )

    # 7) error cases
    e_around = await call(client, sutta_id=DN22, around="dn22:9999.9")
    e_multi = await call(client, sutta_id=DN22, around=anchor, offset=5)
    e_range = await call(client, sutta_id=DN16, segment_range="dn16:2.1.0")
    check("error: around bogus id → error", "error" in e_around, e_around.get("error", "")[:50])
    check("error: two selectors → error", "error" in e_multi, e_multi.get("error", "")[:50])
    check("error: segment_range without '..' → error", "error" in e_range, e_range.get("error", "")[:50])

    return out


async def parity_check(url_a: str, url_b: str) -> list[tuple[str, bool, str]]:
    """deep-equal payload เดียวกันจาก 2 backend (ต้องตรงกันเป๊ะ)."""
    cases = [
        ("outline dn16", dict(sutta_id=DN16, mode="outline")),
        ("around dn22:18.1", dict(sutta_id=DN22, around="dn22:18.1", window=5)),
        ("range dn16", dict(sutta_id=DN16, segment_range="dn16:2.1.0..dn16:2.2.8")),
    ]
    results = []
    async with Client(url_a) as ca, Client(url_b) as cb:
        for name, kw in cases:
            pa = await call(ca, **kw)
            pb = await call(cb, **kw)
            # cross_reference เป็น URL อาจต่าง domain ระหว่าง backend → ตัดออกก่อนเทียบ
            pa.pop("cross_reference", None)
            pb.pop("cross_reference", None)
            results.append((f"parity: {name}", pa == pb,
                            "deep-equal" if pa == pb else "DIFF"))
    return results


async def main() -> int:
    url = os.environ.get("MCP_URL", DEFAULT_URL)
    url_b = os.environ.get("MCP_URL_B")

    print(f"target: {url}\n")
    print(f"{'check':62} {'status'}")
    print("-" * 78)

    async with Client(url) as client:
        results = await run_suite(client)

    if url_b:
        print(f"\n(parity vs {url_b})")
        results += await parity_check(url, url_b)

    failures = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"{name:62} {mark}  {detail}")
        if not ok:
            failures += 1

    print()
    if failures:
        print(f"❌ {failures}/{len(results)} failed")
        return 1
    print(f"✅ all {len(results)} pagination checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
