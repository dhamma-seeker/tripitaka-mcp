"""Regression test — guard the `survey_corpus` exhaustiveness guarantee.

`survey_corpus` returns `lexical.complete: true` as a HARD guarantee that no
segment was dropped for the chosen match_scope. That promise is the whole point
of the tool (anti-hallucination via verifiable, exhaustive counts) — so if the
index or corpus ever drifts while the tool still claims `complete: true`, that
is a silent, dangerous regression. This test pins the exact counts for a few
known terms so drift fails loudly.

Per case it checks 3 invariants:
1. no top-level error
2. `lexical.complete` is True (the guarantee itself)
3. `total_segments` / `total_suttas` match the verified golden counts EXACTLY
   (not a min — an exact pin, because "complete" means the number is exact)

Golden counts verified 2026-06-03 on the SQLite dump and previously on docker
Postgres (identical across backends — see PROGRESS.md survey_corpus entry).
Run against BOTH backends by pointing MCP_URL at a server started with the
respective TRIPITAKA_BACKEND.

ใช้:
    .venv/bin/python scripts/test_survey_counts.py                  # default = production
    MCP_URL=http://localhost:8080/mcp .venv/bin/python scripts/test_survey_counts.py

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail ใด ๆ — ใช้ใน CI ได้
"""

import asyncio
import json
import os
import sys

from fastmcp import Client

DEFAULT_URL = "https://mcp.tripitaka-mcp.com/mcp"

# (keyword, language, match_scope, expected_segments, expected_suttas)
# word = exact form; stem = prefix → inflections + compounds (higher recall).
SURVEYS: list[tuple[str, str, str, int, int]] = [
    ("kusinārā", "pali", "word", 11, 4),
    ("kusinārā", "pali", "stem", 67, 26),
    ("ānāpānassati", "pali", "word", 47, 20),
    ("ānāpānassati", "pali", "stem", 164, 46),
]

# A term that does not occur — the guarantee must still hold: complete with a
# genuine zero, never a silent "I gave up" zero.
NONEXISTENT = ("zxqwvbqq", "pali", "word")


async def check_survey(
    client: Client, kw: str, lang: str, scope: str, exp_segs: int, exp_suttas: int
) -> tuple[bool, str]:
    try:
        result = await client.call_tool(
            "survey_corpus",
            {"keyword": kw, "language": lang, "match_scope": scope, "mode": "fast"},
        )
        payload = json.loads(result.content[0].text)
    except Exception as e:
        return False, f"call failed: {e}"

    if "error" in payload:
        return False, f"server error: {payload['error']}"

    lex = payload.get("lexical")
    if not isinstance(lex, dict):
        return False, "missing lexical block"

    if lex.get("complete") is not True:
        return False, f"NOT complete (complete={lex.get('complete')!r}) — guarantee broken"

    segs = lex.get("total_segments")
    suttas = lex.get("total_suttas")
    if segs != exp_segs or suttas != exp_suttas:
        return False, f"count drift: got {segs}/{suttas}, expected {exp_segs}/{exp_suttas}"

    return True, f"complete=True segs={segs} suttas={suttas}"


async def check_nonexistent(client: Client, kw: str, lang: str, scope: str) -> tuple[bool, str]:
    try:
        result = await client.call_tool(
            "survey_corpus",
            {"keyword": kw, "language": lang, "match_scope": scope, "mode": "fast"},
        )
        payload = json.loads(result.content[0].text)
    except Exception as e:
        return False, f"call failed: {e}"

    if "error" in payload:
        return False, f"server error: {payload['error']}"

    lex = payload.get("lexical", {})
    if lex.get("complete") is not True:
        return False, f"NOT complete on empty result (complete={lex.get('complete')!r})"
    if lex.get("total_segments") != 0:
        return False, f"expected 0 segments, got {lex.get('total_segments')}"

    return True, "complete=True segs=0 (genuine zero)"


async def main(url: str) -> int:
    print(f"target: {url}\n")
    print(f"{'survey':28} {'status':6} {'detail'}")
    print("-" * 72)

    failures = 0
    async with Client(url) as client:
        for kw, lang, scope, exp_segs, exp_suttas in SURVEYS:
            ok, detail = await check_survey(client, kw, lang, scope, exp_segs, exp_suttas)
            mark = "PASS" if ok else "FAIL"
            print(f"{kw + ' [' + scope + ']':28} {mark:6} {detail}")
            if not ok:
                failures += 1

        kw, lang, scope = NONEXISTENT
        ok, detail = await check_nonexistent(client, kw, lang, scope)
        mark = "PASS" if ok else "FAIL"
        print(f"{kw + ' [' + scope + ']':28} {mark:6} {detail}")
        if not ok:
            failures += 1

    total = len(SURVEYS) + 1
    print()
    if failures:
        print(f"❌ {failures}/{total} failed")
        return 1
    print(f"✅ all {total} surveys exact + complete:true guarantee intact")
    return 0


if __name__ == "__main__":
    url = os.environ.get("MCP_URL", DEFAULT_URL)
    sys.exit(asyncio.run(main(url)))
