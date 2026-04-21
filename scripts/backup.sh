#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — Daily DB backup → S3-compatible object storage
# =============================================================================
# รันจาก cron บน VPS (user: deploy, cwd: /opt/tripitaka)
# รองรับ S3-compatible provider ทุกเจ้า: AWS S3, DO Spaces, Cloudflare R2,
# Backblaze B2, MinIO, Wasabi, ฯลฯ — กำหนดผ่าน env vars
#
# ทำอะไรบ้าง:
# 1. pg_dump ฐาน production (custom format) → /tmp
# 2. อัปโหลดขึ้น S3 bucket ผ่าน AWS CLI
# 3. ลบ object ที่เก่ากว่า BACKUP_RETENTION_DAYS วัน
# 4. ลบไฟล์ temp
#
# ต้องตั้งค่าใน .env (หรือ environment) ก่อน:
#   POSTGRES_USER, POSTGRES_DB                 (มีอยู่แล้ว)
#   DO_SPACES_BUCKET=<your-bucket-name>
#   DO_SPACES_REGION=<region>                  (เช่น us-east-1, sgp1, auto)
#   DO_SPACES_ENDPOINT=<s3-endpoint-url>       (เช่น https://s3.amazonaws.com)
#   DO_SPACES_KEY=...
#   DO_SPACES_SECRET=...
#   BACKUP_RETENTION_DAYS=7                    (optional, default 7)
#
# Note: ชื่อ var ขึ้นต้น DO_SPACES_ เพราะ legacy — ใช้ได้กับทุก S3 provider
#
# Crontab (ติดตั้งด้วย `crontab -e` ภายใต้ user deploy):
#   0 3 * * * /opt/tripitaka/scripts/backup.sh >> /var/log/tripitaka-backup.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

log()  { echo "[$(date -u +%FT%TZ)] $*"; }
die()  { echo "[$(date -u +%FT%TZ)] ERROR: $*" >&2; exit 1; }

# --- load .env ---------------------------------------------------------------
[[ -f .env ]] || die ".env ไม่พบที่ ${PROJECT_ROOT}"
set -a; source .env; set +a

: "${POSTGRES_USER:?POSTGRES_USER ต้องตั้งใน .env}"
: "${POSTGRES_DB:?POSTGRES_DB ต้องตั้งใน .env}"
: "${DO_SPACES_BUCKET:?DO_SPACES_BUCKET ต้องตั้งใน .env}"
: "${DO_SPACES_REGION:?DO_SPACES_REGION ต้องตั้งใน .env}"
: "${DO_SPACES_ENDPOINT:?DO_SPACES_ENDPOINT ต้องตั้งใน .env}"
: "${DO_SPACES_KEY:?DO_SPACES_KEY ต้องตั้งใน .env}"
: "${DO_SPACES_SECRET:?DO_SPACES_SECRET ต้องตั้งใน .env}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

command -v aws >/dev/null 2>&1 || die "aws CLI ไม่พบ — ติดตั้งด้วย 'apt-get install awscli' หรือ pipx"
docker ps --format '{{.Names}}' | grep -q '^tripitaka-db$' || die "container tripitaka-db ไม่รัน"

# --- 1. pg_dump --------------------------------------------------------------
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_FILE="/tmp/tripitaka-${TS}.dump"
OBJECT_KEY="daily/tripitaka-${TS}.dump"

log "pg_dump → ${DUMP_FILE}"
docker exec -i tripitaka-db pg_dump -U "${POSTGRES_USER}" -Fc "${POSTGRES_DB}" > "${DUMP_FILE}" \
    || die "pg_dump ล้มเหลว"
SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
log "dump size: ${SIZE}"

# --- 2. upload to S3 bucket --------------------------------------------------
export AWS_ACCESS_KEY_ID="${DO_SPACES_KEY}"
export AWS_SECRET_ACCESS_KEY="${DO_SPACES_SECRET}"
export AWS_DEFAULT_REGION="${DO_SPACES_REGION}"

log "upload → s3://${DO_SPACES_BUCKET}/${OBJECT_KEY}"
aws --endpoint-url "${DO_SPACES_ENDPOINT}" s3 cp \
    "${DUMP_FILE}" "s3://${DO_SPACES_BUCKET}/${OBJECT_KEY}" \
    --only-show-errors \
    || die "upload ล้มเหลว"
log "upload สำเร็จ"

# --- 3. prune old backups ----------------------------------------------------
log "prune backups เก่ากว่า ${RETENTION_DAYS} วัน"
CUTOFF_EPOCH=$(date -u -d "${RETENTION_DAYS} days ago" +%s 2>/dev/null \
    || date -u -v-"${RETENTION_DAYS}"d +%s)  # BSD date fallback

aws --endpoint-url "${DO_SPACES_ENDPOINT}" s3api list-objects-v2 \
    --bucket "${DO_SPACES_BUCKET}" --prefix "daily/" \
    --query 'Contents[].[Key,LastModified]' --output text 2>/dev/null \
| while read -r KEY LAST_MOD; do
    [[ -z "${KEY}" ]] && continue
    OBJ_EPOCH=$(date -u -d "${LAST_MOD}" +%s 2>/dev/null \
        || date -u -jf "%Y-%m-%dT%H:%M:%S" "${LAST_MOD%.*}" +%s)
    if (( OBJ_EPOCH < CUTOFF_EPOCH )); then
        log "  delete: ${KEY}"
        aws --endpoint-url "${DO_SPACES_ENDPOINT}" s3 rm \
            "s3://${DO_SPACES_BUCKET}/${KEY}" --only-show-errors || true
    fi
done

# --- 4. cleanup --------------------------------------------------------------
rm -f "${DUMP_FILE}"
log "เสร็จ: ${OBJECT_KEY} (${SIZE})"
