#!/usr/bin/env bash
# Build (optional) + publish the local SQLite database to HuggingFace.
#
# The SQLite db is what `tripitaka-mcp init` downloads for the local install
# (see cli.py). It is built from the production Postgres by build_sqlite_db.py.
#
# Prereqs (one-time):
#   pip install huggingface_hub
#   huggingface-cli login   # HF token with write access to the dump dataset
#
# Usage:
#   bash scripts/publish_sqlite_db.sh              # publish existing tripitaka.db
#   bash scripts/publish_sqlite_db.sh --build      # rebuild from Postgres, then publish
#   bash scripts/publish_sqlite_db.sh --build-only # rebuild only, do not upload

set -euo pipefail
cd "$(dirname "$0")/.."

DB_FILE="tripitaka.db"
HF_DATASET="dhamma-seeker/tripitaka-mcp-dump"

DO_BUILD=0
UPLOAD=1
case "${1:-}" in
    --build)      DO_BUILD=1 ;;
    --build-only) DO_BUILD=1; UPLOAD=0 ;;
    "")           ;;
    *)            echo "unknown arg: $1"; exit 1 ;;
esac

# ---------- 1. build (optional) ----------
if [ "$DO_BUILD" = "1" ]; then
    echo "▶ building SQLite db from Postgres..."
    set -a; source .env; set +a
    .venv/bin/python scripts/build_sqlite_db.py --out "$DB_FILE"
fi

# ---------- 2. sanity ----------
if [ ! -f "$DB_FILE" ]; then
    echo "❌ $DB_FILE not found — run with --build, or run build_sqlite_db.py first"
    exit 1
fi
echo "▶ $DB_FILE ($(du -h "$DB_FILE" | cut -f1))"

# ---------- 3. smoke check ----------
echo "▶ verifying SQLite db..."
.venv/bin/python - "$DB_FILE" <<'PY'
import sqlite3, sys
db = sys.argv[1]
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
seg = c.execute("SELECT COUNT(*) FROM segment").fetchone()[0]
fts = c.execute("SELECT COUNT(*) FROM segment_fts WHERE segment_fts MATCH 'dukkha'").fetchone()[0]
c.close()
if seg < 400000 or fts < 1:
    print(f"❌ suspicious: segment={seg} fts_hits={fts}"); sys.exit(1)
print(f"  ✅ segment={seg:,}  FTS5 'dukkha' hits={fts:,}")
PY

if [ "$UPLOAD" = "0" ]; then
    echo "▶ --build-only mode: stopping here (not uploaded)"
    exit 0
fi

# ---------- 4. upload to HuggingFace ----------
echo "▶ uploading to HuggingFace dataset $HF_DATASET ..."
if ! command -v huggingface-cli &> /dev/null; then
    echo "❌ huggingface-cli not found — install: pip install huggingface_hub"
    exit 1
fi
huggingface-cli upload \
    "$HF_DATASET" \
    "$DB_FILE" \
    "$DB_FILE" \
    --repo-type dataset \
    --commit-message "SQLite db for local install ($(date +%Y-%m-%d))"

echo ""
echo "✅ Done — 'tripitaka-mcp init' will now download this db."
