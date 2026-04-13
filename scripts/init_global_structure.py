import requests
from db.connection import get_connection

def fetch_suttas(nikaya_code):
    print(f"📡 Fetching structure for {nikaya_code} from SuttaCentral...")
    url = f"https://suttacentral.net/api/menu/{nikaya_code}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ Error fetching {nikaya_code}: {e}")
        return None

def init_global_structure():
    conn = get_connection()
    cur = conn.cursor()

    # Mapping of Nikaya Code to Thai Volumes
    # (Nikaya_Code, [Volume_List], Sutta_Per_Vol_Approx)
    mapping = [
        ("dn", [9, 10, 11], 12),
        ("mn", [12, 13, 14], 51),
        ("sn", [15, 16, 17, 18, 19], 600), # SN has thousands of small suttas
        ("an", [20, 21, 22, 23, 24], 500), # AN also has many
        ("pi-tv-bu-pm", [1], 100), # Special case for Patimokkha
    ]

    print("🚀 เริ่มต้นการลงทะเบียนพิกัดพระสูตรจาก SuttaCentral...")

    for code, vols, approx in mapping:
        data = fetch_suttas(code)
        if not data: continue
        
        # SuttaCentral menu data is nested. We need to flatten it.
        # This is a simplified flattening for Demo/PoC
        suttas = []
        def walk(node):
            if isinstance(node, list):
                for item in node: walk(item)
            elif isinstance(node, dict):
                if node.get("uid") and not node.get("children"):
                    suttas.append((node["uid"], node.get("title", node["uid"])))
                if node.get("children"):
                    walk(node["children"])
        
        walk(data)
        print(f"✅ Found {len(suttas)} suttas for {code}")

        # Distribute suttas into volumes
        for i, (uid, title) in enumerate(suttas):
            # Pick a volume from the list based on index
            vol_idx = min(i // approx, len(vols) - 1)
            vol = vols[vol_idx]
            
            # 1. Ensure book exists for mapping
            cur.execute("SELECT id FROM book WHERE thai_volume = %s", (vol,))
            book_row = cur.fetchone()
            if not book_row: continue
            book_id = book_row[0]

            # 2. Insert Section
            try:
                cur.execute("""
                    INSERT INTO section (book_id, sutta_id, title_pali)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (sutta_id) DO UPDATE SET title_pali = EXCLUDED.title_pali
                    RETURNING id
                """, (book_id, uid, title))
                sec_id = cur.fetchone()[0]

                # 3. Create Translation Batch (Deferred)
                cur.execute("""
                    INSERT INTO translation_batch (section_id, thai_volume, status)
                    VALUES (%s, %s, 'deferred')
                    ON CONFLICT DO NOTHING
                """, (sec_id, vol))
            except Exception as e:
                # print(f"Skip {uid}: {e}")
                pass

    conn.commit()
    print("✨ ลงทะเบียนพิกัดพระสูตรสากลเรียบร้อย (Vinaya & Sutta Main)")
    cur.close()
    conn.close()

if __name__ == "__main__":
    init_global_structure()
