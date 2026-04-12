"""
Tripitaka MCP Server — Load Vinaya Pitaka

โหลดข้อมูลวินัยปิฎกจาก bilara-data เข้าฐานข้อมูล
โครงสร้าง bilara-data สำหรับ Vinaya:
    root/pli/ms/vinaya/{nikaya_code}/{file}_root-pli-ms.json
    translation/en/brahmali/vinaya/{nikaya_code}/{file}_translation-en-brahmali.json
    translation/th/jayasaro/vinaya/{file}_translation-th-jayasaro.json  (มีแค่ 2 ไฟล์)

Usage:
    python scripts/load_vinaya.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

from db.connection import get_connection, release_connection
from db.schema import create_tables
from scripts.data_loader import (
    BILARA_DATA_PATH,
    parse_json_file,
    merge_segments,
    insert_sutta_data,
)

VINAYA_ROOT = BILARA_DATA_PATH / "root" / "pli" / "ms" / "vinaya"
VINAYA_EN = BILARA_DATA_PATH / "translation" / "en" / "brahmali" / "vinaya"
VINAYA_TH = BILARA_DATA_PATH / "translation" / "th" / "jayasaro" / "vinaya"

# mapping: nikaya_code → subdirectory ใน vinaya/
# ไฟล์ที่ไม่อยู่ใน subdir จะถูกจัดให้ nikaya ใกล้เคียง
VINAYA_NIKAYAS = [
    {"code": "pli-tv-bu-vb", "subdir": "pli-tv-bu-vb"},
    {"code": "pli-tv-bi-vb", "subdir": "pli-tv-bi-vb"},
    {"code": "pli-tv-kd",    "subdir": "pli-tv-kd"},
    {"code": "pli-tv-pvr",   "subdir": "pli-tv-pvr"},
]

# ไฟล์ระดับบนสุดของ vinaya/ (Patimokkha) → assign ให้ nikaya ใกล้เคียง
VINAYA_TOP_FILES = [
    {"file": "pli-tv-bu-pm_root-pli-ms.json", "nikaya_code": "pli-tv-bu-vb"},
    {"file": "pli-tv-bi-pm_root-pli-ms.json", "nikaya_code": "pli-tv-bi-vb"},
]


def find_en_translation(root_path: Path) -> Path | None:
    """หาไฟล์แปลอังกฤษ (Brahmali) ที่ตรงกับ root file"""
    filename = root_path.name
    base = filename.split("_root-")[0]
    trans_filename = f"{base}_translation-en-brahmali.json"

    # หา relative path จาก vinaya root
    try:
        rel = root_path.relative_to(VINAYA_ROOT)
        trans_path = VINAYA_EN / rel.parent / trans_filename
        if trans_path.exists():
            return trans_path
    except ValueError:
        pass
    return None


def find_th_translation(root_path: Path) -> Path | None:
    """หาไฟล์แปลไทย (Jayasaro) ที่ตรงกับ root file"""
    filename = root_path.name
    base = filename.split("_root-")[0]
    trans_filename = f"{base}_translation-th-jayasaro.json"

    # Jayasaro files อยู่ที่ root ของ vinaya/th/ (ไม่มี subdir)
    trans_path = VINAYA_TH / trans_filename
    if trans_path.exists():
        return trans_path
    return None


def get_or_create_book_vinaya(cur, nikaya_id: int, nikaya_code: str) -> int:
    """หรือสร้าง book record สำหรับ Vinaya"""
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


def load_vinaya_nikaya(nikaya_code: str, root_files: list[Path]) -> dict[str, int]:
    """โหลดไฟล์ Vinaya ที่อยู่ในนิกายหนึ่งเข้า DB"""
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM nikaya WHERE code = %s", (nikaya_code,))
        row = cur.fetchone()
        if not row:
            print(f"   ⚠️  ไม่พบ nikaya: {nikaya_code} — ต้องรัน seed_metadata.py ก่อน")
            return {"suttas": 0, "segments": 0}
        nikaya_id = row[0]

        book_id = get_or_create_book_vinaya(cur, nikaya_id, nikaya_code)

        total_suttas = 0
        total_segments = 0

        for i, root_path in enumerate(tqdm(root_files, desc=f"   📖 {nikaya_code}")):
            sutta_id = root_path.name.split("_root-")[0]

            pali_data = parse_json_file(root_path)

            en_path = find_en_translation(root_path)
            en_data = parse_json_file(en_path) if en_path else None

            th_path = find_th_translation(root_path)
            th_data = parse_json_file(th_path) if th_path else None

            segments = merge_segments(pali_data, en_data, th_data)
            if segments:
                count = insert_sutta_data(cur, book_id, sutta_id, segments, sort_order=i + 1)
                total_suttas += 1
                total_segments += count

        conn.commit()
        return {"suttas": total_suttas, "segments": total_segments}

    except Exception as e:
        conn.rollback()
        print(f"\n❌ เกิดข้อผิดพลาด ({nikaya_code}): {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def load_all() -> None:
    """โหลดวินัยปิฎกทั้งหมด"""
    print("=" * 60)
    print("📜 Vinaya Pitaka Loader")
    print("   บาลี: Mahasangiti | English: Bhikkhu Brahmali (CC0)")
    print("   Thai: Phra Ajahn Jayasaro (CC0, มีแค่ Patimokkha)")
    print("=" * 60)

    create_tables()

    grand_total = {"suttas": 0, "segments": 0}

    # โหลดไฟล์ระดับบนสุด (Patimokkha) ก่อน
    for top in VINAYA_TOP_FILES:
        root_path = VINAYA_ROOT / top["file"]
        if root_path.exists():
            print(f"\n📚 {top['file']} → nikaya: {top['nikaya_code']}")
            result = load_vinaya_nikaya(top["nikaya_code"], [root_path])
            grand_total["suttas"] += result["suttas"]
            grand_total["segments"] += result["segments"]
            print(f"   ✅ {result['suttas']} สูตร, {result['segments']} segments")
        else:
            print(f"\n⚠️  ไม่พบ: {top['file']}")

    # โหลดแต่ละ subdir
    for nikaya in VINAYA_NIKAYAS:
        subdir = VINAYA_ROOT / nikaya["subdir"]
        if not subdir.exists():
            print(f"\n⚠️  ไม่พบ directory: {subdir}")
            continue

        root_files = sorted(subdir.rglob("*_root-pli-ms.json"))
        print(f"\n📚 {nikaya['code']} — {len(root_files)} ไฟล์")

        result = load_vinaya_nikaya(nikaya["code"], root_files)
        grand_total["suttas"] += result["suttas"]
        grand_total["segments"] += result["segments"]
        print(f"   ✅ {result['suttas']} สูตร, {result['segments']} segments")

    print("\n" + "=" * 60)
    print("✅ โหลดวินัยปิฎกเสร็จสมบูรณ์!")
    print(f"   รวม: {grand_total['suttas']} สูตร, {grand_total['segments']} segments")
    print("=" * 60)


if __name__ == "__main__":
    load_all()
