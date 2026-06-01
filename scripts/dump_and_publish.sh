#!/usr/bin/env bash
# Dump local DB → upload to HuggingFace dataset → ready for prod restore.
#
# Run AFTER scripts/generate_embeddings.py finishes (missing=0).
#
# Prereqs (one-time):
#   pip install huggingface_hub
#   huggingface-cli login   # needs an HF token with write access to dhamma-seeker/tripitaka-mcp-dump
#
# Usage:
#   bash scripts/dump_and_publish.sh                 # full flow
#   bash scripts/dump_and_publish.sh --dump-only     # just produce the .dump file
#
# After this script finishes, on the droplet run `./scripts/deploy.sh` —
# it will pull the new dump from HF and restore.

set -euo pipefail

cd "$(dirname "$0")/.."

DUMP_ONLY=0
[ "${1:-}" = "--dump-only" ] && DUMP_ONLY=1

# ---------- 1. sanity checks ----------
echo "▶ checking embedding completeness..."
missing=$(.venv/bin/python -c "
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from db.connection import get_connection, release_connection
c = get_connection()
try:
    cur = c.cursor()
    cur.execute('SELECT COUNT(*) FROM segment WHERE embedding IS NULL')
    print(cur.fetchone()[0])
finally:
    cur.close()
    release_connection(c)
")

if [ "$missing" -ne 0 ]; then
    echo "❌ $missing segments still missing embeddings — run scripts/generate_embeddings.py first"
    exit 1
fi
echo "  ✅ all segments embedded"

# ---------- 2. dump ----------
DUMP_FILE="tripitaka_production_data.dump"
DUMP_BAK="tripitaka_production_data.dump.bak.$(date +%Y%m%d-%H%M%S)"

# Backup current dump if exists
if [ -f "$DUMP_FILE" ]; then
    echo "▶ backing up old dump → $DUMP_BAK"
    mv "$DUMP_FILE" "$DUMP_BAK"
fi

# Load DB credentials
set -a
source .env
set +a

echo "▶ pg_dump → $DUMP_FILE"
docker exec tripitaka-db pg_dump \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --format=custom --compress=6 \
    > "$DUMP_FILE"

size=$(du -h "$DUMP_FILE" | cut -f1)
echo "  ✅ dump created ($size)"

# ---------- 3. quick smoke check on dump ----------
echo "▶ verifying dump can be read..."
docker run --rm -v "$(pwd):/work" ankane/pgvector:latest \
    pg_restore --list /work/"$DUMP_FILE" > /tmp/tripitaka-dump-toc.txt 2>&1 || true
toc_lines=$(wc -l < /tmp/tripitaka-dump-toc.txt)
if [ "$toc_lines" -lt 50 ]; then
    echo "❌ dump TOC suspiciously small ($toc_lines lines) — dump may be corrupt"
    cat /tmp/tripitaka-dump-toc.txt
    exit 1
fi
echo "  ✅ dump TOC has $toc_lines entries"

if [ "$DUMP_ONLY" = "1" ]; then
    echo ""
    echo "▶ --dump-only mode: stopping here"
    echo "  upload manually with:"
    echo "  huggingface-cli upload dhamma-seeker/tripitaka-mcp-dump $DUMP_FILE --repo-type dataset"
    exit 0
fi

# ---------- 4. upload to HuggingFace ----------
echo "▶ uploading to HuggingFace dataset..."
if ! command -v huggingface-cli &> /dev/null; then
    echo "❌ huggingface-cli not found — install with: pip install huggingface_hub"
    exit 1
fi

huggingface-cli upload \
    dhamma-seeker/tripitaka-mcp-dump \
    "$DUMP_FILE" \
    "$DUMP_FILE" \
    --repo-type dataset \
    --commit-message "Phase B+C — Vinaya + Abhidhamma full coverage ($(date +%Y-%m-%d))"

echo ""
echo "✅ Done!"
echo ""
echo "Next: SSH to droplet and run ./scripts/deploy.sh"
echo "  ssh -i ~/.ssh/tripitaka_prod deploy@${DROPLET_IP:-<your-droplet-ip>}"
echo "  cd /opt/tripitaka"
echo "  git pull"
echo "  rm -f tripitaka_production_data.dump  # force re-download from HF"
echo "  docker compose -f docker-compose.prod.yml stop mcp-server mcp-server-http"
echo "  ./scripts/deploy.sh"
