"""
Tripitaka MCP Server — Load Abhidhamma Pitaka

Loads Abhidhamma data from bilara-data into the database.

Coverage:
- 7 books: ds, vb, dt, pp, kv, ya, patthana — all with Pāli root only
- bilara-data has NO English translation for Abhidhamma (verified 2026-05-03;
  Sujato/Brahmali/anyone have 0 files under translation/en/*/abhidhamma/)
- so this loader is Pāli-only by design; the parity story is "we have what
  bilara has" not "we're missing English"

Bilara structure:
    root/pli/ms/abhidhamma/{book_code}/{file}_root-pli-ms.json
    (no translation/en/*/abhidhamma/)

Usage:
    python scripts/load_abhidhamma.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

from db.connection import get_connection, release_connection
from db.schema import create_tables
from scripts.data_loader import (
    BILARA_DATA_PATH,
    parse_json_file,
    merge_segments,
    insert_sutta_data,
)

ABHIDHAMMA_ROOT = BILARA_DATA_PATH / "root" / "pli" / "ms" / "abhidhamma"

# 7 books matching NIKAYAS_ABHIDHAMMA in seed_metadata.py
ABHIDHAMMA_NIKAYAS = [
    {"code": "ds", "subdir": "ds"},
    {"code": "vb", "subdir": "vb"},
    {"code": "dt", "subdir": "dt"},
    {"code": "pp", "subdir": "pp"},
    {"code": "kv", "subdir": "kv"},
    {"code": "ya", "subdir": "ya"},
    {"code": "patthana", "subdir": "patthana"},
]


def get_or_create_book_abhidhamma(cur, nikaya_id: int, nikaya_code: str) -> int:
    """Get or create a book record for an Abhidhamma sub-book."""
    book_code = f"{nikaya_code}-book"
    cur.execute("SELECT id FROM book WHERE code = %s", (book_code,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO book (nikaya_id, code, name_pali, name_english, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (nikaya_id, book_code, nikaya_code, nikaya_code.upper(), 1),
    )
    return cur.fetchone()[0]


def load_abhidhamma_book(nikaya_code: str, root_files: list[Path]) -> dict[str, int]:
    """Load files of a single Abhidhamma book into the DB."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM nikaya WHERE code = %s", (nikaya_code,))
        row = cur.fetchone()
        if not row:
            print(f"   ⚠️  nikaya not found: {nikaya_code} — run seed_metadata.py first")
            return {"suttas": 0, "segments": 0}
        nikaya_id = row[0]

        book_id = get_or_create_book_abhidhamma(cur, nikaya_id, nikaya_code)

        total_suttas = 0
        total_segments = 0

        for i, root_path in enumerate(tqdm(root_files, desc=f"   📖 {nikaya_code}")):
            sutta_id = root_path.name.split("_root-")[0]

            pali_data = parse_json_file(root_path)
            # Abhidhamma has no en/th translations in bilara-data
            segments = merge_segments(pali_data, en_data=None, th_data=None)
            if segments:
                count = insert_sutta_data(cur, book_id, sutta_id, segments, sort_order=i + 1)
                total_suttas += 1
                total_segments += count

        conn.commit()
        return {"suttas": total_suttas, "segments": total_segments}

    except Exception as e:
        conn.rollback()
        print(f"\n❌ error ({nikaya_code}): {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def load_all() -> None:
    """Load every Abhidhamma book."""
    print("=" * 60)
    print("📜 Abhidhamma Pitaka Loader (Pāli only — no English in bilara)")
    print("   Source: SuttaCentral bilara-data Mahāsaṅgīti")
    print("=" * 60)

    create_tables()

    grand_total = {"suttas": 0, "segments": 0}

    for nikaya in ABHIDHAMMA_NIKAYAS:
        subdir = ABHIDHAMMA_ROOT / nikaya["subdir"]
        if not subdir.exists():
            print(f"\n⚠️  directory not found: {subdir}")
            continue

        root_files = sorted(subdir.rglob("*_root-pli-ms.json"))
        print(f"\n📚 {nikaya['code']} — {len(root_files)} files")

        result = load_abhidhamma_book(nikaya["code"], root_files)
        grand_total["suttas"] += result["suttas"]
        grand_total["segments"] += result["segments"]
        print(f"   ✅ {result['suttas']} sections, {result['segments']} segments")

    print("\n" + "=" * 60)
    print("✅ Abhidhamma load complete")
    print(f"   Total: {grand_total['suttas']} sections, {grand_total['segments']} segments")
    print("=" * 60)


if __name__ == "__main__":
    load_all()
