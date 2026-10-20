#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — Rollback production ด้วยการสลับ image (ไม่ build ใหม่)
# =============================================================================
# รันบน droplet (cwd: /opt/tripitaka) หลัง deploy แล้ว prod พัง
#
# ทำอะไรบ้าง:
# 1. อ่านเวอร์ชันที่รันอยู่จาก .env (APP_VERSION) และประวัติจาก .deploy-history
# 2. หาเวอร์ชันก่อนหน้าที่ image ยังอยู่ในเครื่องครบทุก repo
# 3. pin เวอร์ชันนั้นลง .env + ย้าย tag :latest + recreate service ที่ใช้ image
# 4. ตรวจ health
#
# ใช้เวลาเท่ากับ container restart (ราว 10-30 วินาที) ไม่ใช่หลายนาทีแบบ rebuild
#
# Usage:
#   ./scripts/rollback.sh                 # ย้อนไปเวอร์ชันก่อนหน้า
#   ./scripts/rollback.sh <version>       # ย้อนไปเวอร์ชันที่ระบุ (git short sha)
#   ./scripts/rollback.sh --list          # ดูเวอร์ชันที่ย้อนได้
#   ./scripts/rollback.sh --dry-run       # บอกว่าจะทำอะไร ไม่แตะ container
#
# ⚠️ rollback นี้ย้อน "โค้ดใน image" เท่านั้น
#    ไฟล์ที่ compose bind mount (infra/Caddyfile, site/, topics/, init.sql,
#    scripts/) ยังมาจาก checkout ปัจจุบัน ถ้าของที่พังอยู่ในไฟล์พวกนั้น
#    ต้อง git revert บน main แล้ว deploy ใหม่ สคริปต์นี้ช่วยไม่ได้

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

# --- config ------------------------------------------------------------------
COMPOSE_FILE="${TRIPITAKA_COMPOSE_FILE:-docker-compose.prod.yml}"
HISTORY_FILE="${PROJECT_ROOT}/.deploy-history"
# repos ที่ deploy.sh build เอง — ต้องมี tag ของเวอร์ชันเป้าหมายครบทุกตัวถึงจะย้อนได้
IMAGE_REPOS=(tripitaka-mcp tripitaka-caddy)
# service ที่ใช้ image เหล่านั้น (db ใช้ image จาก registry — ไม่แตะ ข้อมูลอยู่ใน volume)
VERSIONED_SERVICES=(mcp-server mcp-server-http reader caddy)

# --- helpers -----------------------------------------------------------------
# อ่าน key เดียวจาก .env โดยไม่ source ทั้งไฟล์ (ค่าที่มีช่องว่างจะพัง)
load_env() {
    local key="$1" raw
    raw=$(grep -E "^${key}=" .env 2>/dev/null | head -1 | cut -d= -f2-) || true
    if [[ "${raw}" == \"*\" ]] || [[ "${raw}" == \'*\' ]]; then
        raw="${raw:1:${#raw}-2}"
    fi
    printf '%s' "${raw}"
}

# เขียน key=value ลง .env โดยคง inode + chmod 600 เดิม (เหมือน deploy.sh)
upsert_env() {
    local key="$1" value="$2" tmp
    tmp="$(mktemp "${PROJECT_ROOT}/.env.tmp.XXXXXX")"
    chmod 600 "${tmp}"
    awk -F= -v k="${key}" -v v="${value}" '
        $1 == k { if (!done) { print k "=" v; done = 1 } next }
        { print }
        END { if (!done) print k "=" v }
    ' .env > "${tmp}"
    cat "${tmp}" > .env
    rm -f "${tmp}"
}

record_deploy() {
    local version="$1" action="$2" branch
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    printf '%s\t%s\t%s\t%s\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${version}" "${branch}" "${action}" >> "${HISTORY_FILE}"
}

# image ของเวอร์ชันนี้อยู่ครบทุก repo ไหม
version_is_available() {
    local version="$1" repo
    for repo in "${IMAGE_REPOS[@]}"; do
        docker image inspect "${repo}:${version}" >/dev/null 2>&1 || return 1
    done
    return 0
}

# เวอร์ชันใน .deploy-history เรียงใหม่→เก่า ตัดซ้ำ
history_versions() {
    awk -F'\t' 'NF >= 2 { print $2 }' "${HISTORY_FILE}" 2>/dev/null \
        | awk '{ line[NR] = $0 } END { for (i = NR; i >= 1; i--) print line[i] }' \
        | awk 'NF && !seen[$0]++'
}

# --- parse args ----------------------------------------------------------------
TARGET=""
LIST_ONLY=0
DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --list) LIST_ONLY=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) die "unknown arg: $1" ;;
        *) [[ -n "${TARGET}" ]] && die "ระบุเวอร์ชันได้ตัวเดียว"; TARGET="$1"; shift ;;
    esac
done

echo
echo "${C_BOLD}⏮  Tripitaka MCP — rollback (สลับ image ไม่ build ใหม่)${C_RESET}"
echo

# --- 1. sanity ------------------------------------------------------------------
[[ -f "${COMPOSE_FILE}" ]] || die "ไม่พบ ${COMPOSE_FILE} — cd เข้า project ก่อน"
command -v docker >/dev/null 2>&1 || die "docker ไม่พบ"
docker info >/dev/null 2>&1 || die "docker daemon ไม่ทำงาน"
[[ -f .env ]] || die "ไม่พบ .env — rollback ต้องใช้ .env เดิมของ prod"

CURRENT="$(load_env APP_VERSION)"
if [[ -z "${CURRENT}" ]]; then
    warn ".env ไม่มี APP_VERSION — deploy ครั้งล่าสุดยังเป็นแบบเก่า (ทับ :latest ทุก build)"
    CURRENT="latest"
fi

# --- 2. --list -------------------------------------------------------------------
if [[ ${LIST_ONLY} -eq 1 ]]; then
    if [[ ! -s "${HISTORY_FILE}" ]]; then
        warn "ยังไม่มี ${HISTORY_FILE} — ยังไม่เคย deploy ด้วย deploy.sh รุ่นที่ tag เวอร์ชัน"
    else
        echo "  เวอร์ชันใน .deploy-history (ใหม่ → เก่า):"
        echo
        while read -r v; do
            mark=""
            [[ "${v}" == "${CURRENT}" ]] && mark="  ← รันอยู่ตอนนี้"
            if version_is_available "${v}"; then
                echo "    ${C_GREEN}✓${C_RESET} ${v}  (image ครบ ย้อนได้)${mark}"
            else
                echo "    ${C_RED}✗${C_RESET} ${v}  (image ถูกลบไปแล้ว ย้อนไม่ได้)${mark}"
            fi
        done < <(history_versions)
    fi
    echo
    echo "  deploy ล่าสุด 10 บรรทัด:"
    tail -10 "${HISTORY_FILE}" 2>/dev/null | sed 's/^/    /' || true
    exit 0
fi

# --- 3. หาเวอร์ชันเป้าหมาย ---------------------------------------------------------
log "เวอร์ชันที่รันอยู่: ${CURRENT}"

if [[ -n "${TARGET}" ]]; then
    [[ "${TARGET}" == "${CURRENT}" ]] && die "${TARGET} คือเวอร์ชันที่รันอยู่แล้ว ไม่มีอะไรต้องย้อน"
    version_is_available "${TARGET}" || die "$(cat <<MSG
ไม่มี image ของ ${TARGET} ครบในเครื่องนี้
   ตรวจด้วย: docker image ls tripitaka-mcp
   ถ้า image ถูกลบไปแล้ว ย้อนด้วยการสลับ image ไม่ได้ ต้อง git revert + rebuild
MSG
)"
else
    if [[ ! -s "${HISTORY_FILE}" ]]; then
        die "$(cat <<MSG
ไม่มี ${HISTORY_FILE} — ไม่รู้ว่าเวอร์ชันก่อนหน้าคืออะไร
   เกิดกับ droplet ที่ยังไม่เคย deploy ด้วย deploy.sh รุ่นที่ tag เวอร์ชัน
   รอบนี้ต้อง rollback แบบเดิม: git revert <commit> แล้ว ./scripts/deploy.sh
   deploy ครั้งถัดไปจะเริ่มสะสมประวัติให้เอง แล้วรอบหน้าถึงจะย้อนด้วยสคริปต์นี้ได้
MSG
)"
    fi
    while read -r v; do
        [[ "${v}" == "${CURRENT}" ]] && continue
        if version_is_available "${v}"; then
            TARGET="${v}"
            break
        fi
        warn "ข้าม ${v} — image ถูกลบไปแล้ว"
    done < <(history_versions)

    [[ -n "${TARGET}" ]] || die "$(cat <<MSG
ไม่มีเวอร์ชันก่อนหน้าที่ย้อนได้ (image ที่เก็บไว้หมดแล้ว หรือเพิ่ง deploy ครั้งแรก)
   ดูรายการ: ./scripts/rollback.sh --list
   รอบนี้ต้อง rollback แบบเดิม: git revert <commit> แล้ว ./scripts/deploy.sh
MSG
)"
fi

ok "เป้าหมาย: ${CURRENT} → ${TARGET}"

# --- 4. เตือนเรื่อง bind mount ------------------------------------------------------
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [[ "${HEAD_SHA}" != "${TARGET}" ]]; then
    echo
    warn "checkout อยู่ที่ ${HEAD_SHA} แต่จะรัน image ของ ${TARGET}"
    echo "   ไฟล์ที่ bind mount ยังเป็นของ ${HEAD_SHA}: infra/Caddyfile, site/, topics/"
    echo "   rollback นี้ย้อนเฉพาะโค้ดใน image ถ้าของที่พังอยู่ใน 3 path นั้น ต้อง git revert แทน"
    echo
fi

if [[ ${DRY_RUN} -eq 1 ]]; then
    echo "${C_BOLD}--dry-run — จะทำแบบนี้ (ยังไม่ทำ):${C_RESET}"
    echo "  1. เขียน APP_VERSION=${TARGET} ลง .env"
    echo "  2. ย้าย tag latest:"
    for repo in "${IMAGE_REPOS[@]}"; do
        echo "       docker tag ${repo}:${TARGET} ${repo}:latest"
    done
    echo "  3. docker compose -f ${COMPOSE_FILE} up -d --no-build ${VERSIONED_SERVICES[*]}"
    echo "  4. บันทึก rollback ลง .deploy-history"
    echo
    exit 0
fi

# --- 5. สลับ image -------------------------------------------------------------
log "pin APP_VERSION=${TARGET} ลง .env..."
upsert_env APP_VERSION "${TARGET}"
ok ".env pin แล้ว (compose อ่านเอง → up -d เปล่าๆ ก็ได้เวอร์ชันนี้)"

log "ย้าย tag latest มาที่ ${TARGET}..."
for repo in "${IMAGE_REPOS[@]}"; do
    docker tag "${repo}:${TARGET}" "${repo}:latest"
    ok "${repo}:latest → ${TARGET}"
done

log "recreate service: ${VERSIONED_SERVICES[*]}"
warn "caddy ถือ port 80/443 — ช่วงนี้ทุกบริการขาดราว 10-15 วินาที"
# --no-build = ถ้า image หาย ให้ fail ไปเลย ดีกว่าแอบ build ใหม่เงียบๆ
docker compose -f "${COMPOSE_FILE}" up -d --no-build "${VERSIONED_SERVICES[@]}"

record_deploy "${TARGET}" "rollback-from-${CURRENT}"
ok "บันทึกลง .deploy-history แล้ว"

# --- 6. verify -----------------------------------------------------------------
log "ตรวจว่า container รัน image ที่ถูกต้อง..."
for svc in "${VERSIONED_SERVICES[@]}"; do
    cid="$(docker compose -f "${COMPOSE_FILE}" ps -q "${svc}" 2>/dev/null || true)"
    if [[ -z "${cid}" ]]; then
        warn "${svc}: ไม่มี container (ข้าม)"
        continue
    fi
    running="$(docker inspect --format '{{.Config.Image}}' "${cid}" 2>/dev/null || echo "?")"
    echo "   ${svc}: ${running}"
done

TRIPITAKA_DOMAIN="$(load_env TRIPITAKA_DOMAIN)"
if [[ -n "${TRIPITAKA_DOMAIN}" ]]; then
    log "รอ /health ตอบ ok..."
    healthy=0
    for i in {1..30}; do
        if curl -fsS --max-time 10 "https://${TRIPITAKA_DOMAIN}/health" 2>/dev/null | grep -q ok; then
            ok "https://${TRIPITAKA_DOMAIN}/health → ok"
            healthy=1
            break
        fi
        sleep 5
    done
    [[ ${healthy} -eq 1 ]] || warn "health ยังไม่ผ่านใน 2.5 นาที — ดู docker compose -f ${COMPOSE_FILE} logs"
else
    warn "ไม่มี TRIPITAKA_DOMAIN ใน .env — ข้ามการตรวจ /health จากภายนอก"
fi

echo
echo "${C_BOLD}⏮  Rollback เสร็จ: ${CURRENT} → ${TARGET}${C_RESET}"
echo
echo "  ตรวจต่อ (Step 4 ใน CLAUDE.md):"
echo "    MCP_URL=https://${TRIPITAKA_DOMAIN:-example.org}/mcp .venv/bin/python scripts/test_full_sutta.py"
echo "    for u in / /topics/ /favicon-128.png /read/mn1; do curl -s -o /dev/null -w \"\$u %{http_code}\\n\" https://${TRIPITAKA_DOMAIN:-example.org}\$u; done"
echo
echo "  กลับไปเวอร์ชันล่าสุด:  ./scripts/rollback.sh ${CURRENT}"
echo "  แก้ที่ต้นเหตุ:          git revert <commit> บน main แล้ว ./scripts/deploy.sh"
echo
