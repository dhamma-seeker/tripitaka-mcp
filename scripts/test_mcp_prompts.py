"""Prompt-level test — ให้โมเดลจริงตัดสินใจเองว่าจะเรียกเครื่องมือไหน

ต่างจาก test_definitions.py / test_verify_quote.py ที่เรียกฟังก์ชันตรงๆ:
ไฟล์นี้ spawn `claude` CLI ในเครื่อง ต่อ MCP server จริงผ่าน --mcp-config
แล้วปล่อยให้โมเดลเลือกเครื่องมือเอง จึงวัดได้ว่า tool description +
routing rule ที่เราเขียนไว้ "ติด" จริงไหม

ใช้ subscription ของ CLI ไม่ใช่ API key จึงไม่มีค่า token ต่อรอบ
ต้อง `claude login` ให้ session ยังไม่หมดอายุก่อนรัน

กันการปนเปื้อน: รันใน cwd ว่าง (ไม่ให้เจอ CLAUDE.md ของ repo),
--strict-mcp-config (ไม่เอา MCP อื่นของเครื่อง), --restricted (ตัด Bash ทิ้ง)

ใช้:
    .venv/bin/python scripts/test_mcp_prompts.py --dry-run
    .venv/bin/python scripts/test_mcp_prompts.py                    # prod + opus
    .venv/bin/python scripts/test_mcp_prompts.py --case B1 --case C4
    .venv/bin/python scripts/test_mcp_prompts.py --model haiku       # เทียบโมเดลต่ำ
    .venv/bin/python scripts/test_mcp_prompts.py --url http://localhost:8080/mcp
    .venv/bin/python scripts/test_mcp_prompts.py --repeat 3          # วัดความไม่นิ่ง

Exit code 0 ถ้าผ่านทุกเคส, 1 ถ้ามี fail
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = ROOT / "scripts" / "prompt_cases.yaml"
DEFAULT_URL = "https://mcp.tripitaka-mcp.com/mcp"
SERVER = "tripitaka"
PREFIX = f"mcp__{SERVER}__"
TURN_TIMEOUT = 600

C_OK, C_BAD, C_DIM, C_OFF = "\033[32m", "\033[31m", "\033[90m", "\033[0m"


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
    problems, notes, answers, session = [], [], [], None
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
        if expect.get("judge"):
            ok, why = judge(expect["judge"], answer, calls, workdir, judge_model, effort)
            (notes if ok else problems).append(f"{tag}judge{'' if ok else ''}: {why}")
    return problems, notes, answers


def main():
    # ไม่ใช่ tty แล้ว stdout จะถูก buffer จนจบ — รันเบื้องหลังจะมองไม่เห็นอะไรเลย
    sys.stdout.reconfigure(line_buffering=True)

    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
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
            print(f"  {c['id']}")
            for t in c["turns"]:
                print(f"     └ {t['prompt'][:88]}")
        return 0

    results, failed = [], []
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
                    problems, notes, answers = run_case(
                        case, workdir, mcp_config, tools,
                        args.model, args.judge_model, args.effort)
                except (CliError, subprocess.TimeoutExpired) as e:
                    problems, notes, answers = [f"CLI ล้ม: {e}"], [], []
                mark = f"{C_OK}✅ PASS{C_OFF}" if not problems else f"{C_BAD}❌ FAIL{C_OFF}"
                print(f"  {mark}  {case['id']}")
                for n in notes:
                    print(f"         {C_DIM}{n}{C_OFF}")
                for p in problems:
                    print(f"         {C_BAD}→ {p}{C_OFF}")
                if problems:
                    failed.append((case["id"], rnd, problems))
                results.append({"id": case["id"], "round": rnd,
                                "problems": problems, "notes": notes,
                                "turns": answers})

    total = len(cases) * args.repeat
    print(f"\n{C_DIM}ใช้เวลา {time.time()-t0:.0f}s{C_OFF}")
    if args.out:
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"{C_DIM}ผล → {args.out}{C_OFF}")

    if failed:
        print(f"\n{C_BAD}❌ ตก {len(failed)}/{total}{C_OFF}")
        for cid, rnd, ps in failed:
            suffix = f" (รอบ {rnd})" if args.repeat > 1 else ""
            print(f"   {cid}{suffix}: {ps[0]}")
        return 1
    print(f"\n{C_OK}✅ ผ่านทั้งหมด {total}/{total}{C_OFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
