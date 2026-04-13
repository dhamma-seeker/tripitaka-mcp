from db.connection import get_connection

def cleanup_metadata():
    conn = get_connection()
    cur = conn.cursor()

    print("🧹 กำลังทำความสะอาดข้อมูลหมวดหมู่ (Pitaka, Nikaya)...")

    try:
        # 1. ล้างข้อมูล Nikaya และ Book เพื่อป้องกันการซ้ำซ้อนในเชิงโครงสร้าง
        # หมายเหตุ: เราจะไม่ลบ Section หรือ Translation เพราะนั่นคือข้อมูลงานแปล
        # แต่เราจะเคลียร์ Nikaya และ Book เพื่อจัดลำดับใหม่
        cur.execute("DELETE FROM translation_batch") # เคลียร์คิวงานเดิมเพื่อจัดระเบียบใหม่
        cur.execute("DELETE FROM book CASCADE")
        cur.execute("DELETE FROM nikaya CASCADE")
        cur.execute("DELETE FROM pitaka CASCADE")
        
        conn.commit()
        print("✅ ล้างข้อมูลโครงสร้างเดิมเรียบร้อย")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error during cleanup: {e}")
        return

    # 2. Re-initialize with strict sorting
    print("🚀 กำลังลงทะเบียนพระไตรปิฎก 45 เล่ม พร้อมลำดับการเรียงที่ถูกต้อง...")

    # Pitakas
    pitakas = [
        (1, "vinaya", "Vinayapiṭaka", "พระวินัยปิฎก", "Vinaya Pitaka", 1),
        (2, "sutta", "Suttantapiṭaka", "พระสุตตันตปิฎก", "Suttanta Pitaka", 2),
        (3, "abhidhamma", "Abhidhammapiṭaka", "พระอภิธรรมปิฎก", "Abhidhamma Pitaka", 3)
    ]
    for p_id, p_code, p_pali, p_th, p_en, sort in pitakas:
        cur.execute("""
            INSERT INTO pitaka (id, code, name_pali, name_thai, name_english, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (p_id, p_code, p_pali, p_th, p_en, sort))

    # Nikayas with explicit sort order
    nikaya_structure = [
        # (Pitaka_ID, Code, Pali, Thai, English, Sort)
        (1, "vin-v", "Vibhaṅga", "ภิกขุวิภังค์/ภิกขุนีวิภังค์", "Vibhanga", 1),
        (1, "vin-m", "Mahāvagga", "มหาวรรค", "Mahavagga", 2),
        (1, "vin-c", "Cullavagga", "จุลวรรค", "Cullavagga", 3),
        (1, "vin-p", "Parivāra", "ปริวาร", "Parivara", 4),
        
        (2, "dn", "Dīghanikāya", "ทีฆนิกาย", "Digha Nikaya", 1),
        (2, "mn", "Majjhimanikāya", "มัชฌิมนิกาย", "Majjhima Nikaya", 2),
        (2, "sn", "Saṃyuttanikāya", "สังยุตตนิกาย", "Samyutta Nikaya", 3),
        (2, "an", "Aṅguttaranikāya", "อังคุตตรนิกาย", "Anguttara Nikaya", 4),
        (2, "kn", "Khuddakanikāya", "ขุททกนิกาย", "Khuddaka Nikaya", 5),
        
        (3, "ds", "Dhammasaṅgaṇī", "ธัมมสังคณี", "Dhammasangani", 1),
        (3, "vb", "Vibhaṅga", "วิภังค์", "Vibhanga", 2),
        (3, "dt", "Dhātukathā", "ธาตุกถา", "Dhatukatha", 3),
        (3, "pp", "Puggalapaññatti", "ปุคคลบัญญัติ", "Puggalapannatti", 4),
        (3, "kv", "Kathāvatthu", "กถาวัตถุ", "Kathavatthu", 5),
        (3, "ym", "Yamaka", "ยมก", "Yamaka", 6),
        (3, "pt", "Paṭṭhāna", "ปัฏฐาน", "Patthana", 7),
    ]

    nikaya_ids = {}
    for p_id, code, pali, thai, eng, sort in nikaya_structure:
        cur.execute("""
            INSERT INTO nikaya (pitaka_id, code, name_pali, name_thai, name_english, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (p_id, code, pali, thai, eng, sort))
        nikaya_ids[code] = cur.fetchone()[0]

    # Books Volume Mapping
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
        36: "dt", # Simplified to match Nikaya code
        37: "kv",
        38: "ym", 39: "ym",
        40: "pt", 41: "pt", 42: "pt", 43: "pt", 44: "pt", 45: "pt",
    }
    
    # Special case for Vol 36 (Dhatukatha + Puggalapannatti)
    # Actually, in some editions they are combined. I'll map it to Dhatukatha for now.

    for v in range(1, 46):
        n_code = vol_map.get(v, "dn")
        n_id = nikaya_ids[n_code]
        cur.execute("""
            INSERT INTO book (nikaya_id, code, thai_volume, name_thai, name_english, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (n_id, f"vol{v}", v, f"เล่มที่ {v}", f"Volume {v}", v))

    conn.commit()
    print("✅ จัดระเบียบโครงสร้าง 45 เล่มใหม่เรียบร้อย")
    cur.close()
    conn.close()

if __name__ == "__main__":
    cleanup_metadata()
