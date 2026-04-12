"""
Tripitaka MCP Server — Database Schema

โครงสร้างตาราง:
    pitaka → nikaya → book → section → segment

- pitaka:  ปิฎก 3 (วินัย, สุตตันตะ, อภิธรรม)
- nikaya:  นิกาย/หมวด
- book:    เล่ม/คัมภีร์
- section: สูตร/กัณฑ์
- segment: ข้อความจริง (ระดับย่อหน้า) — หน่วยที่ทำ embedding
"""

import os
from db.connection import get_connection, release_connection

EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))


def create_tables() -> None:
    """สร้างตารางทั้งหมดใน database

    เรียกฟังก์ชันนี้ตอน server เริ่มต้น หรือรัน script แยก
    ตารางจะถูกสร้างเฉพาะเมื่อยังไม่มี (IF NOT EXISTS)
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ------------------------------------------------------------------
        # ปิฎก (Pitaka) — ระดับสูงสุด: วินัย, สุตตันตะ, อภิธรรม
        # ------------------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pitaka (
                id          SERIAL PRIMARY KEY,
                code        VARCHAR(20) UNIQUE NOT NULL,    -- e.g. "vinaya", "sutta", "abhidhamma"
                name_pali   VARCHAR(100) NOT NULL,
                name_thai   VARCHAR(100) NOT NULL,
                name_english VARCHAR(100) NOT NULL,
                sort_order  INTEGER NOT NULL DEFAULT 0
            );
        """)

        # ------------------------------------------------------------------
        # นิกาย (Nikaya) — หมวดย่อยในแต่ละปิฎก
        # ------------------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nikaya (
                id          SERIAL PRIMARY KEY,
                pitaka_id   INTEGER NOT NULL REFERENCES pitaka(id) ON DELETE CASCADE,
                code        VARCHAR(20) UNIQUE NOT NULL,    -- e.g. "dn", "mn", "sn", "an", "kn"
                name_pali   VARCHAR(200) NOT NULL,
                name_thai   VARCHAR(200) NOT NULL,
                name_english VARCHAR(200) NOT NULL,
                sort_order  INTEGER NOT NULL DEFAULT 0
            );
        """)

        # ------------------------------------------------------------------
        # เล่ม/คัมภีร์ (Book)
        # ------------------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS book (
                id              SERIAL PRIMARY KEY,
                nikaya_id       INTEGER NOT NULL REFERENCES nikaya(id) ON DELETE CASCADE,
                code            VARCHAR(50) UNIQUE NOT NULL,
                name_pali       VARCHAR(300),
                name_thai       VARCHAR(300),
                name_english    VARCHAR(300),
                volume_number   INTEGER,
                sort_order      INTEGER NOT NULL DEFAULT 0
            );
        """)

        # ------------------------------------------------------------------
        # สูตร/กัณฑ์ (Section) — หน่วยเนื้อหาที่มีความหมาย
        # ------------------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS section (
                id              SERIAL PRIMARY KEY,
                book_id         INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
                sutta_id        VARCHAR(50) UNIQUE NOT NULL,    -- e.g. "mn1", "dn22", "sn56.11"
                title_pali      VARCHAR(500),
                title_thai      VARCHAR(500),
                title_english   VARCHAR(500),
                sort_order      INTEGER NOT NULL DEFAULT 0
            );
        """)

        # ------------------------------------------------------------------
        # ข้อความ (Segment) — ระดับย่อหน้า/ประโยค + vector embedding
        # ------------------------------------------------------------------
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS segment (
                id              SERIAL PRIMARY KEY,
                section_id      INTEGER NOT NULL REFERENCES section(id) ON DELETE CASCADE,
                segment_id      VARCHAR(50) UNIQUE NOT NULL,    -- e.g. "mn1:1.1"
                text_pali       TEXT,
                text_thai       TEXT,
                text_english    TEXT,
                embedding       vector({EMBEDDING_DIMENSIONS}), -- pgvector column
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # ------------------------------------------------------------------
        # Indexes สำหรับ performance
        # ------------------------------------------------------------------

        # Full-text / trigram search indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_segment_text_pali_trgm
            ON segment USING gin (text_pali gin_trgm_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_segment_text_thai_trgm
            ON segment USING gin (text_thai gin_trgm_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_segment_text_english_trgm
            ON segment USING gin (text_english gin_trgm_ops);
        """)

        # Foreign key indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_segment_section_id ON segment(section_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_section_book_id ON section(book_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_book_nikaya_id ON book(nikaya_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nikaya_pitaka_id ON nikaya(pitaka_id);")

        # Section lookup by sutta_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_section_sutta_id ON section(sutta_id);")

        # Vector similarity search index (HNSW — สร้างหลังจาก load ข้อมูลแล้ว)
        # จะสร้างใน generate_embeddings.py เพราะสร้าง index กับตารางว่าง ไม่มีประโยชน์
        # CREATE INDEX idx_segment_embedding ON segment USING hnsw (embedding vector_cosine_ops);

        # ------------------------------------------------------------------
        # คำแปลเพิ่มเติม (Translation) — รองรับหลายฉบับต่อ segment
        # ใช้สำหรับเพิ่มคำแปลจากแหล่งต่างๆ เช่น MCU, ฉบับหลวง, dhiranandi
        # ------------------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS translation (
                id              SERIAL PRIMARY KEY,
                segment_id      INTEGER NOT NULL REFERENCES segment(id) ON DELETE CASCADE,
                language        VARCHAR(10) NOT NULL,   -- e.g. "th", "en"
                edition         VARCHAR(50) NOT NULL,   -- e.g. "dhiranandi", "mbu", "royal"
                translator      VARCHAR(100),           -- ชื่อผู้แปล (optional)
                text            TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (segment_id, language, edition)
            );
        """)

        # Indexes สำหรับ translation table
        cur.execute("CREATE INDEX IF NOT EXISTS idx_translation_segment_id ON translation(segment_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_translation_lang_edition ON translation(language, edition);")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_translation_text_trgm
            ON translation USING gin (text gin_trgm_ops);
        """)

        conn.commit()
        print("✅ สร้างตารางทั้งหมดเรียบร้อย")

    except Exception as e:
        conn.rollback()
        print(f"❌ เกิดข้อผิดพลาดในการสร้างตาราง: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


def drop_tables() -> None:
    """ลบตารางทั้งหมด — ใช้สำหรับ development/reset เท่านั้น!"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            DROP TABLE IF EXISTS segment CASCADE;
            DROP TABLE IF EXISTS section CASCADE;
            DROP TABLE IF EXISTS book CASCADE;
            DROP TABLE IF EXISTS nikaya CASCADE;
            DROP TABLE IF EXISTS pitaka CASCADE;
        """)
        conn.commit()
        print("🗑️ ลบตารางทั้งหมดเรียบร้อย")
    except Exception as e:
        conn.rollback()
        print(f"❌ เกิดข้อผิดพลาดในการลบตาราง: {e}")
        raise
    finally:
        cur.close()
        release_connection(conn)


if __name__ == "__main__":
    print("🔧 กำลังสร้างตาราง...")
    create_tables()
