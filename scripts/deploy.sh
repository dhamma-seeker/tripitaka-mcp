#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — Production deploy (บน droplet)
# =============================================================================
# รันบน droplet หลัง cloud-init เสร็จแล้ว (user: deploy, cwd: /opt/tripitaka)
#
# ทำอะไรบ้าง:
# 1. ตรวจว่ารันจาก /opt/tripitaka (ไม่ใช่ laptop)
# 2. สร้าง .env ด้วย password สุ่ม ถ้ายังไม่มี
# 3. prompt ให้ใส่ TRIPITAKA_DOMAIN
# 4. ดาวน์โหลด + restore dump จาก HF (ถ้ายัง)
# 5. ตั้ง readonly user
# 6. build + up -d docker-compose.prod.yml
# 7. รอ healthcheck + ทดสอบ /health จาก external
#
# Usage:
#   ./scripts/deploy.sh [--domain mcp.example.org] [--dump-url URL] [--force-restore]
#
# --force-restore: drop existing segment data and restore from dump
#                  (use when refreshing prod with a new dump from HF)

set -euo pipefail

# --- paths & colors ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

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

# Read a single key from .env without sourcing the whole file (which would
# break on values containing spaces — `TRIPITAKA_DOMAIN=a.com b.com` would
# try to execute `b.com`). Strips matching surrounding quotes.
load_env() {
    local key="$1"
    local raw
    raw=$(grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2-) || true
    # strip matched leading/trailing quote pair
    if [[ "${raw}" == \"*\" ]] || [[ "${raw}" == \'*\' ]]; then
        raw="${raw:1:${#raw}-2}"
    fi
    printf '%s' "${raw}"
}

# --- parse args --------------------------------------------------------------
DOMAIN=""
DUMP_URL=""
FORCE_RESTORE=0
HF_REPO="dhamma-seeker/tripitaka-mcp-dump"
HF_FILE="tripitaka_production_data.dump"
DEFAULT_DUMP_URL="https://huggingface.co/datasets/${HF_REPO}/resolve/main/${HF_FILE}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain) DOMAIN="${2:-}"; shift 2 ;;
        --dump-url) DUMP_URL="${2:-}"; shift 2 ;;
        --force-restore) FORCE_RESTORE=1; shift ;;
        -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown arg: $1" ;;
    esac
done
DUMP_URL="${DUMP_URL:-${DEFAULT_DUMP_URL}}"

echo
echo "${C_BOLD}🚢 Tripitaka MCP — production deploy${C_RESET}"
echo

# --- 1. sanity -------------------------------------------------------------
log "ตรวจ environment..."
[[ "$(id -un)" == "deploy" ]] || warn "รันในฐานะ $(id -un) (แนะนำ deploy user)"
[[ -f docker-compose.prod.yml ]] || die "ไม่พบ docker-compose.prod.yml — cd เข้า project ก่อน"
command -v docker >/dev/null 2>&1 || die "docker ไม่พบ (cloud-init เสร็จแล้วหรือยัง?)"
docker compose version >/dev/null 2>&1 || die "docker compose plugin ไม่พบ"
docker info >/dev/null 2>&1 || die "docker daemon ไม่ทำงาน"
ok "environment พร้อม"

# --- 2. .env ---------------------------------------------------------------
if [[ -f .env ]]; then
    warn ".env มีอยู่แล้ว — จะไม่ overwrite"
    [[ -n "${DOMAIN}" && "${DOMAIN}" != "$(load_env TRIPITAKA_DOMAIN)" ]] && \
        warn "--domain ${DOMAIN} ขัดกับ .env ($(load_env TRIPITAKA_DOMAIN)) — จะใช้ค่าใน .env"
else
    log "สร้าง .env ใหม่..."
    if [[ -z "${DOMAIN}" ]]; then
        read -rp "TRIPITAKA_DOMAIN (เช่น mcp.example.org): " DOMAIN
    fi
    [[ -z "${DOMAIN}" ]] && die "TRIPITAKA_DOMAIN จำเป็น (Caddy ใช้ขอ Let's Encrypt)"

    POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)"
    TRIPITAKA_RO_PASSWORD="$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-32)"

    sed \
        -e "s|CHANGE_ME_GENERATE_RANDOM_PASSWORD|${POSTGRES_PASSWORD}|g" \
        -e "s|CHANGE_ME_RO_PASSWORD|${TRIPITAKA_RO_PASSWORD}|g" \
        -e "s|^TRIPITAKA_DOMAIN=.*|TRIPITAKA_DOMAIN=${DOMAIN}|g" \
        .env.example > .env
    chmod 600 .env
    ok ".env สร้างแล้ว (chmod 600)"
    echo "   DOMAIN:        ${DOMAIN}"
    echo "   RO password:   ${TRIPITAKA_RO_PASSWORD:0:8}... (full อยู่ใน .env)"
fi

# load specific keys we need — DON'T source the whole .env (handles
# space-separated values like TRIPITAKA_DOMAIN="a.com b.com")
POSTGRES_USER="$(load_env POSTGRES_USER)"
POSTGRES_DB="$(load_env POSTGRES_DB)"
POSTGRES_PASSWORD="$(load_env POSTGRES_PASSWORD)"
TRIPITAKA_DOMAIN="$(load_env TRIPITAKA_DOMAIN)"
TRIPITAKA_RO_PASSWORD="$(load_env TRIPITAKA_RO_PASSWORD)"
[[ -n "${TRIPITAKA_DOMAIN}" ]] || die "TRIPITAKA_DOMAIN ว่าง — แก้ .env"
[[ -n "${POSTGRES_USER}" ]] || die "POSTGRES_USER ว่าง — แก้ .env"
[[ -n "${POSTGRES_DB}" ]] || die "POSTGRES_DB ว่าง — แก้ .env"

# --- 3. dump ---------------------------------------------------------------
DUMP_PATH=""
for candidate in tripitaka_production_data.dump ./data/tripitaka.dump; do
    if [[ -f "${candidate}" ]]; then
        DUMP_PATH="${candidate}"
        log "พบ dump ที่ ${DUMP_PATH}"
        break
    fi
done
if [[ -z "${DUMP_PATH}" ]]; then
    DUMP_PATH="./tripitaka_production_data.dump"
    log "ดาวน์โหลด dump จาก HF: ${DUMP_URL}"
    curl -fL --progress-bar --retry 3 --retry-delay 5 -o "${DUMP_PATH}.tmp" "${DUMP_URL}" \
        || die "ดาวน์โหลดล้มเหลว"
    mv "${DUMP_PATH}.tmp" "${DUMP_PATH}"
    ok "ดาวน์โหลดสำเร็จ ($(du -h "${DUMP_PATH}" | cut -f1))"
fi

# --- 4. boot DB ก่อน (ต้อง restore + setup_readonly ก่อนเริ่ม mcp-server) ---
log "build + start DB..."
docker compose -f docker-compose.prod.yml up -d --build db

for i in {1..60}; do
    if docker exec tripitaka-db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
        ok "DB พร้อม"; break
    fi
    sleep 2
    [[ $i -eq 60 ]] && die "DB ไม่ response ใน 2 นาที"
done

# --- 5. restore (ข้ามถ้า DB มีข้อมูลอยู่แล้ว, --force-restore เพื่อ drop+reload) ----
EXISTING=$(docker exec tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='segment'" 2>/dev/null || echo "0")

if [[ "${EXISTING}" -gt 0 && "${FORCE_RESTORE}" -eq 0 ]]; then
    COUNT=$(docker exec tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT COUNT(*) FROM segment" 2>/dev/null || echo "0")
    warn "DB มี segment อยู่แล้ว ${COUNT} rows — ข้าม restore (ใช้ --force-restore เพื่อ drop+reload)"
else
    if [[ "${EXISTING}" -gt 0 ]]; then
        OLD_COUNT=$(docker exec tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT COUNT(*) FROM segment" 2>/dev/null || echo "0")
        warn "--force-restore: DB มี ${OLD_COUNT} segments — drop schema แล้ว reload"
        docker exec -i tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
            -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pg_trgm;" >/dev/null
        ok "schema ดรอปและสร้างใหม่ + extensions พร้อม"
    fi
    log "Restore จาก ${DUMP_PATH}..."
    docker exec -i tripitaka-db pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --no-acl < "${DUMP_PATH}" \
        || warn "pg_restore มี warnings (ปกติ) — ตรวจ count ด้านล่าง"
    COUNT=$(docker exec tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT COUNT(*) FROM segment")
    [[ "${COUNT}" -gt 0 ]] || die "restore เสร็จแต่ segment ว่าง — dump file อาจเสีย"
    ok "restore: ${COUNT} segments"
fi

# --- 6. readonly user ------------------------------------------------------
log "ตั้งค่า readonly user..."
docker exec -i tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < scripts/setup_readonly_user.sql >/dev/null
docker exec tripitaka-db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    -c "ALTER ROLE tripitaka_ro PASSWORD '${TRIPITAKA_RO_PASSWORD}'" >/dev/null
ok "tripitaka_ro พร้อม"

# --- 7. start full stack ---------------------------------------------------
log "start mcp-server + caddy..."
docker compose -f docker-compose.prod.yml up -d --build

# --- 8. health check -------------------------------------------------------
log "รอ mcp-server healthy (อาจใช้เวลาสักครู่ embedding model โหลด)..."
for i in {1..60}; do
    status=$(docker inspect --format='{{.State.Health.Status}}' tripitaka-mcp-server 2>/dev/null || echo "starting")
    [[ "${status}" == "healthy" ]] && { ok "mcp-server healthy"; break; }
    sleep 5
    [[ $i -eq 60 ]] && warn "mcp-server ยังไม่ healthy ใน 5 นาที — ดู docker logs tripitaka-mcp-server"
done

log "รอ Caddy ขอ Let's Encrypt cert..."
sleep 10
if curl -fsS --max-time 30 "https://${TRIPITAKA_DOMAIN}/health" 2>/dev/null | grep -q ok; then
    ok "https://${TRIPITAKA_DOMAIN}/health → ok"
else
    warn "health check จาก external ยังไม่ผ่าน"
    echo "   ตรวจ: DNS ชี้มา droplet นี้แล้วหรือยัง? (dig ${TRIPITAKA_DOMAIN})"
    echo "   ตรวจ: docker logs tripitaka-caddy  |  docker logs tripitaka-mcp-server"
fi

# --- 9. summary ------------------------------------------------------------
echo
echo "${C_BOLD}🎉 Deploy เสร็จแล้ว${C_RESET}"
echo
echo "  URL:       https://${TRIPITAKA_DOMAIN}"
echo "  Health:    https://${TRIPITAKA_DOMAIN}/health"
echo "  Logs:      docker compose -f docker-compose.prod.yml logs -f"
echo "  Restart:   docker compose -f docker-compose.prod.yml restart"
echo "  Update:    git pull && ./scripts/deploy.sh"
echo
echo "สาธุ 🙏"
