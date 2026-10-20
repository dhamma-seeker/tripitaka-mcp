"""Prompt-level test — ให้โมเดลจริงตัดสินใจเองว่าจะเรียกเครื่องมือไหน

ต่างจาก test_definitions.py / test_verify_quote.py ที่เรียกฟังก์ชันตรงๆ:
ไฟล์นี้ spawn `claude` CLI ในเครื่อง ต่อ MCP server จริงผ่าน --mcp-config
แล้วปล่อยให้โมเดลเลือกเครื่องมือเอง จึงวัดได้ว่า tool description +
routing rule ที่เราเขียนไว้ "ติด" จริงไหม

ใช้ subscription ของ CLI ไม่ใช่ API key จึงไม่มีค่า token ต่อรอบ
ต้อง `claude login` ให้ session ยังไม่หมดอายุก่อนรัน

กันการปนเปื้อน: รันใน cwd ว่าง (ไม่ให้เจอ CLAUDE.md ของ repo),
--strict-mcp-config (ไม่เอา MCP อื่นของเครื่อง), --restricted (ตัด Bash ทิ้ง)

**ต้องบอกปลายทางเองเสมอ** — ไม่มี default ให้เผลอ (`--local`, `--url`, หรือ MCP_URL)
โดยปกติสิ่งที่อยากเทสคือโค้ดในไดเรกทอรีนี้ → `--local` แล้วต้องสตาร์ท server เอง

ใช้:
    .venv/bin/python scripts/test_mcp_prompts.py --local --dry-run
    .venv/bin/python scripts/test_mcp_prompts.py --local             # ของที่เพิ่งแก้
    .venv/bin/python scripts/test_mcp_prompts.py --local --case B1 --case C4
    .venv/bin/python scripts/test_mcp_prompts.py --local --model haiku  # เทียบโมเดลต่ำ
    .venv/bin/python scripts/test_mcp_prompts.py --local --repeat 3  # วัดความไม่นิ่ง
    .venv/bin/python scripts/test_mcp_prompts.py --url https://mcp.<domain>/mcp

บรรทัดหัวที่พิมพ์ `url=` คือสิ่งที่กำลังเทสจริง — ดูมันก่อนเชื่อผล
ยิงไปเครื่องที่ไม่ใช่ localhost จะขึ้นคำเตือนสีแดงว่ากำลังดูโค้ดที่ deploy อยู่

ท้ายรอบยังพิมพ์ "อัตรารูปแบบลิงก์" ทุกครั้ง — สูตรที่โมเดลเอ่ยชื่อในคำตอบ
แนบลิงก์ reader ให้จริงกี่ครั้ง และเป็น markdown ที่คลิกได้กี่ครั้ง (ดู LINK_MIN_RATE)

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail
เคสที่ติดป้าย `known_fail` ใน yaml รายงานผลตามจริงแต่ไม่นับเข้า exit code
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = ROOT / "scripts" / "prompt_cases.yaml"
# ไม่มี default โดยตั้งใจ — เคยตั้งเป็น URL ของ prod แล้วมันกัด: สั่งด้วย
# MCP_URL=... (ซึ่งสคริปต์นี้ไม่เคยอ่าน) เทสก็วิ่งไป prod เงียบๆ = ทดสอบโค้ดเก่า
# บนเครื่องจริง โดยเข้าใจว่ากำลังเทสของที่เพิ่งแก้
LOCAL_URL = "http://localhost:8080/mcp"
MCP_URL_ENV = "MCP_URL"
SERVER = "tripitaka"
PREFIX = f"mcp__{SERVER}__"
TURN_TIMEOUT = 600

C_OK, C_BAD, C_DIM, C_OFF = "\033[32m", "\033[31m", "\033[90m", "\033[0m"
C_WARN = "\033[33m"


def _is_loopback(url: str) -> bool:
    host = urllib.parse.urlsplit(url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


class CliError(RuntimeError):
    pass


# ── การเรียก CLI ──────────────────────────────────────────────────────────


def claude(prompt, workdir, *, model, effort, mcp_config=None, allowed=(),
           resume=None, timeout=TURN_TIMEOUT):
    """รัน claude -p หนึ่งครั้ง คืน list ของ event (stream-json)

    prompt ส่งทาง stdin เพราะ --allowedTools เป็น variadic
    ถ้าวางเป็น positional มันจะกลืน prompt ไปเป็นชื่อ tool
    """
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose",
           "--model", model, "--effort", effort, "--restricted"]
    if mcp_config:
        cmd += ["--mcp-config", str(mcp_config), "--strict-mcp-config"]
    if resume:
        cmd += ["--resume", resume]
    if allowed:
        cmd += ["--allowedTools", *allowed]

    proc = subprocess.run(
        cmd, cwd=workdir, input=prompt, capture_output=True, text=True, timeout=timeout
    )
    events = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not events:
        raise CliError((proc.stderr or proc.stdout or "ไม่มี output").strip()[:400])
    return events


def parse(events):
    """ดึงสิ่งที่ต้องตรวจออกจาก event stream"""
    session, answer, calls, pending = None, "", [], {}
    for e in events:
        t = e.get("type")
        if t == "system" and e.get("subtype") == "init":
            session = e.get("session_id")
        elif t == "assistant":
            for b in e["message"]["content"]:
                if b.get("type") == "tool_use" and b["name"].startswith(PREFIX):
                    rec = {"name": b["name"][len(PREFIX):], "input": b.get("input"),
                           "result": None}
                    pending[b["id"]] = rec
                    calls.append(rec)
        elif t == "user":
            content = e["message"].get("content")
            for b in content if isinstance(content, list) else []:
                rec = pending.get(b.get("tool_use_id"))
                if rec is None or b.get("type") != "tool_result":
                    continue
                rec["result"] = _payload(b.get("content"))
        elif t == "result":
            if e.get("is_error"):
                raise CliError(str(e.get("result"))[:400])
            answer = str(e.get("result") or "")
            session = e.get("session_id", session)
    return session, answer, calls


def _payload(content):
    """tool_result content → dict ถ้าเป็น JSON"""
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
    if not isinstance(content, str):
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


# ── การตรวจ ───────────────────────────────────────────────────────────────


# ── รูปแบบลิงก์ของการอ้างอิง ───────────────────────────────────────────────
#
# `instructions` ของ server สั่งไว้สองที่: "EVERY time you NAME a sutta ... you
# MUST attach the Tripitaka reader link" และ "Always render links as **clickable
# markdown**" แต่ `must_cite` ตรวจแค่ว่าสตริงชื่อสูตรโผล่ในคำตอบ เคสจึงขึ้น PASS
# แม้โมเดลไม่แนบลิงก์เลย หรือแนบเป็น URL เปล่าที่คลิกไม่ได้ เช่น
#     🔗 https://tripitaka-mcp.com/read/sn56.11#sn56.11:2.1
# ซึ่งไม่ใช่ `[sn56.11](https://tripitaka-mcp.com/read/sn56.11#sn56.11:2.1)`
#
# ตรงนี้วัดต่ออีกชั้น ต่อ "สูตรหนึ่งตัวที่เอ่ยชื่อในคำตอบหนึ่ง" (ชื่อซ้ำในคำตอบเดียว
# นับหนึ่งหน่วย): (ก) มีลิงก์ reader ของสูตรนั้นในคำตอบไหม (ข) ลิงก์นั้นเป็น markdown
# ที่คลิกได้ไหม — วัดทุกเคสโดยไม่ต้องประกาศใน yaml เพราะเป็นงานสตริงล้วน ไม่มีต้นทุน

# ตัวย่อชุดคัมภีร์ที่มีในคลัง (prefix ของ segment_id) — ใช้กันชื่อสูตรจริงออกจาก
# ตัวเลขทั่วไปในคำตอบ · id ของวินัย (`pli-tv-...`) มีขีดคั่น ไม่เข้ารูปแบบนี้
# จึงยังไม่ถูกนับ ถ้าวันหนึ่งต้องนับด้วยให้เพิ่ม pattern แยก
SUTTA_COLLECTIONS = frozenset("""
    sn mn dn an kp dhp ud iti snp thag thig ja mil bv cp pv vv
    ps ya kv ds vb dt mnd cnd pe ne pp patthana
""".split())

# ชื่อสูตรแบบ `sn56.11` (ติดกัน) หรือ `SN 56.11` (คนเขียน) — เอา `:segment` ทิ้ง
# เพราะหน่วยที่วัดคือตัวสูตร
_SUTTA_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{2,8})([ \u00a0]?)(\d+(?:\.\d+)*)")
_MD_LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)")
_BARE_URL_RE = re.compile(r"https?://[^\s)\]<>`\"']+")
_READER_PATH_RE = re.compile(r"/read/([A-Za-z][A-Za-z0-9.\-]*)")

# เกณฑ์ขั้นต่ำของอัตราข้างล่าง — `None` = พิมพ์อัตราให้ดูเฉยๆ ไม่ตัดสินผ่าน/ตก
# ยังเป็น None ตั้งแต่ 2026-10-19 เพราะวัดแล้วได้ ลิงก์ ~8/9 แต่ markdown ที่คลิกได้
# แค่ 2–4/9 (~30%) ถ้าตั้งเป็นเกณฑ์วันนี้ ชุดเทสจะแดงทุกรอบจนคนเลิกดูผล
# (Decision 3 ของ 2026-10-18 เรื่อง known-fail)
# เมื่อแก้ `instructions` แล้วอัตรา markdown ขึ้นไปนิ่ง ให้ใส่ตัวเลข (เช่น 0.8)
# แล้วเขียนวันที่ตั้งไว้ในคอมเมนต์นี้ด้วย — ตั้งแล้วอัตราที่ต่ำกว่าเกณฑ์จะทำให้ exit 1
LINK_MIN_RATE = None
MARKDOWN_MIN_RATE = None


def _prose(answer: str) -> str:
    """ตัด URL ออกจากคำตอบ เหลือเฉพาะส่วนที่คนอ่าน

    ของ markdown ตัดแค่ปลายทาง เก็บข้อความที่คลิกได้ไว้ — `[SN 56.11](...)`
    ถือว่า "เอ่ยชื่อ" เหมือนกัน ถ้าไม่ตัด URL ก่อน ชื่อสูตรใน URL จะถูกนับเป็น
    การเอ่ยชื่อ แล้วทุกลิงก์จะดูเหมือนทำตามกฎเสมอ
    """
    return _BARE_URL_RE.sub(" ", re.sub(r"\]\(\s*<?[^)]*\)", "] ", answer))


def _named_suttas(answer: str) -> list[str]:
    """ชื่อสูตรที่โมเดลเอ่ยในเนื้อคำตอบ → id ตัวเล็กติดกัน เรียงแล้วไม่ซ้ำ"""
    found = set()
    for pre, sep, num in _SUTTA_RE.findall(_prose(answer)):
        if pre.lower() not in SUTTA_COLLECTIONS:
            continue
        # ถ้ามีช่องว่างคั่น ตัวย่อต้องขึ้นต้นด้วยตัวใหญ่ ("AN 4.42") — กัน
        # คำนำหน้าคำนามอังกฤษอย่าง "an 8-fold path" ไม่ให้กลายเป็น AN 8
        if sep and not pre[0].isupper():
            continue
        found.add(f"{pre.lower()}{num}")
    return sorted(found)


def _reader_targets(urls) -> set[str]:
    """URL ไหนเป็นลิงก์ reader ของสูตรไหน — `/read/<sutta_id>[#segment]`"""
    return {m.group(1).lower() for u in urls
            if (m := _READER_PATH_RE.search(u))}


def link_style(answer: str) -> dict:
    """วัดรูปแบบลิงก์ของคำตอบเดียว

    คืน {named, linked, markdown} เป็นลิสต์ของ sutta_id:
      named    — เอ่ยชื่อในเนื้อคำตอบ
      linked   — มีลิงก์ reader ของสูตรนั้น (markdown หรือ URL เปล่าก็นับ)
      markdown — ลิงก์นั้นเป็น markdown ที่คลิกได้
    """
    md = _MD_LINK_RE.findall(answer)
    named = _named_suttas(answer)
    linked = _reader_targets(md + _BARE_URL_RE.findall(answer))
    clickable = _reader_targets(md)
    return {"named": named,
            "linked": [s for s in named if s in linked],
            "markdown": [s for s in named if s in clickable]}


def link_note(style: dict) -> str:
    """บรรทัดสรุปรูปแบบลิงก์ของคำตอบเดียว — บอกชื่อสูตรที่ยังไม่ทำตามกฎด้วย"""
    n = len(style["named"])
    line = (f"รูปแบบลิงก์: ลิงก์ {len(style['linked'])}/{n} · "
            f"markdown {len(style['markdown'])}/{n}")
    nolink = [s for s in style["named"] if s not in style["linked"]]
    bare = [s for s in style["linked"] if s not in style["markdown"]]
    if nolink:
        line += f" · ไม่มีลิงก์: {', '.join(nolink)}"
    if bare:
        line += f" · URL เปล่า: {', '.join(bare)}"
    return line


def report_link_rates(styles) -> list[str]:
    """พิมพ์อัตรารวมของทั้งรอบ คืนลิสต์ปัญหา (ว่างเสมอตราบที่เกณฑ์ยังเป็น None)"""
    named = sum(len(s["named"]) for s in styles)
    print(f"\n{C_DIM}รูปแบบลิงก์ — กฎใน instructions: เอ่ยชื่อสูตรแล้วต้องแนบ"
          f"ลิงก์ reader เป็น markdown ที่คลิกได้{C_OFF}")
    if not named:
        print(f"  {C_DIM}ไม่มีคำตอบไหนเอ่ยชื่อสูตร — ไม่มีอะไรให้วัด{C_OFF}")
        return []
    linked = sum(len(s["linked"]) for s in styles)
    md = sum(len(s["markdown"]) for s in styles)
    print(f"  สูตรที่เอ่ยถึง {named} · ลิงก์ {linked}/{named} ({linked/named:.0%})"
          f" · markdown {md}/{named} ({md/named:.0%})")
    problems = []
    for label, got, floor in (("ลิงก์", linked / named, LINK_MIN_RATE),
                              ("markdown", md / named, MARKDOWN_MIN_RATE)):
        if floor is None:
            continue
        if got < floor:
            problems.append(f"อัตรา{label} {got:.0%} ต่ำกว่าเกณฑ์ {floor:.0%}")
    if LINK_MIN_RATE is None and MARKDOWN_MIN_RATE is None:
        print(f"  {C_DIM}(รายงานเฉยๆ ยังไม่เป็นเกณฑ์ผ่าน/ตก — ดู LINK_MIN_RATE){C_OFF}")
    return problems


def check_turn(expect, calls, answer):
    """ตรวจแบบกลไกล้วน — คืนลิสต์ปัญหาที่เจอ"""
    problems = []
    names = [c["name"] for c in calls]

    for t in expect.get("tools_called", []):
        if t not in names:
            problems.append(f"ไม่ได้เรียก {t} (เรียก: {names or 'ไม่เรียกอะไรเลย'})")
    for t in expect.get("tools_not_called", []):
        if t in names:
            problems.append(f"เรียก {t} ทั้งที่ไม่ควรเรียก")

    for tool, fields in (expect.get("tool_result") or {}).items():
        hit = next((c for c in calls if c["name"] == tool and c["result"]), None)
        if not hit:
            problems.append(f"ไม่มีผลลัพธ์จาก {tool} ให้ตรวจ")
            continue
        for key, want in fields.items():
            got = hit["result"].get(key)
            if got != want:
                problems.append(f"{tool}.{key} = {got!r} ควรเป็น {want!r}")

    low = answer.lower()
    for s in expect.get("must_cite", []):
        if s.lower() not in low:
            problems.append(f"คำตอบไม่ได้อ้าง {s!r}")
    for s in expect.get("must_not_say", []):
        if s.lower() in low:
            problems.append(f"คำตอบพูดสิ่งที่ห้ามพูด: {s!r}")
    return problems


JUDGE_INSTRUCTION = (
    "ตอบกลับเป็น JSON บรรทัดเดียวเท่านั้น รูปแบบ "
    '{"pass": true|false, "reason": "เหตุผลสั้นๆ ไม่เกิน 2 ประโยค"} '
    "ห้ามมีข้อความอื่นนอก JSON"
)


def judge(rubric, answer, calls, workdir, model, effort):
    """ให้โมเดลอีกตัวตัดสินเกณฑ์ที่เขียนเป็นภาษาคน — ไม่ต่อ MCP"""
    # ต้องให้ judge เห็น "อะไรถูกเรียกด้วยอาร์กิวเมนต์อะไร" ไม่ใช่แค่ผลลัพธ์
    # ไม่งั้น judge จะกล่าวหาผิดว่าโมเดลแต่งข้อมูล ทั้งที่ไปดึงมาเองด้วยเครื่องมืออื่น
    # และตัดผลลัพธ์ทีละตัว ไม่ใช่ตัดก้อนเดียวจนตัวท้ายๆ หายหมด
    tools_dump = json.dumps(
        [{"name": c["name"], "input": c["input"],
          "result": json.dumps(c["result"], ensure_ascii=False)[:2500]}
         for c in calls],
        ensure_ascii=False,
    )
    prompt = (
        "คุณกำลังตรวจคำตอบของผู้ช่วย AI ตัวหนึ่ง ตัดสินตามเกณฑ์เท่านั้น\n\n"
        f"── เกณฑ์ ──\n{rubric}\n\n"
        f"── สิ่งที่เครื่องมือคืนมาจริง ──\n{tools_dump}\n\n"
        f"── คำตอบที่ต้องตรวจ ──\n{answer}\n\n{JUDGE_INSTRUCTION}"
    )
    _, out, _ = parse(claude(prompt, workdir, model=model, effort=effort))
    start, end = out.find("{"), out.rfind("}")
    if start == -1 or end <= start:
        return False, f"judge ไม่ได้ตอบ JSON: {out[:100]}"
    try:
        v = json.loads(out[start:end + 1])
    except json.JSONDecodeError:
        return False, f"judge ตอบ JSON ไม่ถูก: {out[start:start+100]}"
    return bool(v.get("pass")), str(v.get("reason", ""))


# ── ตัวขับ ────────────────────────────────────────────────────────────────


def run_case(case, workdir, mcp_config, allowed, model, judge_model, effort):
    problems, notes, answers, styles, session = [], [], [], [], None
    for i, turn in enumerate(case["turns"], 1):
        events = claude(turn["prompt"], workdir, model=model, effort=effort,
                        mcp_config=mcp_config, allowed=allowed, resume=session)
        session, answer, calls = parse(events)
        answers.append({"prompt": turn["prompt"], "answer": answer,
                        "calls": [{"name": c["name"], "input": c["input"]} for c in calls]})
        expect = turn.get("expect") or {}
        tag = f"turn{i}: " if len(case["turns"]) > 1 else ""
        notes.append(f"{tag}เรียก: {[c['name'] for c in calls] or '—'}")
        problems += [tag + p for p in check_turn(expect, calls, answer)]
        # วัดทุก turn — รายงานเฉยๆ ไม่เข้า problems (ดู LINK_MIN_RATE)
        style = link_style(answer)
        styles.append(style)
        if style["named"]:
            notes.append(tag + link_note(style))
        if expect.get("judge"):
            ok, why = judge(expect["judge"], answer, calls, workdir, judge_model, effort)
            (notes if ok else problems).append(f"{tag}judge{'' if ok else ''}: {why}")
    return problems, notes, answers, styles


def main():
    # ไม่ใช่ tty แล้ว stdout จะถูก buffer จนจบ — รันเบื้องหลังจะมองไม่เห็นอะไรเลย
    sys.stdout.reconfigure(line_buffering=True)

    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("MCP_URL"),
                    help="ปลายทางที่จะเทส (หรือตั้ง MCP_URL) — ต้องระบุเอง ไม่มีค่าเริ่มต้น")
    ap.add_argument("--local", action="store_true",
                    help=f"ทางลัดของ --url {LOCAL_URL}")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--judge-model", default="opus")
    ap.add_argument("--effort", default="high",
                    choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--case", action="append", default=[],
                    help="รันเฉพาะ id ที่ขึ้นต้นด้วยค่านี้ (ใส่ซ้ำได้)")
    ap.add_argument("--repeat", type=int, default=1, help="รันแต่ละเคสกี่รอบ")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default="", help="เขียนผลลง JSON")
    args = ap.parse_args()

    if args.local:
        if args.url and args.url != LOCAL_URL:
            print(f"{C_BAD}--local ขัดกับ --url/{MCP_URL_ENV}={args.url}{C_OFF}")
            return 1
        args.url = LOCAL_URL
    if not args.url:
        print(f"{C_BAD}ต้องบอกก่อนว่าจะเทสที่ไหน{C_OFF} — สคริปต์นี้ไม่มีปลายทางเริ่มต้น\n"
              f"  เครื่องตัวเอง : --local  (= {LOCAL_URL})\n"
              "  ที่อื่น        : --url <URL>  หรือ  MCP_URL=<URL>\n"
              "ที่ไม่มี default เพราะเคยตั้งเป็น prod แล้วเผลอเทสโค้ดเก่าบนเครื่องจริง")
        return 1
    if not _is_loopback(args.url):
        print(f"{C_BAD}⚠️  กำลังเทสเครื่องที่ไม่ใช่ localhost: {args.url}{C_OFF}\n"
              f"{C_BAD}   สิ่งที่เห็นคือโค้ดที่ deploy อยู่ ไม่ใช่โค้ดในไดเรกทอรีนี้{C_OFF}\n")

    if not shutil.which("claude"):
        print("ไม่พบคำสั่ง claude ในเครื่อง")
        return 1

    cases = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    if args.case:
        cases = [c for c in cases if any(c["id"].startswith(p) for p in args.case)]
    if not cases:
        print("ไม่มีเคสตรงกับที่เลือก")
        return 1

    n_judge = sum(1 for c in cases for t in c["turns"]
                  if (t.get("expect") or {}).get("judge"))
    print(f"{C_DIM}เคส {len(cases)} · รอบละ {args.repeat} · judge {n_judge} จุด")
    print(f"model={args.model} effort={args.effort} url={args.url}{C_OFF}\n")

    if args.dry_run:
        for c in cases:
            flag = f" {C_WARN}[known-fail]{C_OFF}" if c.get("known_fail") else ""
            print(f"  {c['id']}{flag}")
            for t in c["turns"]:
                print(f"     └ {t['prompt'][:88]}")
        return 0

    results, failed, known_failed, styles = [], [], [], []
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="tripitaka-prompt-test-") as tmp:
        # cwd ว่าง = CLI ไม่เจอ CLAUDE.md ของ repo มาปนกับ system prompt
        workdir = Path(tmp) / "run"
        workdir.mkdir()
        mcp_config = Path(tmp) / "mcp.json"
        mcp_config.write_text(json.dumps(
            {"mcpServers": {SERVER: {"type": "http", "url": args.url}}}
        ), encoding="utf-8")

        try:
            probe = claude("ok", workdir, model=args.model, effort="low",
                           mcp_config=mcp_config, timeout=180)
        except CliError as e:
            print(f"{C_BAD}CLI ใช้ไม่ได้: {e}{C_OFF}")
            print(f"{C_DIM}ถ้าเป็นเรื่อง OAuth ให้รัน `claude login` ก่อน{C_OFF}")
            return 1
        init = next((e for e in probe if e.get("type") == "system"), {})
        tools = [t for t in (init.get("tools") or []) if t.startswith(PREFIX)]
        status = next((s.get("status") for s in (init.get("mcp_servers") or [])
                       if s.get("name") == SERVER), "?")
        print(f"{C_DIM}MCP {status} · เครื่องมือของเรา {len(tools)} ตัว{C_OFF}\n")
        if status != "connected" or not tools:
            print(f"{C_BAD}ต่อ MCP ไม่ได้ — หยุด{C_OFF}")
            return 1

        for rnd in range(1, args.repeat + 1):
            if args.repeat > 1:
                print(f"{C_DIM}── รอบ {rnd}/{args.repeat}{C_OFF}")
            for case in cases:
                try:
                    problems, notes, answers, case_styles = run_case(
                        case, workdir, mcp_config, tools,
                        args.model, args.judge_model, args.effort)
                except (CliError, subprocess.TimeoutExpired) as e:
                    problems, notes, answers, case_styles = [f"CLI ล้ม: {e}"], [], [], []
                styles += case_styles
                # known_fail = รู้อยู่ว่ายังตก และรู้ว่ารออะไร → รายงานตามจริง
                # แต่ไม่นับเข้า exit code ไม่งั้นชุดเทสแดงค้างจนคนเลิกดูผล
                known = case.get("known_fail")
                if not problems:
                    mark = f"{C_OK}✅ PASS{C_OFF}"
                elif known:
                    mark = f"{C_WARN}⚠️  KNOWN-FAIL{C_OFF}"
                else:
                    mark = f"{C_BAD}❌ FAIL{C_OFF}"
                print(f"  {mark}  {case['id']}")
                if known:
                    state = "ผ่านรอบนี้ — ถ้าผ่านนิ่งแล้วถอดป้าย known_fail ออกได้" \
                        if not problems else "รอ: " + " ".join(str(known).split())
                    print(f"         {C_WARN}known_fail · {state}{C_OFF}")
                for n in notes:
                    print(f"         {C_DIM}{n}{C_OFF}")
                for p in problems:
                    colour = C_WARN if known else C_BAD
                    print(f"         {colour}→ {p}{C_OFF}")
                if problems:
                    (known_failed if known else failed).append(
                        (case["id"], rnd, problems))
                results.append({"id": case["id"], "round": rnd,
                                "known_fail": str(known or ""),
                                "problems": problems, "notes": notes,
                                "links": case_styles, "turns": answers})

    total = len(cases) * args.repeat
    print(f"\n{C_DIM}ใช้เวลา {time.time()-t0:.0f}s{C_OFF}")
    link_problems = report_link_rates(styles)
    if args.out:
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"{C_DIM}ผล → {args.out}{C_OFF}")

    def _lines(rows):
        for cid, rnd, ps in rows:
            suffix = f" (รอบ {rnd})" if args.repeat > 1 else ""
            print(f"   {cid}{suffix}: {ps[0]}")

    if known_failed:
        print(f"\n{C_WARN}⚠️  known-fail {len(known_failed)}/{total} "
              f"— ไม่นับเข้า exit code{C_OFF}")
        _lines(known_failed)
    if failed or link_problems:
        if failed:
            print(f"\n{C_BAD}❌ ตก {len(failed)}/{total}{C_OFF}")
            _lines(failed)
        for p in link_problems:
            print(f"{C_BAD}❌ {p}{C_OFF}")
        return 1
    if known_failed:
        # ไม่พูดว่า "ผ่านทั้งหมด" ตราบที่ยังมีเคสติดป้ายตกอยู่
        print(f"\n{C_OK}✅ ไม่มีเคสที่นับเข้า exit code ตก{C_OFF}"
              f"{C_DIM} · ผ่าน {total - len(known_failed)}/{total}"
              f" · known-fail {len(known_failed)}{C_OFF}")
    else:
        print(f"\n{C_OK}✅ ผ่านทั้งหมด {total}/{total}{C_OFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
