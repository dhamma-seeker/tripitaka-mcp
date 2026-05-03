"""Embedding progress checker.

Queries the local DB and shows:
- total segments + segments still missing an embedding
- progress percentage and per-pitaka breakdown
- ETA based on a rolling sample (saves prev count + timestamp)

Usage:
    python scripts/check_embedding_progress.py            # one-shot snapshot
    python scripts/check_embedding_progress.py --watch    # refresh every 30s

ETA caveats: the rate is sampled between two adjacent runs. The first
run shows "no rate yet"; subsequent runs compare against the cached
state in /tmp/tripitaka-embedding-progress.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from db.connection import get_connection, release_connection

CACHE_FILE = Path("/tmp/tripitaka-embedding-progress.json")


def fetch_state() -> dict:
    """Return total/missing counts overall and per pitaka."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.code, COUNT(seg.id) AS total,
                   COUNT(seg.id) FILTER (WHERE seg.embedding IS NULL) AS missing
            FROM pitaka p
            LEFT JOIN nikaya n ON n.pitaka_id = p.id
            LEFT JOIN book b ON b.nikaya_id = n.id
            LEFT JOIN section sec ON sec.book_id = b.id
            LEFT JOIN segment seg ON seg.section_id = sec.id
            GROUP BY p.id, p.code, p.sort_order
            ORDER BY p.sort_order
            """
        )
        per_pitaka = [
            {"pitaka": row[0], "total": row[1], "missing": row[2]}
            for row in cur.fetchall()
        ]
        total = sum(p["total"] for p in per_pitaka)
        missing = sum(p["missing"] for p in per_pitaka)
        return {
            "ts": time.time(),
            "total": total,
            "missing": missing,
            "done": total - missing,
            "per_pitaka": per_pitaka,
        }
    finally:
        cur.close()
        release_connection(conn)


def load_cached() -> dict | None:
    if not CACHE_FILE.exists():
        return None
    try:
        return json.loads(CACHE_FILE.read_text())
    except json.JSONDecodeError:
        return None


def save_cache(state: dict) -> None:
    CACHE_FILE.write_text(json.dumps(state))


def fmt_eta(missing: int, rate_per_sec: float) -> str:
    if rate_per_sec <= 0:
        return "—"
    seconds_left = missing / rate_per_sec
    eta_at = datetime.now() + timedelta(seconds=seconds_left)
    if seconds_left < 60:
        return f"{seconds_left:.0f}s (~{eta_at:%H:%M:%S})"
    if seconds_left < 3600:
        return f"{seconds_left/60:.1f}m (~{eta_at:%H:%M})"
    return f"{seconds_left/3600:.1f}h (~{eta_at:%H:%M})"


def render(state: dict, prev: dict | None) -> None:
    print()
    print(f"📊 Embedding progress @ {datetime.now():%H:%M:%S}")
    print("─" * 60)

    total = state["total"]
    done = state["done"]
    missing = state["missing"]
    pct = 100 * done / total if total else 0

    bar_w = 40
    filled = int(bar_w * done / total) if total else 0
    bar = "█" * filled + "░" * (bar_w - filled)
    print(f"  [{bar}] {pct:5.1f}%")
    print(f"  done:    {done:>10,} / {total:,}")
    print(f"  missing: {missing:>10,}")

    if prev and state["ts"] > prev["ts"]:
        delta_done = state["done"] - prev["done"]
        delta_t = state["ts"] - prev["ts"]
        rate = delta_done / delta_t if delta_t > 0 else 0
        print(f"  rate:    {rate:>10.1f} segs/sec  (over {delta_t:.0f}s window)")
        print(f"  ETA:     {fmt_eta(missing, rate)}")
    else:
        print(f"  rate:    (run again to compute)")

    print()
    print("  Per pitaka:")
    for p in state["per_pitaka"]:
        p_done = p["total"] - p["missing"]
        p_pct = 100 * p_done / p["total"] if p["total"] else 0
        print(
            f"    {p['pitaka']:<11} {p_done:>8,} / {p['total']:>8,} "
            f"({p_pct:5.1f}%)  missing: {p['missing']:,}"
        )
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="refresh every 30s")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                prev = load_cached()
                state = fetch_state()
                render(state, prev)
                save_cache(state)
                if state["missing"] == 0:
                    print("✅ embedding complete")
                    return 0
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nstopped (cache saved)")
            return 0

    prev = load_cached()
    state = fetch_state()
    render(state, prev)
    save_cache(state)
    return 0 if state["missing"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
