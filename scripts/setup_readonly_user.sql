-- =============================================================================
-- Tripitaka MCP — Create read-only DB role for MCP server runtime
-- =============================================================================
-- รันครั้งเดียวหลัง migration/load ข้อมูลเสร็จ เพื่อให้ MCP server runtime
-- connect ด้วย role ที่ไม่มีสิทธิ์เขียน — ป้องกันความเสียหายถ้าถูก exploit
--
-- Usage (inside db container หรือผ่าน psql):
--   docker exec -i tripitaka-db psql -U admin -d tripitaka_db \
--       < scripts/setup_readonly_user.sql
--
-- หรือเปลี่ยน password:
--   docker exec -i tripitaka-db psql -U admin -d tripitaka_db \
--       -v ro_password="'YOUR_STRONG_PASSWORD'" \
--       -f /scripts/setup_readonly_user.sql
--
-- Idempotent — รันซ้ำได้

-- -----------------------------------------------------------------------------
-- 1. สร้าง role สำหรับ runtime (READ ONLY)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tripitaka_ro') THEN
        -- หมายเหตุ: password จะต้องถูก set ผ่าน ALTER ROLE แยก
        -- เพื่อให้ใช้ password ที่แข็งแรงจาก secrets manager
        CREATE ROLE tripitaka_ro LOGIN PASSWORD 'changeme_set_via_alter_role';
        RAISE NOTICE 'Created role tripitaka_ro with placeholder password';
    ELSE
        RAISE NOTICE 'Role tripitaka_ro already exists';
    END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 2. Grant SELECT บนทุกตารางที่มีอยู่ + ที่จะสร้างในอนาคต
-- -----------------------------------------------------------------------------
GRANT CONNECT ON DATABASE tripitaka_db TO tripitaka_ro;
GRANT USAGE ON SCHEMA public TO tripitaka_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tripitaka_ro;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tripitaka_ro;

-- ตาราง/sequence ที่ถูกสร้างในอนาคต (จาก role admin) ให้ ro เห็นอัตโนมัติ
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO tripitaka_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO tripitaka_ro;

-- -----------------------------------------------------------------------------
-- 3. ตั้ง timeout ระดับ role
--    statement_timeout: abort query ที่รันนานเกิน 10 วินาที (ป้องกัน DoS)
--    idle_in_transaction_session_timeout: ตัด transaction ที่ค้าง 60 วินาที
-- -----------------------------------------------------------------------------
ALTER ROLE tripitaka_ro SET statement_timeout = '10s';
ALTER ROLE tripitaka_ro SET idle_in_transaction_session_timeout = '60s';
ALTER ROLE tripitaka_ro SET lock_timeout = '5s';

-- -----------------------------------------------------------------------------
-- 4. Revoke สิทธิ์ที่อาจรั่วจาก default
-- -----------------------------------------------------------------------------
REVOKE CREATE ON SCHEMA public FROM tripitaka_ro;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO tripitaka_ro;

-- -----------------------------------------------------------------------------
-- ⚠️ หลังจากรันสคริปต์นี้ ให้ตั้ง password ที่แข็งแรงด้วยคำสั่ง:
--    ALTER ROLE tripitaka_ro PASSWORD 'NEW_STRONG_PASSWORD';
-- แล้วอัปเดต DATABASE_URL ใน .env ของ MCP server เป็น:
--    postgresql://tripitaka_ro:NEW_STRONG_PASSWORD@db:5432/tripitaka_db
-- -----------------------------------------------------------------------------
