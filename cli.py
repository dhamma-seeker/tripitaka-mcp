#!/usr/bin/env python3
"""
Tripitaka MCP — command-line interface สำหรับ local install.

Subcommands:
  tripitaka-mcp init    ดาวน์โหลด SQLite database (~120 MB) จาก HuggingFace
  tripitaka-mcp serve   รัน MCP server แบบ stdio (สำหรับ Claude Desktop / Cursor)

local install ใช้ SQLite backend เสมอ — ดู Dual-Backend Discipline ใน CLAUDE.md.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.request

# SQLite database บน HuggingFace (สร้างด้วย scripts/build_sqlite_db.py)
HF_DB_URL = (
    "https://huggingface.co/datasets/dhamma-seeker/tripitaka-mcp-dump/"
    "resolve/main/tripitaka.db"
)


def _log(msg: str) -> None:
    """พิมพ์ลง stderr — stdout สงวนไว้สำหรับ MCP protocol (stdio transport)."""
    print(msg, file=sys.stderr, flush=True)


def cmd_init(args: argparse.Namespace) -> int:
    """ดาวน์โหลด SQLite database ไปไว้ที่ user data dir."""
    from db.sqlite_connection import resolve_db_path

    dest = resolve_db_path()
    if os.path.exists(dest) and not args.force:
        size_mb = os.path.getsize(dest) / 1024 / 1024
        _log(f"database already present: {dest} ({size_mb:.0f} MB)")
        _log("use `tripitaka-mcp init --force` to re-download.")
        return 0

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    _log("downloading SQLite database...")
    _log(f"  from: {HF_DB_URL}")
    _log(f"  to:   {dest}")
    try:
        with urllib.request.urlopen(HF_DB_URL) as resp:  # noqa: S310 (trusted URL)
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        pct = done * 100 // total
                        print(
                            f"\r  {pct:3d}%  ({done // 1024 // 1024} MB)",
                            end="",
                            file=sys.stderr,
                            flush=True,
                        )
        print("", file=sys.stderr)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        _log(f"download failed: {e}")
        return 1

    os.replace(tmp, dest)
    size_mb = os.path.getsize(dest) / 1024 / 1024
    _log(f"✓ database ready: {dest} ({size_mb:.0f} MB)")
    _log("next:  tripitaka-mcp serve")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """รัน MCP server แบบ stdio. ตั้ง backend = sqlite ก่อน import main."""
    # ตั้ง env ก่อน import main — main.py อ่าน env ตอน module load
    os.environ["TRIPITAKA_BACKEND"] = "sqlite"
    os.environ.setdefault("TRIPITAKA_SKIP_MIGRATIONS", "true")

    from db.sqlite_connection import resolve_db_path

    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        _log(f"error: SQLite database not found at {db_path}")
        _log("run `tripitaka-mcp init` first to download it.")
        return 1

    _log(f"Tripitaka MCP (local / SQLite) — db: {db_path}")
    import main  # noqa: E402 — ต้อง import หลังตั้ง env

    main.mcp.run(transport="stdio")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tripitaka-mcp",
        description="Local MCP server for the Pāli Tipiṭaka (offline, SQLite).",
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="download the SQLite database (~120 MB)")
    p_init.add_argument(
        "--force", action="store_true", help="re-download even if already present"
    )
    p_init.set_defaults(func=cmd_init)

    p_serve = sub.add_parser("serve", help="run the MCP server (stdio transport)")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
