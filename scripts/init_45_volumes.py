from db.connection import get_connection

def init_45_volumes():
    conn = get_connection()
    cur = conn.cursor()

    print("🚀 สตาร์ทการลงทะเบียนพระไตรปิฎก 45 เล่ม (Ver. 2)...")

    # 1. Ensure Pitakas exist
    # id, code, pali, thai, eng, sort
    pitakas = [
        (1, "vinaya", "Vinayapiṭaka", "พระวินัยปิฎก", "Vinaya Pitaka", 1),
        (2, "sutta", "Suttantapiṭaka", "พระสุตตันตปิฎก", "Suttanta Pitaka", 2),
        (3, "abhidhamma", "Abhidhammapiṭaka", "พระอภิธรรมปิฎก", "Abhidhamma Pitaka", 3)
    ]
    for p_id, p_code, p_pali, p_th, p_en, sort in pitakas:
        cur.execute("""
            INSERT INTO pitaka (id, code, name_pali, name_thai, name_english, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET name_thai = EXCLUDED.name_thai, code = EXCLUDED.code
        """, (p_id, p_code, p_pali, p_th, p_en, sort))

    # 2. Define Nikayas & Books mapping
    # (Pitaka_ID, Code, Pali, Thai, English)
    nikaya_structure = [
        # Vinaya
        (1, "vin-v", "Vibhaṅga", "มหาวิภังค์/ภิกขุนีวิภังค์", "Vibhanga"),
        (1, "vin-m", "Mahāvagga", "มหาวรรค", "Mahavagga"),
        (1, "vin-c", "Cullavagga", "จุลวรรค", "Cullavagga"),
        (1, "vin-p", "Parivāra", "ปริวาร", "Parivara"),
        # Suttanta
        (2, "dn", "Dīghanikāya", "ทีฆนิกาย", "Digha Nikaya"),
        (2, "mn", "Majjhimanikāya", "มัชฌิมนิกาย", "Majjhima Nikaya"),
        (2, "sn", "Saṃyuttanikāya", "สังยุตตนิกาย", "Samyutta Nikaya"),
        (2, "an", "Aṅguttaranikāya", "อังคุตตรนิกาย", "Anguttara Nikaya"),
        (2, "kn", "Khuddakanikāya", "ขุททกนิกาย", "Khuddaka Nikaya"),
        # Abhidhamma
        (3, "ds", "Dhammasaṅgaṇī", "ธัมมสังคณี", "Dhammasangani"),
        (3, "vb", "Vibhaṅga", "วิภังค์", "Vibhanga"),
        (3, "dt-pp", "Dhātukathā-Puggalapaññatti", "ธาตุกถา-ปุคคลบัญญัติ", "Dhatukatha-Puggalapannatti"),
        (3, "kv", "Kathāvatthu", "กถาวัตถุ", "Kathavatthu"),
        (3, "ym", "Yamaka", "ยมก", "Yamaka"),
        (3, "pt", "Paṭṭhāna", "ปัฏฐาน", "Patthana"),
    ]

    # Map volume range to Nikaya Code
    # Based on Thai standard 45 vols
    vol_map = {
        1: "vin-v", 2: "vin-v", 3: "vin-v",
        4: "vin-m", 5: "vin-m",
        6: "vin-c", 7: "vin-c",
        8: "vin-p",
        9: "dn", 10: "dn", 11: "dn",
        12: "mn", 13: "mn", 14: "mn",
        15: "sn", 16: "sn", 17: "sn", 18: "sn", 19: "sn",
        20: "an", 21: "an", 22: "an", 23: "an", 24: "an",
        25: "kn", 26: "kn", 27: "kn", 28: "kn", 29: "kn", 30: "kn", 31: "kn", 32: "kn", 33: "kn",
        34: "ds",
        35: "vb",
        36: "dt-pp",
        37: "kv",
        38: "ym", 39: "ym",
        40: "pt", 41: "pt", 42: "pt", 43: "pt", 44: "pt", 45: "pt",
    }

    # First, Insert Nikayas
    nikaya_ids = {}
    for p_id, code, pali, thai, eng in nikaya_structure:
        cur.execute("""
            INSERT INTO nikaya (pitaka_id, code, name_pali, name_thai, name_english)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET name_thai = EXCLUDED.name_thai
            RETURNING id
        """, (p_id, code, pali, thai, eng))
        nikaya_ids[code] = cur.fetchone()[0]

    # Second, Insert all 45 Books
    for v in range(1, 46):
        n_code = vol_map[v]
        n_id = nikaya_ids[n_code]
        cur.execute("""
            INSERT INTO book (nikaya_id, code, thai_volume, name_thai, name_english)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (thai_volume) DO UPDATE SET nikaya_id = EXCLUDED.nikaya_id
        """, (n_id, f"vol{v}", v, f"เล่มที่ {v}", f"Volume {v}"))

    conn.commit()
    print("✅ ลงทะเบียนครบ 45 เล่มเรียบร้อยแล้ว!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    init_45_volumes()
