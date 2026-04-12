"""
Tripitaka MCP Server — Load Thai CC0 Translations

โหลดคำแปลภาษาไทยที่มี license CC0 จาก bilara-data เข้าตาราง translation
รองรับหลาย translator (dhiranandi, jayasaro, ...)

ข้อมูลที่มีใน bilara-data (CC0):
    - dhiranandi: mn26, snp1.8
    - jayasaro:   vinaya (pli-tv-bu-pm, pli-tv-bi-pm)

Usage:
    python scripts/load_thai_cc0.py
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

BILARA_DATA_PATH = Path(os.getenv("BILARA_DATA_PATH", "./data/bilara-data"))

# CC0 translators ที่มีใน bilara-data พร้อมข้อมูลเพิ่มเติม
TH_TRANSLATORS = [
    {
        "code": "dhiranandi",
        "name": "พระภิกษุณีธีรนันที",
        "base_path": BILARA_DATA_PATH / "translation" / "th" / "dhiranandi",
    },
    {
        "code": "jayasaro",
        "name": "พระอาจารย์ชยสาโร",
        "base_path": BILARA_DATA_PATH / "translation" / "th" / "jayasaro",
    },
]


def find_all_thai_files(translator: dict) -> list[Path]:
    """หาไฟล์แปลภาษาไทยทั้งหมดของ translator นี้"""
    base = translator["base_path"]
    if not base.exists():
        return []
    return sorted(base.rglob("*_translation-th-*.json"))


def extract_sutta_id_from_translation(path: Path) -> str:
    """ดึง sutta_id จากชื่อไฟล์ translation
    เช่น mn26_translation-th-dhiranandi.json → mn26
    """
    return path.name.split("_translation-")[0]


def load_translator(translator: dict) -> dict[str, int]:
    """โหลดคำแปลของ translator หนึ่งเข้า translation table

    Returns:
        {"files": int, "segments": int}
    """
    files = find_all_thai_files(translator)
    if not files:
        print(f"   ⚠️  ไม่พบไฟล์สำหรับ {translator['code']}")
        return {"files": 0, "segments": 0}

    total_segments = 0
    total_files = 0

    conn = get_connection()
    try:
        cur = conn.cursor()

        for path in tqdm(files, desc=f"   📖 {translator['code']}"):
            sutta_id = extract_sutta_id_from_translation(path)

            with open(path, "r", encoding="utf-8") as f:
                th_data: dict[str, str] = json.load(f)

            count = 0
            for segment_id_str, text in th_data.items():
                if not text or not text.strip():
                    continue

                # หา segment.id จาก segment_id string
                cur.execute(
                    "SELECT id FROM segment WHERE segment_id = %s",
                    (segment_id_str,),
                )
                row = cur.fetchone()
                if not row:
                    continue  # segment นี้ยังไม่ได้ load ลง DB

                segment_db_id = row[0]

                # Insert หรืออัปเดตใน translation table
                cur.execute(
                    """
                    INSERT INTO translation (segment_id, language, edition, translator, text)
                    VALUES (%s, 'th', %s, %s, %s)
                    ON CONFLICT (segment_id, language, edition) DO UPDATE SET
                        text = EXCLUDED.text,
                        translator = EXCLUDED.translator
                    """,
                    (segment_db_id, translator["code"], translator["name"], text.strip()),
                )
                count += 1

            conn.commit()
            total_segments += count
            total_files += 1
            print(f"      ✅ {sutta_id}: {count} segments")

        return {"files": total_files, "segments": total_segments}

    except Exception as e:
        conn.rollback()
        print(f"\n❌ เกิดข้อผิดพลาด ({translator['code']}): {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def load_all() -> None:
    """โหลดคำแปลไทย CC0 ทั้งหมด"""
    print("=" * 60)
    print("🇹🇭 Thai CC0 Translation Loader")
    print("   แหล่งข้อมูล: SuttaCentral bilara-data (CC0)")
    print("=" * 60)

    # สร้างตารางถ้ายังไม่มี (รวม translation table)
    create_tables()

    grand_total = {"files": 0, "segments": 0}

    for translator in TH_TRANSLATORS:
        print(f"\n📚 กำลังโหลด: {translator['code']} ({translator['name']})")
        result = load_translator(translator)
        grand_total["files"] += result["files"]
        grand_total["segments"] += result["segments"]
        print(f"   รวม: {result['files']} ไฟล์, {result['segments']} segments")

    print("\n" + "=" * 60)
    print("✅ โหลดคำแปลไทย CC0 เสร็จสมบูรณ์!")
    print(f"   รวม: {grand_total['files']} ไฟล์, {grand_total['segments']} segments")
    print()
    print("💡 หากต้องการเพิ่มคำแปลจากแหล่งอื่น (เช่น MCU, ฉบับหลวง)")
    print("   ต้องได้รับอนุญาตก่อน แล้วสร้าง script แยกโดยใช้ edition ต่างกัน")
    print("=" * 60)


if __name__ == "__main__":
    load_all()
