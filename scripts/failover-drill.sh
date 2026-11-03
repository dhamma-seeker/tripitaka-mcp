#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — สร้างเครื่องสำรองบน DigitalOcean (ซ้อม หรือใช้จริง)
# =============================================================================
# รันได้สองที่:
# - laptop: checkout ที่มี infra/terraform.tfvars + infra/backend.hcl และ export
#   AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY ของ R2 ไว้ · ต้องเปิด VPN เพราะ
#   firewall ของ DO ให้ SSH เฉพาะ ssh_allowed_cidrs
# - GitHub Actions (.github/workflows/ops-*.yml): ค่าทั้งหมดมาจาก TF_VAR_* และ secrets
#
# Terraform state อยู่ใน R2 (infra/backend.hcl) ทั้งสองที่จึงเห็นเครื่องชุดเดียวกัน
#
# ทำอะไรบ้าง:
# 1. เช็คสำเนา .env ด้วย check-env.sh ก่อนสร้างเครื่อง (สำเนาเก่า = หยุดตั้งแต่ยังไม่เสียเงิน)
# 2. terraform apply → droplet ใหม่ที่ผ่าน cloud-init แล้ว
# 3. เช็คสิ่งที่ cloud-init ต้องทำ (docker, aws-cli, /etc/cron.d/tripitaka)
# 4. วาง .env, clone repo, รัน deploy.sh แบบเดียวกับเครื่องจริง
# 5. ทดสอบบนเครื่อง: container healthy, จำนวน segment, /mcp ตอบ initialize
# 6. โหมดซ้อม: terraform destroy ทุกครั้งที่จบ (รวมตอนล้มกลางทาง)
#    โหมด --keep: เก็บเครื่องไว้ให้ชี้ DNS มาใช้จริง (ดู docs/FAILOVER_DO.md)
#
# การซ้อมไม่แตะ DNS · Caddy บนเครื่องซ้อมขอ certificate ไม่ได้เพราะโดเมนยังชี้ไป
# Oracle จึงทดสอบผ่าน SSH แทน · ขั้น certificate ทดสอบได้ตอน failover จริงเท่านั้น
#
# Usage:
#   ./scripts/failover-drill.sh --env-file PATH [--branch main] [--keep]
#
#   --env-file  สำเนา .env (export จาก password manager ลงไฟล์ชั่วคราว ลบทิ้งหลังรัน)
#   --branch    branch ที่จะ deploy (default main ซึ่งเป็น branch ของ prod)
#   --keep      ไม่ destroy ตอนจบ · ใช้ตอน failover จริง
#
# ค่าใช้จ่าย: droplet s-2vcpu-4gb ราว $0.036/ชม. การซ้อมที่ผ่านครั้งแรกใช้ 65 นาที
# (restore dump + index ราว 40 นาที เป็นส่วนที่นานที่สุด)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infra"
HISTORY_FILE="${INFRA_DIR}/.drill-history"
REPO_URL="https://github.com/dhamma-seeker/tripitaka-mcp.git"
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/tripitaka_prod}"

if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
    C_RESET=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""
fi
log()  { echo "${C_BLUE}==>${C_RESET} [$(elapsed)] $*"; }
ok()   { echo "${C_GREEN}✓${C_RESET} $*"; }
warn() { echo "${C_YELLOW}⚠${C_RESET}  $*"; }
die()  { echo "${C_RED}✗${C_RESET} $*" >&2; exit 1; }

START_TS=$(date +%s)
elapsed() { local s=$(( $(date +%s) - START_TS )); printf '%02d:%02d' $((s / 60)) $((s % 60)); }

ENV_FILE=""
BRANCH="main"
KEEP=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env-file) ENV_FILE="${2:-}"; shift 2 ;;
        --branch) BRANCH="${2:-}"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "unknown arg: $1" ;;
    esac
done

# --- 1. preflight (ยังไม่เสียเงิน) -------------------------------------------
[[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]] || die "ต้องระบุ --env-file ที่มีอยู่จริง"
command -v terraform >/dev/null 2>&1 || die "ไม่พบ terraform"
[[ -f "${SSH_KEY}" ]] || die "ไม่พบ ${SSH_KEY}"
[[ -f "${INFRA_DIR}/terraform.tfvars" || -n "${TF_VAR_do_token:-}" ]] \
    || die "ไม่พบ ${INFRA_DIR}/terraform.tfvars และไม่ได้ตั้ง TF_VAR_do_token"
[[ -f "${INFRA_DIR}/backend.hcl" ]] \
    || die "ไม่พบ ${INFRA_DIR}/backend.hcl · คัดลอกจาก backend.hcl.example (state อยู่ใน R2)"
[[ -n "${AWS_ACCESS_KEY_ID:-}" && -n "${AWS_SECRET_ACCESS_KEY:-}" ]] \
    || die "ต้อง export AWS_ACCESS_KEY_ID และ AWS_SECRET_ACCESS_KEY ของ R2 ก่อน"

log "เช็คสำเนา .env กับ .env.example..."
"${SCRIPT_DIR}/check-env.sh" "${ENV_FILE}" "${PROJECT_ROOT}/.env.example" \
    || die "สำเนา .env ไม่ครบ · แก้ก่อนแล้วค่อยสร้างเครื่อง"

cd "${INFRA_DIR}"
terraform init -input=false -backend-config=backend.hcl >/dev/null
if [[ -n "$(terraform state list 2>/dev/null)" ]]; then
    die "terraform state ยังมีทรัพยากรอยู่ (เครื่องเก่าหรือเครื่องซ้อมที่ค้าง) · ดู terraform state list แล้ว destroy ก่อน"
fi
ok "preflight ผ่าน"

# ServerAlive: pg_restore เงียบไปหลายนาที ถ้าไม่ส่งอะไรเลยเครือข่ายระหว่างทางตัดการเชื่อมต่อทิ้ง
# (ซ้อมรอบ 2026-11-03 หลุดด้วย "client_loop: send disconnect: Broken pipe" ตรงนี้)
SSH_OPTS=(-i "${SSH_KEY}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new
          -o UserKnownHostsFile="${INFRA_DIR}/.drill-known-hosts" -o ConnectTimeout=15
          -o ServerAliveInterval=30 -o ServerAliveCountMax=10)
RESULT="failed"
IP=""

cleanup() {
    local code=$?
    if [[ "${KEEP}" -eq 1 && "${RESULT}" == "passed" ]]; then
        echo
        ok "เก็บเครื่องไว้ (--keep): ${IP}"
        echo "   ขั้นต่อไปตาม docs/FAILOVER_DO.md: ชี้ A record ใน Cloudflare มาที่ ${IP}"
    else
        [[ "${KEEP}" -eq 1 ]] && warn "--keep แต่การทดสอบไม่ผ่าน · destroy เครื่องทิ้งเพื่อไม่ให้ค้างเสียเงิน"
        log "terraform destroy..."
        if terraform -chdir="${INFRA_DIR}" destroy -auto-approve -input=false >/dev/null; then
            ok "ลบเครื่องแล้ว"
        else
            echo "${C_RED}✗ destroy ไม่สำเร็จ · เครื่องอาจยังเปิดอยู่และคิดเงิน: รัน terraform destroy ใน ${INFRA_DIR} เอง${C_RESET}" >&2
        fi
    fi
    rm -f "${INFRA_DIR}/.drill-known-hosts"
    printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${RESULT}" "$(elapsed)" \
        "${BRANCH}" "$([[ ${KEEP} -eq 1 ]] && echo keep || echo drill)" >> "${HISTORY_FILE}"
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        echo "ผล: **${RESULT}** · ใช้เวลา $(elapsed) · branch ${BRANCH} · $([[ ${KEEP} -eq 1 ]] && echo keep || echo drill)" \
            >> "${GITHUB_STEP_SUMMARY}"
    fi
    echo
    echo "ผล: ${RESULT} · ใช้เวลา $(elapsed) · บันทึกใน ${HISTORY_FILE}"
    exit "${code}"
}
trap cleanup EXIT

# --- 2. สร้างเครื่อง -----------------------------------------------------------
log "terraform apply (รวมรอ cloud-init)..."
terraform apply -auto-approve -input=false >/dev/null
IP="$(terraform output -raw droplet_ip)"
# log ของ Actions ใน repo public ใครก็อ่านได้ · ตอน failover จริง IP นี้คือ origin ของเว็บ
# ดู IP ได้จาก DigitalOcean dashboard หรือ terraform output บน laptop
[[ -n "${GITHUB_ACTIONS:-}" ]] && echo "::add-mask::${IP}"
ok "droplet: ${IP}  (สร้างเสร็จที่ $(elapsed))"
remote() { ssh "${SSH_OPTS[@]}" "deploy@${IP}" "$@"; }

# --- 3. สิ่งที่ cloud-init ต้องทำ --------------------------------------------
log "เช็คผล cloud-init..."
remote 'cloud-init status --wait >/dev/null; cloud-init status' | grep -q 'status: done' \
    || die "cloud-init ไม่จบด้วย done · ดู /var/log/cloud-init-output.log บนเครื่อง"
if ! remote 'docker compose version >/dev/null && /snap/bin/aws --version >/dev/null && test -f /etc/cron.d/tripitaka'; then
    # cloud-init รายงาน done แม้คำสั่งใน runcmd ล้ม · ดึงท้าย log มาให้เห็นสาเหตุก่อนเครื่องถูกลบ
    remote 'sudo tail -n 30 /var/log/cloud-init-output.log; sudo cat /var/log/tripitaka-bootstrap-errors.log 2>/dev/null' >&2 || true
    die "เครื่องใหม่ขาด docker / aws-cli / cron.d · cloud-init ตามไม่ทัน"
fi
ok "cloud-init ครบ: docker, aws-cli, cron.d"

if [[ "${KEEP}" -eq 0 ]]; then
    # เครื่องซ้อมห้าม backup ขึ้น bucket จริง (สำเนา .env ชี้ bucket ของ prod)
    remote 'sudo rm -f /etc/cron.d/tripitaka'
fi

# --- 4. deploy แบบเดียวกับเครื่องจริง ----------------------------------------
log "วาง .env + clone ${BRANCH}..."
scp "${SSH_OPTS[@]}" -q "${ENV_FILE}" "deploy@${IP}:/opt/tripitaka/.env"
remote "set -e; cd /opt/tripitaka; chmod 600 .env
        git clone -q --branch '${BRANCH}' '${REPO_URL}' /tmp/repo
        mv /tmp/repo/.git . && rm -rf /tmp/repo && git checkout -q -f '${BRANCH}'"

log "deploy.sh (build image + restore dump จาก Hugging Face)..."
# sed -u: ไม่อย่างนั้น sed เก็บ output ไว้ส่งทีเดียวตอนจบ เวลาใน log ของ Actions จะเป็นเวลาเดียวกันหมด
# และบอกไม่ได้ว่าขั้นไหนใน deploy.sh ใช้เวลาเท่าไร
if ! remote 'cd /opt/tripitaka && ./scripts/deploy.sh' 2>&1 | sed -u 's/^/   │ /'; then
    die "deploy.sh ล้มเหลว"
fi

# --- 5. ทดสอบบนเครื่อง ---------------------------------------------------------
log "ทดสอบบนเครื่อง..."
unhealthy="$(remote "docker ps --format '{{.Names}} {{.Status}}' | grep '^tripitaka-' | grep -v '(healthy)' || true")"
if [[ -n "${unhealthy}" ]]; then
    echo "${unhealthy}" >&2
    die "container ยังไม่ healthy"
fi
[[ "$(remote "docker ps --format '{{.Names}}' | grep -c '^tripitaka-'")" -eq 5 ]] || die "container ไม่ครบ 5 ตัว"
ok "container 5 ตัว healthy"

segments="$(remote "cd /opt/tripitaka && docker exec tripitaka-db psql -U \$(grep '^POSTGRES_USER=' .env | cut -d= -f2) -d \$(grep '^POSTGRES_DB=' .env | cut -d= -f2) -Atc 'SELECT COUNT(*) FROM segment'")"
[[ "${segments}" -gt 0 ]] || die "segment ว่าง"
ok "segments: ${segments}"

remote "docker exec tripitaka-mcp-server-http python -c \"
import json, urllib.request
body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
    'protocolVersion': '2025-03-26', 'capabilities': {},
    'clientInfo': {'name': 'failover-drill', 'version': '1'}}}).encode()
req = urllib.request.Request('http://127.0.0.1:8080/mcp', body, {
    'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
text = urllib.request.urlopen(req, timeout=30).read().decode()
assert 'serverInfo' in text, text[:300]
\"" || die "/mcp ไม่ตอบ initialize"
ok "/mcp ตอบ initialize"

RESULT="passed"
