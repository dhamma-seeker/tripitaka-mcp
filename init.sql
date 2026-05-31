-- =============================================================================
-- Tripitaka MCP Server — Database Initialization
-- =============================================================================
-- ไฟล์นี้จะถูกรันอัตโนมัติเมื่อ PostgreSQL container เริ่มต้นครั้งแรก

-- เปิดใช้งาน pgvector extension สำหรับ vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- เปิดใช้งาน pg_trgm สำหรับ fuzzy text search (trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- NOTE: unaccent extension + f_unaccent() wrapper + functional GIN indexes
-- (diacritic-insensitive search) ตั้งค่าใน scripts/setup_unaccent.sql ซึ่ง
-- deploy.sh รันหลัง restore data (ต้องมีข้อมูลก่อนจึงสร้าง functional index ได้
-- + มี GRANT EXECUTE ให้ readonly role). ไม่ทำซ้ำที่นี่.
