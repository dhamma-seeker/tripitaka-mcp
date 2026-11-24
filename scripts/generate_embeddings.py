"""
Tripitaka MCP Server — Generate Embeddings

สร้าง vector embeddings สำหรับทุก segment ใน database
ใช้สำหรับ semantic search

Usage:
    python scripts/generate_embeddings.py

หมายเหตุ:
    - รันหลังจาก data_loader.py โหลดข้อมูลเสร็จแล้ว
    - ใช้เวลาพอสมควร ขึ้นอยู่กับจำนวน segments และขนาด model
    - สร้าง HNSW index หลังจากสร้าง embeddings เสร็จ
"""

import os
import sys

from dotenv import load_dotenv
from tqdm import tqdm

# เพิ่ม project root ใน path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from db.connection import get_connection, release_connection
from embedding.model import generate_embeddings_batch


BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))


def count_segments_without_embedding() -> int:
    """นับจำนวน segments ที่ยังไม่มี embedding"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM segment WHERE embedding IS NULL")
        return cur.fetchone()[0]
    finally:
        cur.close()
        release_connection(conn)


def generate_all_embeddings() -> None:
    """สร้าง embeddings สำหรับทุก segment ที่ยังไม่มี

    ใช้ text_pali อย่างเดียวเป็น input (ไม่ concat กับคำแปล)
    เพราะโมเดล fine-tuned รองรับการ align ข้ามภาษา Pāli↔English ได้โดยตรง
    (วัดแล้ว BUCC 22% → 90% เทียบกับ concat เดิมที่ใช้ไม่ได้กับ segment ที่ไม่มีคำแปล)
    """
    total = count_segments_without_embedding()
    if total == 0:
        print("✅ ทุก segment มี embedding แล้ว!")
        return

    print(f"🔄 ต้องสร้าง embedding สำหรับ {total:,} segments")
    print(f"   Batch size: {BATCH_SIZE}")

    conn = get_connection()
    try:
        cur = conn.cursor()

        # อ่าน segments ทีละ batch
        offset = 0
        processed = 0

        with tqdm(total=total, desc="🧠 Generating embeddings") as pbar:
            while True:
                cur.execute(
                    """
                    SELECT id, text_pali, text_english, text_thai
                    FROM segment
                    WHERE embedding IS NULL
                    ORDER BY id
                    LIMIT %s
                    """,
                    (BATCH_SIZE,),
                )
                rows = cur.fetchall()
                if not rows:
                    break

                # ใช้ text_pali อย่างเดียว — โมเดล fine-tuned เก่งข้ามภาษาโดยตรง
                segment_ids = []
                texts = []
                for row in rows:
                    seg_id, text_pali, text_english, text_thai = row
                    segment_ids.append(seg_id)
                    texts.append(text_pali or "")

                # สร้าง embeddings
                embeddings = generate_embeddings_batch(texts, batch_size=BATCH_SIZE)

                # อัปเดต database
                for seg_id, embedding in zip(segment_ids, embeddings):
                    cur.execute(
                        "UPDATE segment SET embedding = %s WHERE id = %s",
                        (embedding, seg_id),
                    )

                conn.commit()
                processed += len(rows)
                pbar.update(len(rows))

        print(f"\n✅ สร้าง embedding เสร็จ: {processed:,} segments")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def create_vector_index() -> None:
    """สร้าง HNSW index สำหรับ vector similarity search

    ควรรันหลังจากสร้าง embeddings เสร็จแล้ว
    HNSW index จะเร่งความเร็วการค้นหา vector อย่างมาก
    """
    print("📊 กำลังสร้าง HNSW vector index...")
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_segment_embedding
            ON segment USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
            """
        )
        conn.commit()
        print("✅ สร้าง HNSW index เรียบร้อย")
    except Exception as e:
        conn.rollback()
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


if __name__ == "__main__":
    generate_all_embeddings()
    create_vector_index()
