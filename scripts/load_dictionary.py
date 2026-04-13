"""
Tripitaka MCP Server — Load Pali Dictionaries

ดาวน์โหลดและนำเข้าข้อมูล Open Source Pali Dictionaries จาก SuttaCentral
(PTS, DPPN, Dhammika) โดยแกะ HTML tags ผ่าน BeautifulSoup ให้เป็น Plain text
และจัดเก็บลงตาราง dictionary

ใช้งาน: python scripts/load_dictionary.py
"""

import json
import os
import sys

import requests
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values
from tqdm import tqdm

# เพิ่ม project root ใน path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_connection, release_connection

DICTIONARIES = [
    {
        "url": "https://raw.githubusercontent.com/suttacentral/sc-data/master/dictionaries/complex/en/pli2en_pts.json",
        "source": "pts",
        "name": "Pali Text Society Pali-English Dictionary"
    },
    {
        "url": "https://raw.githubusercontent.com/suttacentral/sc-data/master/dictionaries/complex/en/pli2en_dppn.json",
        "source": "dppn",
        "name": "Dictionary of Pali Proper Names"
    },
    {
        "url": "https://raw.githubusercontent.com/suttacentral/sc-data/master/dictionaries/complex/en/pli2en_dhammika.json",
        "source": "dhammika",
        "name": "Nature and Environment in Early Buddhism (Dhammika)"
    }
]

def clean_html(raw_html: str) -> str:
    """แปลง HTML ให้เป็น Plain Text ที่อ่านง่ายขึ้น"""
    if not raw_html:
        return ""
    
    # ใส่วงเล็บให้ tags ที่มักจะเป็น grammatical info
    raw_html = raw_html.replace("<span class='grammar'>", " <span class='grammar'>[")
    raw_html = raw_html.replace("</span>", "] </span>")
    
    soup = BeautifulSoup(raw_html, "html.parser")
    # ดึงข้อความออกมา โดยคั่นด้วย new line สำหรับ block elements
    text = soup.get_text(separator="\n", strip=True)
    
    # ทำความสะอาดช่องว่างเกิน
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def load_dictionaries():
    print("📚 กำลังโหลด Pali Dictionaries...")
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        for dic in DICTIONARIES:
            print(f"\n📥 กำลังดาวน์โหลด: {dic['name']} ({dic['source']})")
            response = requests.get(dic["url"])
            response.raise_for_status()
            data = response.json()
            
            print(f"🧹 กำลังทำความสะอาด HTML และเตรียมข้อมูล ({len(data):,} คำ)")
            records = []
            for item in tqdm(data, desc="Parsing"):
                word = item.get("word")
                raw_text = item.get("text", "")
                if not word or not raw_text:
                    continue
                
                clean_text = clean_html(raw_text)
                
                records.append((
                    word.lower().strip(), 
                    "en",        # ทั้ง 3 เล่มนี้เป็น English
                    clean_text,
                    dic["source"]
                ))
            
            print(f"💾 กำลังบันทึกข้อมูล {dic['source']} ลงฐานข้อมูล...")
            
            # ลบข้อมูลเก่าของ source นี้เพื่อป้องกันข้อมูลซ้ำถ้าโหลดใหม่
            cur.execute("DELETE FROM dictionary WHERE source = %s", (dic["source"],))
            
            # Batch insert
            insert_query = """
                INSERT INTO dictionary (word, language, text, source)
                VALUES %s
            """
            
            execute_values(
                cur,
                insert_query,
                records,
                page_size=1000
            )
            
            conn.commit()
            print(f"✅ บันทึก {dic['source']} สำเร็จ!")
            
        # ---------------- Load Payutto from Local File ----------------
        payutto_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'payutto_dict.json')
        if os.path.exists(payutto_path):
            print("\n📥 กำลังโหลดข้อมูลจากไฟล์: พจนานุกรมพุทธศาสน์ (Payutto)")
            with open(payutto_path, 'r', encoding='utf-8') as f:
                payutto_data = json.load(f)
                
            print(f"🧹 กำลังเตรียมข้อมูล Payutto ({len(payutto_data):,} คำ)")
            records = []
            for item in tqdm(payutto_data, desc="Parsing Payutto"):
                word = item.get("word")
                text = item.get("definition")
                if not word or not text:
                    continue
                
                records.append((
                    word.strip(), 
                    "thai",
                    text,
                    "payutto"
                ))
            
            print(f"💾 กำลังบันทึกข้อมูล payutto ลงฐานข้อมูล...")
            cur.execute("DELETE FROM dictionary WHERE source = %s", ("payutto",))
            
            insert_query = """
                INSERT INTO dictionary (word, language, text, source)
                VALUES %s
            """
            
            execute_values(
                cur,
                insert_query,
                records,
                page_size=1000
            )
            
            conn.commit()
            print("✅ บันทึก payutto สำเร็จ!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
    finally:
        cur.close()
        release_connection(conn)


if __name__ == "__main__":
    load_dictionaries()
