from db.connection import get_connection

def map_volumes():
    mapping = {
        # Vinaya
        "pli-tv-bu-vb-book": 1,  # มหาวิภังค์ (ปาราชิก-ปาจิตตีย์) - ปูมหลังคือเล่ม 1-2
        "pli-tv-bi-vb-book": 3,  # ภิกขุนีวิภังค์
        "pli-tv-kd-book": 4,     # มหาวรรค (เล่ม 4-5) และ จุลวรรค (เล่ม 6-7)
        "pli-tv-pvr-book": 8,    # ปริวาร
        
        # Sutta
        "dn-book": 9,            # ทีฆนิกาย (9-11)
        "mn-book": 12,           # มัชฌิมนิกาย (12-14)
        "sn-book": 15,           # สังยุตตนิกาย (15-19)
        "an-book": 20,           # อังคุตตรนิกาย (20-24)
        "kn-book": 25,           # ขุททกนิกาย (25-33)
        
        # Abhidhamma
        "ds-book": 34,           # ธัมมสังคณี
        "vb-book": 35,           # วิภังค์
        "dt-book": 36,           # ธาตุกถา
        "pp-book": 36,           # ปุคคลบัญญัติ (เล่มเดียวกับธาตุกถาในสยามรัฐ)
        "kv-book": 37,           # กถาวัตถุ
        "ya-book": 38,           # ยมก (38-39)
        "patthana-book": 40      # ปัฏฐาน (40-45)
    }
    
    conn = get_connection()
    cur = conn.cursor()
    
    updated = 0
    for code, vol in mapping.items():
        cur.execute("UPDATE book SET thai_volume = %s WHERE code = %s", (vol, code))
        if cur.rowcount > 0:
            updated += 1
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"Mapped {updated} books to Thai volumes.")

if __name__ == "__main__":
    map_volumes()
