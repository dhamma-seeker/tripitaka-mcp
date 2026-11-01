#!/usr/bin/env bash
# =============================================================================
# Render infra/cloud-init.yml for providers without Terraform (Oracle Cloud)
# =============================================================================
# infra/cloud-init.yml เป็น Terraform template (ใช้กับ DO ผ่าน templatefile)
# สคริปต์นี้ทำสิ่งเดียวกับ templatefile:
#   - แทน ${deploy_public_key} ด้วย public key ที่ให้มา
#   - แปลง $${...} (escape ของ Terraform) กลับเป็น ${...}
# แล้วพิมพ์ผลออก stdout เอาไปวางในช่อง cloud-init script ของ OCI console
#
# Usage:
#   ./scripts/render-cloud-init.sh ~/.ssh/id_ed25519.pub > /tmp/cloud-init.yml
#   ./scripts/render-cloud-init.sh ~/.ssh/id_ed25519.pub | pbcopy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/../infra/cloud-init.yml"
PUBKEY_PATH="${1:-}"

[[ -n "${PUBKEY_PATH}" ]] || { echo "usage: $0 <path-to-public-key.pub>" >&2; exit 1; }
[[ -f "${PUBKEY_PATH}" ]] || { echo "ไม่พบ ${PUBKEY_PATH}" >&2; exit 1; }
[[ "${PUBKEY_PATH}" == *.pub ]] || { echo "${PUBKEY_PATH} ไม่ใช่ไฟล์ .pub (ห้ามใช้ private key)" >&2; exit 1; }

python3 - "${TEMPLATE}" "${PUBKEY_PATH}" <<'PY'
import sys
template, pubkey_path = sys.argv[1], sys.argv[2]
key = open(pubkey_path).read().strip()
text = open(template).read()
text = text.replace("${deploy_public_key}", key).replace("$${", "${")
sys.stdout.write(text)
PY
