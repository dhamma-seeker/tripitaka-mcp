"""Parity test — คลังของเรา vs bilara-data ต้นทาง

`main.py` ประกาศไว้สามจุด (`:651` `:1466` `:2157`) ว่าคลังของเรา "at parity with
SuttaCentral bilara-data" แต่ไม่มีเทสไหนในรีโปตรวจคำประกาศนั้นเลย —
`test_full_sutta.py` ดู 22 สูตรด้วยค่าขั้นต่ำ, `test_survey_counts.py` ปักตัวเลข
ของคำไม่กี่คำ. ถ้าตัวบทหายไปทีละสูตรจาก migration หรือจาก loader ที่รันไม่ครบ
จะไม่มีอะไรส่งเสียง จุดขายของเซิร์ฟเวอร์นี้คือทุกคำตอบสืบกลับถึง segment_id ได้
ความครบถ้วนของคลังจึงไม่ใช่เรื่องคุณภาพ แต่เป็นเงื่อนไขว่าคำประกาศนั้นยังจริงอยู่ไหม

ไฟล์นี้ไม่ได้มาแก้ของที่พัง — วันที่เขียนทุกข้อผ่าน มันมาล็อกสถานะที่วันนี้ยังดีไว้

ตรวจสี่ข้อ:

1. **sutta coverage** — ทุก sutta_id ที่ต้นทางมี ต้องมีใน DB ยกเว้น allowlist
   ที่เขียนเหตุผลกำกับไว้ (ดู `SOURCE_ONLY_ALLOWLIST`)
2. **per-sutta segment counts** — จำนวนท่อนต่อสูตรต้องเท่ากันเป๊ะ รายงานทุกตัว
   ที่ไม่เท่าพร้อม delta
3. **corpus total** — ผลรวมทั้งคลังต้องเท่ากัน
4. **extra suttas in DB** — sutta_id ที่เรามีแต่ต้นทางไม่มี: ถ้า 0 ท่อนคือ
   placeholder ค้างจาก migration เก่า → รายงานเป็นข้อสังเกต ไม่ fail
   ถ้ามีท่อน → fail (แปลว่ามีข้อมูลที่ไม่มีต้นทางรองรับ ซึ่งเป็นเรื่องใหญ่)

กฎการนับใช้กฎเดียวกับ `scripts/data_loader.py` ไม่คิดใหม่: sutta_id = ชื่อไฟล์
ส่วนหน้าก่อน `_root-` (`extract_sutta_id`), นับ key ที่ค่า strip แล้วไม่ว่าง
(`merge_segments`). ฝั่ง DB นับแถวใน `segment` ตรงๆ เพราะ loader คัดท่อนว่างออก
ก่อน insert อยู่แล้ว — หนึ่งแถว = หนึ่งท่อนที่ต้นทางมีเนื้อหา

ต้องมี bilara-data ในเครื่อง (gitignored, ไม่ใช่ทุกเครื่องที่มี) — ถ้าไม่มี
สคริปต์จะ skip พร้อมบอกชัดว่าการตรวจนี้ไม่ได้รัน และ exit 0 เพื่อไม่พังของคนอื่น
    git clone --depth=1 https://github.com/suttacentral/bilara-data.git data/bilara-data

ใช้:
    BILARA_DATA_PATH=./data/bilara-data \
      TRIPITAKA_BACKEND=postgres .venv/bin/python scripts/test_corpus_parity.py
    BILARA_DATA_PATH=./data/bilara-data TRIPITAKA_BACKEND=sqlite \
      TRIPITAKA_DB_PATH=./tripitaka.db .venv/bin/python scripts/test_corpus_parity.py

Exit code 0 ถ้าผ่านหมด (หรือ skip), 1 ถ้ามี fail — ใช้ใน CI ได้
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# default เดียวกับ data_loader.py:36 — คนที่ clone ไว้ที่ปกติไม่ต้องตั้ง env
DEFAULT_BILARA_PATH = "./data/bilara-data"

# sutta_id ที่ต้นทางมีไฟล์ แต่ไม่ต้องมีใน DB ของเรา — เพิ่มได้ แต่ต้องมีเหตุผล
SOURCE_ONLY_ALLOWLIST: dict[str, str] = {
    # ไฟล์ทดลองของ bilara เอง ไม่ใช่ตัวบท (root/pli/ms/xplayground1_root-pli-ms.json)
    # ไม่อยู่ในนิกายไหน loader จึงไม่โหลด และไม่ควรโหลด
    "xplayground1": "bilara's own scratch file, not canon",
}

# นับท่อนต่อสูตรจาก DB — ANSI ล้วน ไม่มี placeholder ไม่มี ILIKE จึง execute
# ได้เหมือนกันทั้ง Postgres และ SQLite. Dual-Backend Discipline ต้องการกิ่ง
# `if backend.name == "sqlite"` เฉพาะที่ SQL ต่างกันจริง — ที่นี่ไม่ต่าง
# LEFT JOIN เพื่อให้ section ที่ไม่มีท่อนเลยคืน 0 ไม่ใช่หายไปจากผล
SQL_SEGMENT_COUNTS = """
    SELECT s.sutta_id, COUNT(g.id)
    FROM section s
    LEFT JOIN segment g ON g.section_id = s.id
    GROUP BY s.sutta_id
"""


# ---------------------------------------------------------------------------
# ต้นทาง (bilara-data)
# ---------------------------------------------------------------------------
def resolve_bilara_path() -> tuple[Path, str]:
    """คืน path ของ bilara-data + บอกว่ามาจาก env หรือ default"""
    env = os.getenv("BILARA_DATA_PATH")
    raw = os.getenv("BILARA_DATA_PATH", DEFAULT_BILARA_PATH)
    origin = "BILARA_DATA_PATH" if env else f"default ({DEFAULT_BILARA_PATH})"
    return Path(os.path.expanduser(raw)), origin


def bilara_revision(path: Path) -> str:
    """revision ของต้นทางที่ใช้เทียบ — ผลย้อนดูได้ว่าเทียบกับรุ่นไหน"""
    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(path), *args],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    rev = git("rev-parse", "--short", "HEAD")
    if not rev:
        return "ไม่ทราบ revision (ไม่ใช่ git repo)"
    date = git("log", "-1", "--format=%cd", "--date=short")
    return f"rev {rev}" + (f" ({date})" if date else "")


def scan_source(root: Path) -> tuple[dict[str, int], dict[str, list[str]]]:
    """เดินไฟล์ root บาลีทั้งหมด → {sutta_id: จำนวนท่อนที่มีเนื้อหา}

    กฎเดียวกับ data_loader.py: sutta_id จากชื่อไฟล์ส่วนหน้าก่อน `_root-`
    และนับ key ที่ค่า strip แล้วไม่ว่าง
    """
    counts: dict[str, int] = {}
    files: dict[str, list[str]] = {}
    for path in sorted(root.glob("**/*_root-pli-ms.json")):
        sutta_id = path.name.split("_root-")[0]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            n = sum(1 for text in data.values() if text and text.strip())
        except (OSError, ValueError, AttributeError) as e:
            # ไฟล์ต้นทางพังเอง — บอกให้รู้ว่าไฟล์ไหน ไม่ใช่ traceback เปล่า
            raise RuntimeError(f"อ่านไฟล์ต้นทางไม่ได้: {path} — {e}") from e
        counts[sutta_id] = counts.get(sutta_id, 0) + n
        files.setdefault(sutta_id, []).append(path.name)
    return counts, files


# ---------------------------------------------------------------------------
# ฝั่งเรา (DB)
# ---------------------------------------------------------------------------
def scan_database() -> dict[str, int]:
    """อ่านผ่าน get_backend() → รันได้ทั้ง Postgres และ SQLite ด้วย TRIPITAKA_BACKEND"""
    from db.backend import get_backend

    backend = get_backend()
    conn = backend.connect()
    cur = None
    try:
        cur = backend.cursor(conn)
        cur.execute(SQL_SEGMENT_COUNTS)
        return {row[0]: int(row[1]) for row in cur.fetchall()}
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                pass
        backend.release(conn)


# ---------------------------------------------------------------------------
# การตรวจ
# ---------------------------------------------------------------------------
def check_coverage(
    source: dict[str, int], db: dict[str, int]
) -> tuple[bool, str, list[str]]:
    """ข้อ 1 — ทุกสูตรที่ต้นทางมี ต้องมีใน DB (ยกเว้น allowlist)"""
    missing = sorted(set(source) - set(db) - set(SOURCE_ONLY_ALLOWLIST))
    skipped = sorted(set(source) & set(SOURCE_ONLY_ALLOWLIST))
    detail = (
        f"ต้นทาง {len(source):,} สูตร · allowlist {len(skipped)} · "
        f"หายจาก DB {len(missing)}"
    )
    lines = [f"    - {sid} (ต้นทางมี {source[sid]:,} ท่อน)" for sid in missing]
    if lines:
        lines.insert(0, f"  สูตรที่ต้นทางมีแต่ DB ไม่มี ({len(missing)}):")
    for sid in skipped:
        lines.append(f"  allowlist: {sid} — {SOURCE_ONLY_ALLOWLIST[sid]}")
    return not missing, detail, lines


def check_counts(
    source: dict[str, int], db: dict[str, int]
) -> tuple[bool, str, list[str]]:
    """ข้อ 2 — จำนวนท่อนต่อสูตรต้องเท่ากันเป๊ะ"""
    shared = sorted(set(source) & set(db))
    diffs = [(sid, source[sid], db[sid]) for sid in shared if source[sid] != db[sid]]
    detail = f"เทียบ {len(shared):,} สูตร · ไม่เท่า {len(diffs)}"
    lines: list[str] = []
    if diffs:
        lines.append(f"  สูตรที่จำนวนท่อนไม่ตรง ({len(diffs)}):")
        # หัวตารางเป็น ASCII — อักษรไทยกว้างกว่าหนึ่งช่องทำให้คอลัมน์เยื้อง
        lines.append(f"    {'sutta_id':<20} {'source':>8} {'db':>8} {'delta':>8}")
        for sid, src, ours in diffs:
            lines.append(f"    {sid:<20} {src:>8,} {ours:>8,} {ours - src:>+8,}")
    return not diffs, detail, lines


def check_total(
    source: dict[str, int], db: dict[str, int]
) -> tuple[bool, str, list[str]]:
    """ข้อ 3 — ผลรวมทั้งคลังต้องเท่ากัน"""
    src_total = sum(source.values())
    allowed = sum(n for sid, n in source.items() if sid in SOURCE_ONLY_ALLOWLIST)
    expected = src_total - allowed
    db_total = sum(db.values())
    detail = (
        f"DB {db_total:,} · ต้นทาง {src_total:,} - allowlist {allowed:,} "
        f"= {expected:,} · delta {db_total - expected:+,}"
    )
    return db_total == expected, detail, []


def check_extras(
    source: dict[str, int], db: dict[str, int]
) -> tuple[bool, str, list[str]]:
    """ข้อ 4 — สูตรที่เรามีแต่ต้นทางไม่มี: 0 ท่อน = ข้อสังเกต, มีท่อน = fail"""
    extras = sorted(set(db) - set(source))
    empty = [sid for sid in extras if db[sid] == 0]
    filled = [(sid, db[sid]) for sid in extras if db[sid] > 0]
    detail = (
        f"DB มีเกิน {len(extras)} สูตร · ว่าง {len(empty)} (ข้อสังเกต) · "
        f"มีเนื้อหา {len(filled)}"
    )
    lines: list[str] = []
    if filled:
        lines.append(
            f"  มีเนื้อหาแต่ไม่มีต้นทางรองรับ ({len(filled)}) — ตรวจว่ามาจากไหน:"
        )
        for sid, n in filled:
            lines.append(f"    - {sid} ({n:,} ท่อน)")
    if empty:
        lines.append(
            f"  ข้อสังเกต: {len(empty)} sutta_id ไม่มีไฟล์ต้นทางและไม่มีท่อนเลย"
            " — placeholder ค้างจาก migration เก่า ไม่ใช่ความผิดพลาด"
        )
        lines.append("    " + ", ".join(empty))
    return not filled, detail, lines


# ---------------------------------------------------------------------------
def main() -> int:
    bilara, origin = resolve_bilara_path()
    root = bilara / "root" / "pli" / "ms"

    if not bilara.exists():
        print("⏭️  SKIP — corpus parity ไม่ได้รัน (ไม่มีการตรวจเกิดขึ้น)")
        print(f"   ไม่พบ bilara-data ที่ {bilara}  [จาก {origin}]")
        print("   ข้อมูลชุดนี้ gitignored — clone ก่อนแล้วชี้ BILARA_DATA_PATH มาที่นั้น:")
        print("     git clone --depth=1 https://github.com/suttacentral/bilara-data.git"
              " data/bilara-data")
        return 0
    if not root.is_dir():
        print("⏭️  SKIP — corpus parity ไม่ได้รัน (ไม่มีการตรวจเกิดขึ้น)")
        print(f"   {bilara} มีอยู่ แต่ไม่มี root/pli/ms/ ข้างใน")
        print("   path นี้ไม่ใช่ bilara-data checkout — ชี้ BILARA_DATA_PATH ให้ถูกก่อน")
        return 0

    backend_name = os.getenv("TRIPITAKA_BACKEND", "postgres")
    print("corpus parity — DB ของเรา vs bilara-data ต้นทาง\n")
    print(f"ต้นทาง   {bilara}  [{origin}]")
    print(f"         {bilara_revision(bilara)}")
    print(f"backend  {backend_name}")

    t0 = time.perf_counter()
    source, source_files = scan_source(root)
    scan_secs = time.perf_counter() - t0
    n_files = sum(len(v) for v in source_files.values())
    if not source:
        print()
        print(f"❌ ไม่พบไฟล์ `*_root-pli-ms.json` ใต้ {root} เลย — ต้นทางว่าง")
        return 1
    print(f"         {n_files:,} ไฟล์ · {len(source):,} สูตร · "
          f"{sum(source.values()):,} ท่อน (อ่าน {scan_secs:.1f}s)")

    try:
        db = scan_database()
    except Exception as e:
        print()
        print(f"❌ อ่าน DB ไม่ได้ (backend={backend_name}): {e}")
        return 1
    print(f"DB       {len(db):,} สูตร · {sum(db.values()):,} ท่อน\n")

    dupes = {sid: f for sid, f in source_files.items() if len(f) > 1}
    if dupes:
        print(f"ℹ️  sutta_id ที่มาจากหลายไฟล์ ({len(dupes)}) — นับรวมกัน:")
        for sid, names in sorted(dupes.items()):
            print(f"   {sid}: {', '.join(names)}")
        print()

    checks = [
        ("sutta coverage", check_coverage),
        ("per-sutta segment counts", check_counts),
        ("corpus total", check_total),
        ("extra suttas in DB", check_extras),
    ]
    print(f"{'check':<26} {'status':<6} detail")
    failed = 0
    details: list[str] = []
    for name, fn in checks:
        ok, detail, lines = fn(source, db)
        print(f"{name:<26} {'PASS' if ok else 'FAIL':<6} {detail}")
        if not ok:
            failed += 1
        if lines:
            details.append(f"[{name}]")
            details.extend(lines)

    if details:
        print()
        print("\n".join(details))

    print()
    if failed:
        print(f"❌ fail {failed} ข้อ — คลังเลื่อนจากต้นทางแล้ว")
        return 1
    print("✅ ผ่านทั้งหมด — คลังตรงกับ bilara-data ที่ revision นี้")
    return 0


if __name__ == "__main__":
    sys.exit(main())
