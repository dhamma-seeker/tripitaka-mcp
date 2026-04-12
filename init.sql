-- =============================================================================
-- Tripitaka MCP Server — Database Initialization
-- =============================================================================
-- ไฟล์นี้จะถูกรันอัตโนมัติเมื่อ PostgreSQL container เริ่มต้นครั้งแรก

-- เปิดใช้งาน pgvector extension สำหรับ vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- เปิดใช้งาน pg_trgm สำหรับ fuzzy text search (trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
