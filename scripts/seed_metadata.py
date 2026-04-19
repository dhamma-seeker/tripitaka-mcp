"""
Tripitaka MCP Server — Seed Metadata

ข้อมูล pitaka, nikaya เบื้องต้น (static/hardcoded)
ข้อมูลเหล่านี้ค่อนข้างคงที่ ไม่เปลี่ยนแปลง

Usage:
    python scripts/seed_metadata.py
"""

import os
import sys

# เพิ่ม project root ใน path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_connection, release_connection
from db.schema import create_tables


# =============================================================================
# ข้อมูล Pitaka (ปิฎก 3)
# =============================================================================
PITAKAS = [
    {
        "code": "vinaya",
        "name_pali": "Vinayapiṭaka",
        "name_thai": "วินัยปิฎก",
        "name_english": "Basket of Discipline",
        "sort_order": 1,
    },
    {
        "code": "sutta",
        "name_pali": "Suttantapiṭaka",
        "name_thai": "สุตตันตปิฎก",
        "name_english": "Basket of Discourses",
        "sort_order": 2,
    },
    {
        "code": "abhidhamma",
        "name_pali": "Abhidhammapiṭaka",
        "name_thai": "อภิธรรมปิฎก",
        "name_english": "Basket of Higher Teaching",
        "sort_order": 3,
    },
]


# =============================================================================
# ข้อมูล Nikaya (นิกาย/หมวด) — เฉพาะสุตตันตปิฎก (เริ่มต้น)
# =============================================================================
NIKAYAS_SUTTA = [
    {
        "code": "dn",
        "name_pali": "Dīghanikāya",
        "name_thai": "ทีฆนิกาย",
        "name_english": "Long Discourses",
        "sort_order": 1,
    },
    {
        "code": "mn",
        "name_pali": "Majjhimanikāya",
        "name_thai": "มัชฌิมนิกาย",
        "name_english": "Middle Discourses",
        "sort_order": 2,
    },
    {
        "code": "sn",
        "name_pali": "Saṁyuttanikāya",
        "name_thai": "สังยุตตนิกาย",
        "name_english": "Connected Discourses",
        "sort_order": 3,
    },
    {
        "code": "an",
        "name_pali": "Aṅguttaranikāya",
        "name_thai": "อังคุตตรนิกาย",
        "name_english": "Numerical Discourses",
        "sort_order": 4,
    },
    {
        "code": "kn",
        "name_pali": "Khuddakanikāya",
        "name_thai": "ขุททกนิกาย",
        "name_english": "Minor Collection",
        "sort_order": 5,
    },
]


# =============================================================================
# ข้อมูล Nikaya — วินัยปิฎก
# =============================================================================
NIKAYAS_VINAYA = [
    {
        "code": "pli-tv-bu-vb",
        "name_pali": "Bhikkhuvibhaṅga",
        "name_thai": "ภิกขุวิภังค์",
        "name_english": "Analysis of Rules for Monks",
        "sort_order": 1,
    },
    {
        "code": "pli-tv-bi-vb",
        "name_pali": "Bhikkhunīvibhaṅga",
        "name_thai": "ภิกขุนีวิภังค์",
        "name_english": "Analysis of Rules for Nuns",
        "sort_order": 2,
    },
    {
        "code": "pli-tv-kd",
        "name_pali": "Khandhaka",
        "name_thai": "ขันธกะ",
        "name_english": "Chapters on Legal Procedures",
        "sort_order": 3,
    },
    {
        "code": "pli-tv-pvr",
        "name_pali": "Parivāra",
        "name_thai": "ปริวาร",
        "name_english": "The Compendium",
        "sort_order": 4,
    },
]


# =============================================================================
# ข้อมูล Nikaya — อภิธรรมปิฎก
# =============================================================================
NIKAYAS_ABHIDHAMMA = [
    {
        "code": "ds",
        "name_pali": "Dhammasaṅgaṇī",
        "name_thai": "ธัมมสังคณี",
        "name_english": "Enumeration of Phenomena",
        "sort_order": 1,
    },
    {
        "code": "vb",
        "name_pali": "Vibhaṅga",
        "name_thai": "วิภังค์",
        "name_english": "Book of Analysis",
        "sort_order": 2,
    },
    {
        "code": "dt",
        "name_pali": "Dhātukathā",
        "name_thai": "ธาตุกถา",
        "name_english": "Discussion of Elements",
        "sort_order": 3,
    },
    {
        "code": "pp",
        "name_pali": "Puggalapaññatti",
        "name_thai": "ปุคคลบัญญัติ",
        "name_english": "Designation of Persons",
        "sort_order": 4,
    },
    {
        "code": "kv",
        "name_pali": "Kathāvatthu",
        "name_thai": "กถาวัตถุ",
        "name_english": "Points of Controversy",
        "sort_order": 5,
    },
    {
        "code": "ya",
        "name_pali": "Yamaka",
        "name_thai": "ยมก",
        "name_english": "Book of Pairs",
        "sort_order": 6,
    },
    {
        "code": "patthana",
        "name_pali": "Paṭṭhāna",
        "name_thai": "ปัฏฐาน",
        "name_english": "Book of Conditional Relations",
        "sort_order": 7,
    },
]


# =============================================================================
# ข้อมูล Book — KN sub-books (Khuddaka Nikāya มี 20 คัมภีร์ย่อย)
# ลำดับ volume_number ตาม SC canonical order
# =============================================================================
BOOKS_KN = [
    {"code": "kn-kp",     "name_pali": "Khuddakapāṭha",         "name_thai": "ขุททกปาฐะ",    "name_english": "Shorter Readings",             "volume_number": 1,  "sort_order": 1},
    {"code": "kn-dhp",    "name_pali": "Dhammapada",             "name_thai": "ธรรมบท",       "name_english": "Sayings of the Dhamma",        "volume_number": 2,  "sort_order": 2},
    {"code": "kn-ud",     "name_pali": "Udāna",                  "name_thai": "อุทาน",        "name_english": "Inspired Utterances",          "volume_number": 3,  "sort_order": 3},
    {"code": "kn-iti",    "name_pali": "Itivuttaka",             "name_thai": "อิติวุตตกะ",   "name_english": "So It Was Said",               "volume_number": 4,  "sort_order": 4},
    {"code": "kn-snp",    "name_pali": "Suttanipāta",            "name_thai": "สุตตนิบาต",    "name_english": "Sutta Collection",             "volume_number": 5,  "sort_order": 5},
    {"code": "kn-vv",     "name_pali": "Vimānavatthu",           "name_thai": "วิมานวัตถุ",   "name_english": "Stories of Heavenly Mansions", "volume_number": 6,  "sort_order": 6},
    {"code": "kn-pv",     "name_pali": "Petavatthu",             "name_thai": "เปตวัตถุ",     "name_english": "Stories of Ghosts",            "volume_number": 7,  "sort_order": 7},
    {"code": "kn-thag",   "name_pali": "Theragāthā",             "name_thai": "เถรคาถา",      "name_english": "Verses of the Elder Monks",    "volume_number": 8,  "sort_order": 8},
    {"code": "kn-thig",   "name_pali": "Therīgāthā",             "name_thai": "เถรีคาถา",     "name_english": "Verses of the Elder Nuns",     "volume_number": 9,  "sort_order": 9},
    {"code": "kn-tha-ap", "name_pali": "Therāpadāna",            "name_thai": "เถราปทาน",     "name_english": "Stories of the Elder Monks",   "volume_number": 10, "sort_order": 10},
    {"code": "kn-thi-ap", "name_pali": "Therīapadāna",           "name_thai": "เถรีอปทาน",    "name_english": "Stories of the Elder Nuns",    "volume_number": 11, "sort_order": 11},
    {"code": "kn-bv",     "name_pali": "Buddhavaṁsa",            "name_thai": "พุทธวงศ์",     "name_english": "Lineage of the Buddhas",       "volume_number": 12, "sort_order": 12},
    {"code": "kn-cp",     "name_pali": "Cariyāpiṭaka",           "name_thai": "จริยาปิฎก",    "name_english": "Basket of Conduct",            "volume_number": 13, "sort_order": 13},
    {"code": "kn-ja",     "name_pali": "Jātaka",                 "name_thai": "ชาดก",         "name_english": "Birth Stories",                "volume_number": 14, "sort_order": 14},
    {"code": "kn-mnd",    "name_pali": "Mahāniddesa",            "name_thai": "มหานิทเทส",    "name_english": "Great Exposition",             "volume_number": 15, "sort_order": 15},
    {"code": "kn-cnd",    "name_pali": "Cūḷaniddesa",            "name_thai": "จูฬนิทเทส",    "name_english": "Lesser Exposition",            "volume_number": 16, "sort_order": 16},
    {"code": "kn-ps",     "name_pali": "Paṭisambhidāmagga",      "name_thai": "ปฏิสัมภิทามรรค", "name_english": "Path of Discrimination",       "volume_number": 17, "sort_order": 17},
    {"code": "kn-ne",     "name_pali": "Nettippakaraṇa",         "name_thai": "เนตติปกรณ์",   "name_english": "The Guide",                    "volume_number": 18, "sort_order": 18},
    {"code": "kn-pe",     "name_pali": "Peṭakopadesa",           "name_thai": "เปฏโกปเทส",    "name_english": "Instruction on the Piṭaka",    "volume_number": 19, "sort_order": 19},
    {"code": "kn-mil",    "name_pali": "Milindapañha",           "name_thai": "มิลินทปัญหา",  "name_english": "Questions of King Milinda",    "volume_number": 20, "sort_order": 20},
]


def seed_kn_books(cur, nikaya_ids: dict[str, int]) -> dict[str, int]:
    """Insert KN sub-books ทั้ง 20 คัมภีร์ ภายใต้ nikaya 'kn'"""
    kn_id = nikaya_ids["kn"]
    book_ids = {}
    for b in BOOKS_KN:
        cur.execute(
            """
            INSERT INTO book (nikaya_id, code, name_pali, name_thai, name_english, volume_number, sort_order)
            VALUES (%(nikaya_id)s, %(code)s, %(name_pali)s, %(name_thai)s, %(name_english)s, %(volume_number)s, %(sort_order)s)
            ON CONFLICT (code) DO UPDATE SET
                nikaya_id = EXCLUDED.nikaya_id,
                name_pali = EXCLUDED.name_pali,
                name_thai = EXCLUDED.name_thai,
                name_english = EXCLUDED.name_english,
                volume_number = EXCLUDED.volume_number,
                sort_order = EXCLUDED.sort_order
            RETURNING id;
            """,
            {**b, "nikaya_id": kn_id},
        )
        book_ids[b["code"]] = cur.fetchone()[0]
    return book_ids


def seed_pitakas(cur) -> dict[str, int]:
    """Insert ปิฎก 3 และคืน mapping code → id

    Args:
        cur: database cursor

    Returns:
        dict mapping pitaka code to pitaka id
    """
    pitaka_ids = {}
    for p in PITAKAS:
        cur.execute(
            """
            INSERT INTO pitaka (code, name_pali, name_thai, name_english, sort_order)
            VALUES (%(code)s, %(name_pali)s, %(name_thai)s, %(name_english)s, %(sort_order)s)
            ON CONFLICT (code) DO UPDATE SET
                name_pali = EXCLUDED.name_pali,
                name_thai = EXCLUDED.name_thai,
                name_english = EXCLUDED.name_english,
                sort_order = EXCLUDED.sort_order
            RETURNING id;
            """,
            p,
        )
        pitaka_ids[p["code"]] = cur.fetchone()[0]
    return pitaka_ids


def seed_nikayas(cur, pitaka_ids: dict[str, int]) -> dict[str, int]:
    """Insert นิกาย/หมวดทั้งหมด และคืน mapping code → id

    Args:
        cur: database cursor
        pitaka_ids: mapping pitaka code → id

    Returns:
        dict mapping nikaya code to nikaya id
    """
    nikaya_ids = {}

    all_nikayas = [
        ("sutta", NIKAYAS_SUTTA),
        ("vinaya", NIKAYAS_VINAYA),
        ("abhidhamma", NIKAYAS_ABHIDHAMMA),
    ]

    for pitaka_code, nikayas in all_nikayas:
        pitaka_id = pitaka_ids[pitaka_code]
        for n in nikayas:
            cur.execute(
                """
                INSERT INTO nikaya (pitaka_id, code, name_pali, name_thai, name_english, sort_order)
                VALUES (%(pitaka_id)s, %(code)s, %(name_pali)s, %(name_thai)s, %(name_english)s, %(sort_order)s)
                ON CONFLICT (code) DO UPDATE SET
                    pitaka_id = EXCLUDED.pitaka_id,
                    name_pali = EXCLUDED.name_pali,
                    name_thai = EXCLUDED.name_thai,
                    name_english = EXCLUDED.name_english,
                    sort_order = EXCLUDED.sort_order
                RETURNING id;
                """,
                {**n, "pitaka_id": pitaka_id},
            )
            nikaya_ids[n["code"]] = cur.fetchone()[0]

    return nikaya_ids


def seed_all() -> None:
    """รัน seed ข้อมูล metadata ทั้งหมด"""
    conn = get_connection()
    try:
        cur = conn.cursor()

        print("📦 กำลัง seed ข้อมูล pitaka...")
        pitaka_ids = seed_pitakas(cur)
        print(f"   ✅ pitaka: {len(pitaka_ids)} รายการ")

        print("📦 กำลัง seed ข้อมูล nikaya...")
        nikaya_ids = seed_nikayas(cur, pitaka_ids)
        print(f"   ✅ nikaya: {len(nikaya_ids)} รายการ")

        print("📦 กำลัง seed ข้อมูล KN sub-books...")
        kn_book_ids = seed_kn_books(cur, nikaya_ids)
        print(f"   ✅ KN books: {len(kn_book_ids)} รายการ")

        conn.commit()
        print("\n✅ Seed metadata เรียบร้อย!")
        print(f"   Pitakas: {list(pitaka_ids.keys())}")
        print(f"   Nikayas: {list(nikaya_ids.keys())}")
        print(f"   KN books: {list(kn_book_ids.keys())}")

    except Exception as e:
        conn.rollback()
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


if __name__ == "__main__":
    # สร้างตารางก่อน (ถ้ายังไม่มี)
    create_tables()
    # แล้ว seed ข้อมูล
    seed_all()
