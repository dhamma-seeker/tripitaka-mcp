"""
Generate chunk + sutta embeddings for multi-level semantic search.

- chunk_embedding: กลุ่ม 6 segment ติดกันใน section เดียว → concat text_pali → embed
- sutta_embedding: ค่าเฉลี่ยเวกเตอร์ของ segment ใน section เดียว (AVG ใน SQL ไม่ต้อง re-embed)

Usage:
    python scripts/generate_multilevel_embeddings.py

รันหลังจาก generate_embeddings.py สร้าง segment.embedding ครบแล้ว
"""
import os
import sys

from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from db.connection import get_connection, release_connection
from embedding.model import generate_embeddings_batch

CHUNK_SIZE = 6
BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))


def build_chunk_embeddings() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunk_embedding")
        if cur.fetchone()[0] > 0:
            print("✅ chunk_embedding มีข้อมูลแล้ว (ข้าม)")
            return

        cur.execute(
            """
            SELECT s.id, s.section_id, s.text_pali
            FROM segment s
            WHERE s.text_pali IS NOT NULL
            ORDER BY s.section_id, s.id
            """
        )
        rows = cur.fetchall()

        # group into chunks of CHUNK_SIZE within each section
        chunks = []           # (section_id, start_segment_id, chunk_text)
        buf = []
        cur_section = None
        for seg_pk, section_id, text_pali in rows:
            if section_id != cur_section:
                if buf:
                    chunks.append((cur_section, buf[0][0], " ".join(t for _, t in buf)))
                cur_section = section_id
                buf = []
            buf.append((seg_pk, text_pali or ""))
            if len(buf) == CHUNK_SIZE:
                chunks.append((section_id, buf[0][0], " ".join(t for _, t in buf)))
                buf = []
        if buf:
            chunks.append((cur_section, buf[0][0], " ".join(t for _, t in buf)))

        print(f"🔄 สร้าง chunk embeddings: {len(chunks):,} chunks")
        for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="🧠 chunk embeddings"):
            batch = chunks[i:i + BATCH_SIZE]
            embs = generate_embeddings_batch([c[2] for c in batch], batch_size=BATCH_SIZE)
            for (section_id, start_seg, _), emb in zip(batch, embs):
                cur.execute(
                    "INSERT INTO chunk_embedding (section_id, start_segment_id, embedding) "
                    "VALUES (%s, %s, %s)",
                    (section_id, start_seg, emb),
                )
            conn.commit()
        print(f"✅ chunk embeddings เสร็จ: {len(chunks):,}")

    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)


def build_sutta_embeddings() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sutta_embedding")
        if cur.fetchone()[0] > 0:
            print("✅ sutta_embedding มีข้อมูลแล้ว (ข้าม)")
            return

        print("🔄 สร้าง sutta embeddings (AVG ของ segment embeddings) ...")
        cur.execute(
            """
            INSERT INTO sutta_embedding (section_id, embedding)
            SELECT section_id, AVG(embedding)
            FROM segment
            WHERE embedding IS NOT NULL
            GROUP BY section_id
            """
        )
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM sutta_embedding")
        print(f"✅ sutta embeddings เสร็จ: {cur.fetchone()[0]:,} sections")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)


if __name__ == "__main__":
    build_chunk_embeddings()
    build_sutta_embeddings()
