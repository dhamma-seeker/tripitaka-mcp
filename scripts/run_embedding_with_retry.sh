#!/usr/bin/env bash
# Resilient wrapper for generate_embeddings.py — auto-retries on DB hiccups.
#
# Why: Mac sleep / Docker restarts kill the DB connection mid-run. The
# python script doesn't reconnect, so it dies with a partial commit.
# This wrapper retries until missing-embedding count reaches zero.
#
# Usage:
#   bash scripts/run_embedding_with_retry.sh
#
# Tip: pair with `caffeinate -dis &` before starting if running overnight,
# so macOS doesn't suspend Docker.

set -u

cd "$(dirname "$0")/.."

LOG=/tmp/tripitaka-embedding-retry.log
MAX_ATTEMPTS=20
SLEEP_BETWEEN=15
EMBEDDING_BATCH_SIZE=${EMBEDDING_BATCH_SIZE:-128}
export EMBEDDING_BATCH_SIZE

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) starting wrapper (batch=$EMBEDDING_BATCH_SIZE)" | tee -a "$LOG"

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) attempt $attempt/$MAX_ATTEMPTS" | tee -a "$LOG"

    # Wait for DB to be healthy (handles container restart timing)
    for i in {1..30}; do
        if docker exec tripitaka-db pg_isready -U admin -q 2>/dev/null; then
            break
        fi
        echo "  waiting for DB..." | tee -a "$LOG"
        sleep 2
    done

    # Run the embedding generator
    .venv/bin/python scripts/generate_embeddings.py 2>&1 | tee -a "$LOG"
    rc=${PIPESTATUS[0]}

    # Check if any segments still need embeddings
    missing=$(.venv/bin/python -c "
import os, sys
sys.path.insert(0, '.')
os.environ.setdefault('DATABASE_URL', open('.env').read().split('DATABASE_URL=')[1].split('\n')[0])
from db.connection import get_connection, release_connection
conn = get_connection()
try:
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM segment WHERE embedding IS NULL')
    print(cur.fetchone()[0])
finally:
    cur.close()
    release_connection(conn)
" 2>/dev/null)

    if [ "$missing" = "0" ]; then
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ✅ all segments embedded (rc=$rc)" | tee -a "$LOG"
        exit 0
    fi

    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) attempt $attempt finished rc=$rc missing=$missing — retrying in ${SLEEP_BETWEEN}s" | tee -a "$LOG"
    sleep $SLEEP_BETWEEN
done

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) ❌ exceeded $MAX_ATTEMPTS attempts — manual intervention" | tee -a "$LOG"
exit 1
