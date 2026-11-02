#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — เทียบ .env กับ .env.example
# =============================================================================
# กันเครื่องใหม่ (หรือสำเนา .env ที่เก็บไว้นอกเครื่อง) ตามไม่ทัน prod:
#   - key ที่ไม่ได้ comment ใน .env.example = บังคับ → ขาดตัวไหนจบด้วย exit 1
#   - key ใน .env ที่ .env.example ไม่ได้พูดถึงเลย (แม้แต่แบบ "# KEY=") → เตือน
#     เพราะเครื่องถัดไปที่สร้างจาก .env.example จะไม่มี key นั้น
#
# deploy.sh เรียกสคริปต์นี้ก่อนแตะ docker · failover-drill.sh เรียกกับสำเนา .env
# ก่อนสร้างเครื่อง จะได้รู้ว่าสำเนาเก่าตั้งแต่ยังไม่เสียเงิน
#
# Usage:
#   ./scripts/check-env.sh [ENV_FILE] [EXAMPLE_FILE]
#   (default: .env กับ .env.example ใน project root)
#
# ห้ามพิมพ์ค่าของ key ออกจอ: สคริปต์นี้อ่านเฉพาะชื่อ

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${1:-${PROJECT_ROOT}/.env}"
EXAMPLE_FILE="${2:-${PROJECT_ROOT}/.env.example}"

[[ -f "${ENV_FILE}" ]] || { echo "✗ ไม่พบ ${ENV_FILE}" >&2; exit 1; }
[[ -f "${EXAMPLE_FILE}" ]] || { echo "✗ ไม่พบ ${EXAMPLE_FILE}" >&2; exit 1; }

keys_set()      { grep -oE '^[A-Z][A-Z0-9_]*=' "$1" | tr -d '=' | sort -u; }
keys_mentioned() { grep -oE '^#? ?[A-Z][A-Z0-9_]*=' "$1" | sed -E 's/^#? ?//; s/=$//' | sort -u; }

required="$(keys_set "${EXAMPLE_FILE}")"
documented="$(keys_mentioned "${EXAMPLE_FILE}")"
present="$(keys_set "${ENV_FILE}")"

missing="$(comm -23 <(printf '%s\n' "${required}") <(printf '%s\n' "${present}") | sed '/^$/d')"
undocumented="$(comm -13 <(printf '%s\n' "${documented}") <(printf '%s\n' "${present}") | sed '/^$/d')"

if [[ -n "${undocumented}" ]]; then
    echo "⚠  key ใน $(basename "${ENV_FILE}") ที่ .env.example ไม่ได้ระบุ (เพิ่มลง .env.example เป็น '# KEY=' พร้อมคำอธิบาย):"
    printf '     %s\n' ${undocumented}
fi

if [[ -n "${missing}" ]]; then
    echo "✗ $(basename "${ENV_FILE}") ขาด key ที่ .env.example บังคับ:" >&2
    printf '     %s\n' ${missing} >&2
    echo "   ถ้าเป็นสำเนาจาก password manager แปลว่าสำเนาเก่ากว่า prod: เอาค่าจากเครื่องจริงมาเติมแล้วอัปเดตสำเนา" >&2
    exit 1
fi

echo "✓ $(basename "${ENV_FILE}") มี key ครบตาม .env.example"
