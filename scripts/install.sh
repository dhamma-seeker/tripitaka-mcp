#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — One-shot self-host installer
# =============================================================================
# สำหรับผู้ใช้ที่ไม่ใช่สาย dev อยากลง MCP ในเครื่องตัวเองภายในไม่กี่นาที
#
# สิ่งที่สคริปต์นี้ทำ:
#   1. ตรวจว่ามี docker + docker compose
#   2. สร้าง .env ใหม่ด้วย password สุ่ม (ถ้ายังไม่มี)
#   3. ดาวน์โหลด database dump (ถ้ามี URL) หรือบอกวิธีโหลดข้อมูลเอง
#   4. boot DB + restore dump
#   5. ตั้ง readonly role + ใส่ password สุ่ม
#   6. พิมพ์ config สำหรับ Claude Desktop ให้ copy ใช้ได้เลย
#
# Usage:
#   ./scripts/install.sh                 # interactive
#   ./scripts/install.sh --dump PATH     # ใช้ dump ที่มีอยู่แล้ว
#   ./scripts/install.sh --no-dump       # ข้าม restore (โหลดข้อมูลเองทีหลัง)

set -euo pipefail

# --- paths -------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# --- colors ------------------------------------------------------------------
if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
    C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
    C_RESET=""; C_BOLD=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""
fi

log()  { echo "${C_BLUE}==>${C_RESET} $*"; }
ok()   { echo "${C_GREEN}✓${C_RESET} $*"; }
warn() { echo "${C_YELLOW}⚠${C_RESET}  $*"; }
die()  { echo "${C_RED}✗${C_RESET} $*" >&2; exit 1; }

# --- parse args --------------------------------------------------------------
DUMP_PATH=""
SKIP_DUMP=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dump) DUMP_PATH="${2:-}"; shift 2 ;;
        --no-dump) SKIP_DUMP=1; shift ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown arg: $1" ;;
    esac
done

echo
echo "${C_BOLD}🛕 Tripitaka MCP — self-host installer${C_RESET}"
echo "  เผยแผ่เป็นธรรมทาน (Dhamma Dāna) · ห้ามใช้เชิงพาณิชย์"
echo

# --- 1. preflight ------------------------------------------------------------
log "ตรวจ prerequisites..."
command -v docker >/dev/null 2>&1 || die "docker ไม่พบ — ติดตั้งจาก https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || die "docker compose ไม่พบ (plugin v2) — อัปเดต Docker Desktop หรือติดตั้ง compose plugin"
command -v openssl >/dev/null 2>&1 || die "openssl ไม่พบ (ใช้สร้าง password สุ่ม)"
docker info >/dev/null 2>&1 || die "docker daemon ไม่ทำงาน — เปิด Docker Desktop ก่อน"
ok "docker + compose + openssl พร้อม"

# --- 2. .env -----------------------------------------------------------------
if [[ -f .env ]]; then
    warn ".env มีอยู่แล้ว — จะไม่ overwrite"
    # shellcheck disable=SC1091
    set -a; source .env; set +a
else
    log "สร้าง .env ด้วย password สุ่ม..."
    [[ -f .env.example ]] || die ".env.example หาย — clone repo ใหม่"
    POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)"
    TRIPITAKA_RO_PASSWORD="$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)"
    # substitute placeholders
    sed \
        -e "s|CHANGE_ME_GENERATE_RANDOM_PASSWORD|${POSTGRES_PASSWORD}|g" \
        -e "s|CHANGE_ME_RO_PASSWORD|${TRIPITAKA_RO_PASSWORD}|g" \
        .env.example > .env
    chmod 600 .env
    ok ".env ถูกสร้าง (chmod 600) — เก็บให้ดี ห้าม commit"
fi

# --- 3. dump -----------------------------------------------------------------
if [[ ${SKIP_DUMP} -eq 0 && -z "${DUMP_PATH}" ]]; then
    for candidate in tripitaka_production_data.dump ./data/tripitaka.dump; do
        if [[ -f "${candidate}" ]]; then
            DUMP_PATH="${candidate}"
            log "พบ dump ที่ ${DUMP_PATH} — จะใช้ restore"
            break
        fi
    done
fi

# --- 4. boot DB --------------------------------------------------------------
log "เริ่ม PostgreSQL..."
docker compose up db -d
# รอให้ DB ready
for i in {1..30}; do
    if docker exec tripitaka-db pg_isready -U "${POSTGRES_USER:-admin}" -d "${POSTGRES_DB:-tripitaka_db}" >/dev/null 2>&1; then
        ok "DB พร้อม"
        break
    fi
    sleep 2
    [[ $i -eq 30 ]] && die "DB ไม่ response ใน 60 วินาที — ดู logs: docker compose logs db"
done

# --- 5. restore dump ---------------------------------------------------------
if [[ -n "${DUMP_PATH}" ]]; then
    [[ -f "${DUMP_PATH}" ]] || die "ไฟล์ dump ไม่พบ: ${DUMP_PATH}"
    log "Restore จาก ${DUMP_PATH} (อาจใช้เวลาหลายนาที)..."
    docker exec -i tripitaka-db pg_restore -U "${POSTGRES_USER:-admin}" -d "${POSTGRES_DB:-tripitaka_db}" --no-owner --no-acl < "${DUMP_PATH}" \
        || warn "pg_restore แจ้ง warnings บ้าง (ปกติสำหรับ extension/owner) — ตรวจข้อมูลด้านล่าง"
    COUNT=$(docker exec tripitaka-db psql -U "${POSTGRES_USER:-admin}" -d "${POSTGRES_DB:-tripitaka_db}" -Atc "SELECT COUNT(*) FROM segment" 2>/dev/null || echo "0")
    if [[ "${COUNT}" -gt 0 ]]; then
        ok "restore สำเร็จ — ${COUNT} segments"
    else
        warn "restore จบแต่ตาราง segment ว่าง — ตรวจ dump file"
    fi
elif [[ ${SKIP_DUMP} -eq 1 ]]; then
    warn "ข้าม restore — ต้องโหลดข้อมูลเอง:"
    echo "    python scripts/seed_metadata.py"
    echo "    python scripts/data_loader.py"
    echo "    python scripts/load_thai_cc0.py"
    echo "    python scripts/load_dictionary.py"
    echo "    python scripts/generate_embeddings.py"
else
    warn "ไม่พบไฟล์ dump — จะข้าม restore (รัน scripts โหลดเอง หรือใช้ --dump PATH)"
fi

# --- 6. readonly role --------------------------------------------------------
log "ตั้งค่า readonly user สำหรับ MCP runtime..."
docker exec -i tripitaka-db psql -U "${POSTGRES_USER:-admin}" -d "${POSTGRES_DB:-tripitaka_db}" < scripts/setup_readonly_user.sql >/dev/null
docker exec tripitaka-db psql -U "${POSTGRES_USER:-admin}" -d "${POSTGRES_DB:-tripitaka_db}" \
    -c "ALTER ROLE tripitaka_ro PASSWORD '${TRIPITAKA_RO_PASSWORD}'" >/dev/null
ok "tripitaka_ro พร้อมใช้ (SELECT-only, statement_timeout=10s)"

# --- 7. print config ---------------------------------------------------------
echo
echo "${C_BOLD}🎉 ติดตั้งเสร็จแล้ว${C_RESET}"
echo
echo "${C_BOLD}Claude Desktop config${C_RESET} — copy ไปวางใน claude_desktop_config.json:"
cat <<EOF

{
  "mcpServers": {
    "tripitaka": {
      "command": "$(command -v python3 || echo python)",
      "args": ["${PROJECT_ROOT}/main.py"],
      "env": {
        "DATABASE_URL": "postgresql://tripitaka_ro:${TRIPITAKA_RO_PASSWORD}@localhost:5432/${POSTGRES_DB:-tripitaka_db}",
        "TRIPITAKA_SKIP_MIGRATIONS": "true"
      }
    }
  }
}

EOF
echo "${C_BOLD}ถัดไป:${C_RESET}"
echo "  1. ติดตั้ง Python deps: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
echo "  2. ทดสอบ: python main.py"
echo "  3. restart Claude Desktop"
echo
echo "สาธุ 🙏"
