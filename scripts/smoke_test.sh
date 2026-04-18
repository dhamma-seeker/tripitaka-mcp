#!/usr/bin/env bash
# =============================================================================
# Tripitaka MCP — Smoke test (รันจาก laptop ยิงไปที่ staging/production)
# =============================================================================
# ตรวจว่า deploy ใหม่พร้อมใช้งาน:
# 1. DNS resolve ได้
# 2. TLS cert valid + expiry > 7 วัน
# 3. /health ตอบ 200 "ok"
# 4. security headers ถูกต้อง
# 5. rate limit ทำงาน (20 req พร้อมกัน → มี 429)
# 6. SSE endpoint เปิด stream ได้
#
# Usage:
#   ./scripts/smoke_test.sh https://mcp.example.org
#   ./scripts/smoke_test.sh mcp.example.org   # auto-prepend https://

set -uo pipefail

URL="${1:-}"
[[ -z "${URL}" ]] && { echo "usage: $0 <url>" >&2; exit 2; }
[[ "${URL}" != http* ]] && URL="https://${URL}"
HOST="$(echo "${URL}" | sed -E 's|https?://||; s|/.*||')"

if [[ -t 1 ]]; then
    C_RESET=$'\033[0m'; C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'
else C_RESET=""; C_RED=""; C_GREEN=""; C_YELLOW=""; fi

PASS=0; FAIL=0
pass() { echo "${C_GREEN}✓${C_RESET} $*"; PASS=$((PASS+1)); }
fail() { echo "${C_RED}✗${C_RESET} $*"; FAIL=$((FAIL+1)); }
warn() { echo "${C_YELLOW}⚠${C_RESET} $*"; }

echo "Smoke test → ${URL}"
echo

# --- 1. DNS ------------------------------------------------------------------
if host "${HOST}" >/dev/null 2>&1 || dig +short "${HOST}" | grep -q .; then
    pass "DNS resolves: ${HOST}"
else
    fail "DNS lookup ล้มเหลว: ${HOST}"
fi

# --- 2. TLS + expiry ---------------------------------------------------------
CERT_INFO=$(echo | openssl s_client -servername "${HOST}" -connect "${HOST}:443" 2>/dev/null | openssl x509 -noout -dates -issuer 2>/dev/null || echo "")
if [[ -n "${CERT_INFO}" ]]; then
    NOT_AFTER=$(echo "${CERT_INFO}" | sed -n 's/notAfter=//p')
    ISSUER=$(echo "${CERT_INFO}" | sed -n 's/issuer=//p')
    EXPIRY_EPOCH=$(date -j -f "%b %d %T %Y %Z" "${NOT_AFTER}" +%s 2>/dev/null || date -d "${NOT_AFTER}" +%s 2>/dev/null || echo 0)
    NOW=$(date +%s)
    DAYS=$(( (EXPIRY_EPOCH - NOW) / 86400 ))
    if [[ ${DAYS} -gt 7 ]]; then
        pass "TLS cert valid (${DAYS} วันจะหมดอายุ) — ${ISSUER}"
    else
        fail "TLS cert จะหมดใน ${DAYS} วัน!"
    fi
else
    fail "ดึง TLS cert ไม่ได้"
fi

# --- 3. /health --------------------------------------------------------------
HEALTH=$(curl -fsS --max-time 10 "${URL}/health" || echo "")
if [[ "${HEALTH}" == "ok" ]]; then
    pass "/health → ok"
else
    fail "/health ตอบ: '${HEALTH}' (คาด 'ok')"
fi

# --- 4. security headers -----------------------------------------------------
HEADERS=$(curl -sI --max-time 10 "${URL}/health" || echo "")
for h in "strict-transport-security" "x-content-type-options" "x-frame-options"; do
    if echo "${HEADERS}" | grep -qi "^${h}:"; then
        pass "header ${h} พบ"
    else
        fail "header ${h} หาย"
    fi
done
if echo "${HEADERS}" | grep -qi "^server: caddy"; then
    fail "header 'Server: Caddy' เปิดโผล่ (Caddyfile ควร strip -Server)"
else
    pass "Server header ถูกซ่อน"
fi

# --- 5. rate limit -----------------------------------------------------------
# ยิง 20 req รวดเดียว — ควรมี 429 อย่างน้อย 1 ตัว (limit = 10 req/10s)
CODES=$(for i in $(seq 1 20); do
    curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 "${URL}/health" &
done; wait)
NUM_429=$(echo "${CODES}" | grep -c "^429$" || true)
NUM_200=$(echo "${CODES}" | grep -c "^200$" || true)
if [[ ${NUM_429} -gt 0 ]]; then
    pass "rate limit ทำงาน (20 reqs → ${NUM_200} × 200, ${NUM_429} × 429)"
else
    warn "rate limit ไม่ trigger (20/20 ผ่าน) — อาจผ่าน Cloudflare cache หรือ zone ยังไม่ apply"
fi

# --- 6. SSE endpoint (MCP_TRANSPORT=sse) -------------------------------------
# MCP SSE ควรตอบ Content-Type: text/event-stream
SSE_CT=$(curl -sI --max-time 5 "${URL}/sse" 2>/dev/null | grep -i "^content-type:" | head -1 || echo "")
if echo "${SSE_CT}" | grep -qi "text/event-stream"; then
    pass "/sse → text/event-stream (MCP transport ทำงาน)"
else
    warn "/sse ไม่ใช่ event-stream (อาจใช้ stdio transport, ข้ามได้)"
fi

# --- summary -----------------------------------------------------------------
echo
echo "---"
echo "PASS: ${PASS}  FAIL: ${FAIL}"
if [[ ${FAIL} -eq 0 ]]; then
    echo "${C_GREEN}พร้อมใช้งาน 🎉${C_RESET}"
    exit 0
else
    echo "${C_RED}พบปัญหา — แก้ก่อน promote เป็น production${C_RESET}"
    exit 1
fi
