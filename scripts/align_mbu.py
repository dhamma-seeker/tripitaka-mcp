"""
Tripitaka MCP Server — MBU Fuzzy Alignment (Phase 2.2 PoC)
รันเพื่อจัดการข้อมูล MBU เข้าสู่ฐานข้อมูลหลักในตาราง translation
ด้วยเทคนิค Sentence Merging, Vector Alignment, Sutta Filter, และ Staged Commit
"""

import sys
import os
import io
import csv
import urllib.request
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_connection, release_connection

def clean_html(text: str) -> str:
    """ลบ HTML tags จากสตริง"""
    for tag in ['<H1>', '</H1>', '<H2>', '</H2>', '<H3>', '</H3>', '<H4>', '</H4>', '<B>', '</B>', '<I>', '</I>']:
        text = text.replace(tag, '')
    return text.strip()

def fetch_and_merge_mbu(url: str) -> list[str]:
    """
    Step 1: Pre-processing
    รวมบรรทัดที่ขาดกลางประโยค โดยดูจากเครื่องหมายจุด (.)
    """
    print(f"📥 กำลังดาวน์โหลดข้อมูลจาก {url} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req).read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(response))
    
    merged_sentences = []
    current_sentence = ""
    
    for row in reader:
        line = clean_html(row.get('Text', ''))
        if not line or line.startswith('เล่ม'):
            continue
            
        # รวมบรรทัดเข้าไป
        if current_sentence:
            current_sentence += " " + line
        else:
            current_sentence = line
            
        # ถ้าจบบรรทัดด้วยเครื่องหมายจุด (.) หรือเป็นบรรทัดหัวเรื่องที่ควรจบ
        if line.endswith('.') or line.endswith('ฯ') or len(current_sentence) > 150:
            merged_sentences.append(current_sentence.strip())
            current_sentence = ""
            
    if current_sentence:
        merged_sentences.append(current_sentence.strip())
        
    return merged_sentences

def run_alignment_pipeline():
    print("🚀 เริ่มระบบ MBU Fuzzy Alignment Pipeline")
    
    # ดึงข้อมูลตัวอย่าง: ทีฆนิกาย ศีลขันธวรรค ตอนต้น (DN 1) เล่ม 11 ของ MBU
    url = "https://huggingface.co/datasets/uisp/tripitaka-mbu/resolve/main/11/110001.csv"
    sentences = fetch_and_merge_mbu(url)
    print(f"   ➤ แกะรูปประโยคสมบูรณ์ได้ทั้งหมด {len(sentences)} ประโยค")
    
    print("\n🧠 กำลังโหลด AI Model (paraphrase-multilingual-MiniLM-L12-v2)...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        success_count = 0
        pending_count = 0
        rejected_count = 0
        
        print("\n🔍 เริ่มค้นหา Fuzzymatching ลง Database...")
        # เพื่อใช้ Sequence Constraint ให้สมบูรณ์แบบที่สุด (สแกนทีละประโยคของ MBU เทียบกับเฉพาะ DN)
        for text in tqdm(sentences, desc="Aligning MBU Sentences"):
            if len(text) < 10:
                continue
                
            vector = model.encode(text).tolist()
            
            # Step 3: Alignment with Sutta Filtered (หาเฉพาะ 'dn%') กรองเอาตัวที่ใกล้เคียงที่สุด
            # หา Similarity Score (1 - Cosine Distance)
            cur.execute("""
                SELECT segment.segment_id, segment.id, 
                       1 - (segment.embedding <=> %s::vector) AS similarity 
                FROM segment
                JOIN section ON segment.section_id = section.id
                WHERE section.sutta_id LIKE 'dn%%'
                ORDER BY segment.embedding <=> %s::vector 
                LIMIT 1;
            """, (vector, vector))
            
            result = cur.fetchone()
            if not result:
                continue
                
            segment_id_str, segment_db_id, sim = result
            confidence = float(sim)
            
            # Step 4: Staged Commit Logic
            status = 'rejected'
            if confidence >= 0.90:
                status = 'auto_verified'
                success_count += 1
            elif confidence >= 0.75:
                status = 'pending_review'
                pending_count += 1
            else:
                rejected_count += 1
                continue # ข้าม ไม่บันทึก
                
            # บันทึกลงตาราง translation
            cur.execute("""
                INSERT INTO translation (
                    segment_id, language, edition, translator, text, 
                    alignment_confidence, alignment_status
                )
                VALUES (%s, 'th', 'mbu', 'มหามกุฏราชวิทยาลัย', %s, %s, %s)
                ON CONFLICT (segment_id, language, edition) DO UPDATE SET
                    text = EXCLUDED.text,
                    alignment_confidence = EXCLUDED.alignment_confidence,
                    alignment_status = EXCLUDED.alignment_status;
            """, (segment_db_id, text, confidence, status))
            
        conn.commit()
        
        print("\n✨ อัปโหลด Staged Commit เข้าระบบฐานข้อมูลสำเร็จ!")
        print(f"✅ Auto-Verified (≥90%): {success_count} segments")
        print(f"⚠️ Pending Review (75-89%): {pending_count} segments")
        print(f"❌ Rejected (<75% - ไม่บันทึก): {rejected_count} segments")
        
        # แสดงข้อมูลที่ Auto-Verified ให้ดูสัก 3-4 แถวเพื่อพิสูจน์
        print("\nตัวอย่างผลลัพธ์ที่ได้รับความเชื่อมั่นสูงเกรด (Auto-Verified):")
        cur.execute("""
            SELECT s.segment_id, t.text, t.alignment_confidence 
            FROM translation t
            JOIN segment s ON t.segment_id = s.id
            WHERE t.edition = 'mbu' AND t.alignment_status = 'auto_verified'
            ORDER BY t.alignment_confidence DESC
            LIMIT 3;
        """)
        for row in cur.fetchall():
            print(f"[{row[0]}] (มั่นใจ {row[2]*100:.1f}%): {row[1]}")
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
    finally:
        cur.close()
        release_connection(conn)

if __name__ == "__main__":
    run_alignment_pipeline()
