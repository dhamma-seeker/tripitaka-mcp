"""
Tripitaka MCP Server — Data Loader

นำเข้าข้อมูลพระไตรปิฎกจาก SuttaCentral bilara-data (JSON)
โครงสร้างข้อมูล bilara-data:
    root/pli/ms/sutta/{nikaya}/{sutta_id}_root-pli-ms.json
    translation/en/sujato/sutta/{nikaya}/{sutta_id}_translation-en-sujato.json

Usage:
    # Clone bilara-data ก่อน:
    git clone https://github.com/suttacentral/bilara-data.git data/bilara-data

    # รัน data loader:
    python scripts/data_loader.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# เพิ่ม project root ใน path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tqdm import tqdm

from db.connection import get_connection, release_connection
from db.schema import create_tables


# =============================================================================
# Configuration
# =============================================================================
BILARA_DATA_PATH = Path(os.getenv("BILARA_DATA_PATH", "./data/bilara-data"))
BILARA_REPO_URL = "https://github.com/suttacentral/bilara-data.git"

# นิกายที่จะ load (เริ่มจาก Sutta Pitaka)
SUTTA_NIKAYAS = ["dn", "mn", "sn", "an"]


def download_bilara_data() -> None:
    """Clone bilara-data repo จาก SuttaCentral (ถ้ายังไม่มี)"""
    if BILARA_DATA_PATH.exists() and (BILARA_DATA_PATH / ".git").exists():
        print(f"📁 bilara-data มีอยู่แล้วที่ {BILARA_DATA_PATH}")
        print("   กำลัง pull ข้อมูลล่าสุด...")
        subprocess.run(
            ["git", "pull"],
            cwd=BILARA_DATA_PATH,
            check=True,
        )
        return

    print(f"📥 กำลัง clone bilara-data ไปที่ {BILARA_DATA_PATH} ...")
    print("   (อาจใช้เวลาสักครู่ — repo มีขนาดใหญ่)")
    BILARA_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth=1", BILARA_REPO_URL, str(BILARA_DATA_PATH)],
        check=True,
    )
    print("✅ Clone เรียบร้อย")


def find_root_files(nikaya_code: str) -> list[Path]:
    """หาไฟล์ root (บาลี) ทั้งหมดในนิกายที่ระบุ

    Args:
        nikaya_code: รหัสนิกาย เช่น "mn", "dn", "sn", "an"

    Returns:
        รายการ path ไปยังไฟล์ JSON ของ root text (บาลี)
    """
    root_dir = BILARA_DATA_PATH / "root" / "pli" / "ms" / "sutta" / nikaya_code
    if not root_dir.exists():
        print(f"⚠️ ไม่พบ directory: {root_dir}")
        return []

    files = sorted(root_dir.rglob("*_root-pli-ms.json"))
    return files


def parse_json_file(path: Path) -> dict[str, str]:
    """อ่านไฟล์ JSON ของ bilara-data

    Args:
        path: path ไปยังไฟล์ JSON

    Returns:
        dict mapping segment_id → text
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_translation_file(root_path: Path, lang: str, translator: str) -> Path | None:
    """หาไฟล์แปลที่ตรงกับ root file

    Args:
        root_path: path ไปยังไฟล์ root (บาลี)
        lang: รหัสภาษา เช่น "en", "th"
        translator: ชื่อผู้แปล เช่น "sujato"

    Returns:
        path ไปยังไฟล์แปล หรือ None ถ้าไม่พบ
    """
    # root: root/pli/ms/sutta/mn/mn1_root-pli-ms.json
    # translation: translation/en/sujato/sutta/mn/mn1_translation-en-sujato.json
    filename = root_path.name
    # แปลง root filename → translation filename
    # mn1_root-pli-ms.json → mn1_translation-en-sujato.json
    base = filename.split("_root-")[0]
    trans_filename = f"{base}_translation-{lang}-{translator}.json"

    # สร้าง path สำหรับ translation
    # ใช้ relative path จาก sutta/ เป็นฐาน
    rel_parts = root_path.relative_to(
        BILARA_DATA_PATH / "root" / "pli" / "ms"
    ).parts  # ('sutta', 'mn', ...)
    trans_path = BILARA_DATA_PATH / "translation" / lang / translator / Path(*rel_parts).parent / trans_filename

    if trans_path.exists():
        return trans_path
    return None


def extract_sutta_id(root_path: Path) -> str:
    """ดึง sutta_id จากชื่อไฟล์

    Args:
        root_path: เช่น .../mn1_root-pli-ms.json

    Returns:
        sutta_id เช่น "mn1"
    """
    return root_path.name.split("_root-")[0]


def merge_segments(
    pali_data: dict[str, str],
    en_data: dict[str, str] | None = None,
    th_data: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """รวม segments จากทุกภาษาเข้าด้วยกัน โดยใช้ segment_id เป็น key

    Args:
        pali_data: dict mapping segment_id → text (บาลี, ต้องมีเสมอ)
        en_data: dict mapping segment_id → text (อังกฤษ, optional)
        th_data: dict mapping segment_id → text (ไทย, optional)

    Returns:
        list of dicts แต่ละตัวมี segment_id, text_pali, text_thai, text_english
    """
    segments = []
    for segment_id, text_pali in pali_data.items():
        # ข้ามถ้าเป็น segment ที่ไม่มีเนื้อหา
        if not text_pali or not text_pali.strip():
            continue

        segment = {
            "segment_id": segment_id,
            "text_pali": text_pali.strip(),
            "text_english": None,
            "text_thai": None,
        }

        if en_data and segment_id in en_data:
            text = en_data[segment_id]
            if text and text.strip():
                segment["text_english"] = text.strip()

        if th_data and segment_id in th_data:
            text = th_data[segment_id]
            if text and text.strip():
                segment["text_thai"] = text.strip()

        segments.append(segment)

    return segments


def get_or_create_book(cur, nikaya_id: int, nikaya_code: str) -> int:
    """หรือสร้าง book record (ใช้ nikaya_code เป็น book code เบื้องต้น)

    Args:
        cur: database cursor
        nikaya_id: ID ของ nikaya
        nikaya_code: รหัสนิกาย เช่น "mn"

    Returns:
        book id
    """
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
        (nikaya_id, book_code, nikaya_code.upper(), nikaya_code.upper(), 1),
    )
    return cur.fetchone()[0]


def insert_sutta_data(
    cur,
    book_id: int,
    sutta_id: str,
    segments: list[dict[str, Any]],
    sort_order: int,
) -> int:
    """Insert section (สูตร) และ segments (ข้อความ) ลง database

    Args:
        cur: database cursor
        book_id: ID ของ book
        sutta_id: รหัสสูตร เช่น "mn1"
        segments: list of merged segments
        sort_order: ลำดับ

    Returns:
        จำนวน segments ที่ insert
    """
    # Insert/update section
    cur.execute(
        """
        INSERT INTO section (book_id, sutta_id, sort_order)
        VALUES (%s, %s, %s)
        ON CONFLICT (sutta_id) DO UPDATE SET
            book_id = EXCLUDED.book_id
        RETURNING id
        """,
        (book_id, sutta_id, sort_order),
    )
    section_id = cur.fetchone()[0]

    # Insert segments
    count = 0
    for seg in segments:
        cur.execute(
            """
            INSERT INTO segment (section_id, segment_id, text_pali, text_thai, text_english)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (segment_id) DO UPDATE SET
                text_pali = EXCLUDED.text_pali,
                text_thai = EXCLUDED.text_thai,
                text_english = EXCLUDED.text_english
            """,
            (section_id, seg["segment_id"], seg["text_pali"], seg["text_thai"], seg["text_english"]),
        )
        count += 1

    return count


def load_nikaya(nikaya_code: str) -> dict[str, int]:
    """โหลดข้อมูลทั้งนิกายลง database

    Args:
        nikaya_code: รหัสนิกาย เช่น "mn", "dn"

    Returns:
        dict สรุปจำนวน {"suttas": int, "segments": int}
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # หา nikaya_id
        cur.execute("SELECT id FROM nikaya WHERE code = %s", (nikaya_code,))
        row = cur.fetchone()
        if not row:
            print(f"⚠️ ไม่พบ nikaya code: {nikaya_code} ใน database — ต้อง seed_metadata ก่อน")
            return {"suttas": 0, "segments": 0}
        nikaya_id = row[0]

        # สร้าง/หา book
        book_id = get_or_create_book(cur, nikaya_id, nikaya_code)

        # หาไฟล์ root ทั้งหมด
        root_files = find_root_files(nikaya_code)
        if not root_files:
            print(f"⚠️ ไม่พบไฟล์ root สำหรับ {nikaya_code}")
            return {"suttas": 0, "segments": 0}

        total_suttas = 0
        total_segments = 0

        for i, root_path in enumerate(tqdm(root_files, desc=f"📖 {nikaya_code.upper()}")):
            sutta_id = extract_sutta_id(root_path)

            # อ่าน root (บาลี)
            pali_data = parse_json_file(root_path)

            # หาและอ่านคำแปลอังกฤษ (Bhikkhu Sujato)
            en_path = find_translation_file(root_path, "en", "sujato")
            en_data = parse_json_file(en_path) if en_path else None

            # หาและอ่านคำแปลไทย (ลองทุก translator ที่มีใน bilara-data)
            th_path = None
            for th_translator in ["dhiranandi", "jayasaro", "kee", "nyanamoli"]:
                th_path = find_translation_file(root_path, "th", th_translator)
                if th_path:
                    break
            th_data = parse_json_file(th_path) if th_path else None

            # รวม segments
            segments = merge_segments(pali_data, en_data, th_data)

            if segments:
                count = insert_sutta_data(cur, book_id, sutta_id, segments, sort_order=i + 1)
                total_suttas += 1
                total_segments += count

        conn.commit()
        return {"suttas": total_suttas, "segments": total_segments}

    except Exception as e:
        conn.rollback()
        print(f"❌ เกิดข้อผิดพลาดในการ load {nikaya_code}: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def load_all() -> None:
    """โหลดข้อมูลทุกนิกาย (Sutta Pitaka)"""
    print("=" * 60)
    print("🛕 Tripitaka Data Loader — SuttaCentral bilara-data")
    print("=" * 60)

    # Step 1: ดาวน์โหลด/อัปเดต bilara-data
    download_bilara_data()

    # Step 2: สร้างตาราง (ถ้ายังไม่มี)
    create_tables()

    # Step 3: โหลดข้อมูลแต่ละนิกาย
    grand_total = {"suttas": 0, "segments": 0}
    for nikaya_code in SUTTA_NIKAYAS:
        print(f"\n📚 กำลังโหลด {nikaya_code.upper()}...")
        result = load_nikaya(nikaya_code)
        grand_total["suttas"] += result["suttas"]
        grand_total["segments"] += result["segments"]
        print(f"   ✅ {result['suttas']} สูตร, {result['segments']} segments")

    print("\n" + "=" * 60)
    print(f"✅ โหลดข้อมูลเสร็จสมบูรณ์!")
    print(f"   รวม: {grand_total['suttas']} สูตร, {grand_total['segments']} segments")
    print("=" * 60)


if __name__ == "__main__":
    load_all()
