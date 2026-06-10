"""MCP Apps (interactive UI) — additive, env-gated PoC.

ลงทะเบียน `ui://` HTML resource + tool ที่ประกาศ `_meta.ui.resourceUri` เพื่อให้ host
ที่รองรับ MCP Apps (Claude Desktop/web/mobile, VS Code Copilot ฯลฯ) **render พระสูตร
inline ในแชท** แทนที่จะคืน JSON ก้อนใหญ่.

ออกแบบให้ **additive ล้วน** ตาม Dual-Backend Discipline:
  - pure-Python/text — ไม่แตะ SQL, ไม่แก้ tool เดิม, ไม่แก้บรรทัด `mcp = FastMCP(...)`.
  - gate ด้วย env `TRIPITAKA_MCP_APP` → default OFF → smoke test 22/22 + tool surface เดิม
    (9 local / 11 hosted) ไม่กระทบเลยจนกว่าจะเปิด flag.

QW0 (ไฟล์นี้): พิสูจน์ว่า ui:// resource render ได้ inline + ช่อง postMessage ทำงาน.
QW1+: ป้อน segment จริงจาก get_sutta เข้า UI + ไฮไลต์ segment ที่อ้างถึง.
"""

from __future__ import annotations

import os

# ──────────────────────────────────────────────────────────────────────────
# ui:// resource URIs
# ──────────────────────────────────────────────────────────────────────────
UI_SUTTA_VIEWER = "ui://tripitaka/sutta-viewer.html"


def mcp_app_enabled() -> bool:
    """เปิด MCP App surface ต่อเมื่อ `TRIPITAKA_MCP_APP` ถูกตั้งเป็น truthy."""
    return os.getenv("TRIPITAKA_MCP_APP", "").strip().lower() in {"1", "true", "yes", "on"}


# ──────────────────────────────────────────────────────────────────────────
# Viewer HTML — generated โดย mcp_app_ui/ (vite bundle MCP Apps SDK inline
# → ไม่มี CDN/network dep ตอน runtime, offline ได้เต็มตัว — local SQLite รอด)
# rebuild: cd mcp_app_ui && npm install && npm run build
# ──────────────────────────────────────────────────────────────────────────
from mcp_app_viewer_html import VIEWER_HTML as _SUTTA_VIEWER_HTML


# จำนวน segment สูงสุดที่ส่งเข้า viewer เมื่อไม่ได้ระบุ around (กัน payload ระเบิด).
_VIEWER_MAX_SEGMENTS = 80


def _to_viewer_payload(sutta: dict, target_segment_id: str | None) -> dict:
    """แปลงผลจาก get_sutta(...) → shape ที่ UI ใช้: {ref,title,target_segment_id,
    segments:[{id,pali,en}], total, truncated}."""
    segs_in = sutta.get("segments") or []
    truncated = False
    if target_segment_id is None and len(segs_in) > _VIEWER_MAX_SEGMENTS:
        segs_in = segs_in[:_VIEWER_MAX_SEGMENTS]
        truncated = True
    segments = [
        {
            "id": s.get("segment_id", ""),
            "pali": s.get("text_pali") or "",
            "en": s.get("text_english") or "",
        }
        for s in segs_in
    ]
    # title อาจเป็น dict {pali,thai,english} หรือ str → ทำเป็น string เดียวให้ UI
    raw_title = sutta.get("title")
    if isinstance(raw_title, dict):
        parts = [raw_title.get("english"), raw_title.get("pali")]
        title = " · ".join(p for p in parts if p) or sutta.get("sutta_id", "")
    else:
        title = raw_title or sutta.get("sutta_id", "")
    return {
        "ref": sutta.get("sutta_id", ""),
        "title": title,
        "target_segment_id": target_segment_id,
        "segments": segments,
        "total": sutta.get("total_segments", len(segments)),
        "truncated": truncated,
    }


def register_mcp_app_ui(mcp, get_sutta) -> list[str]:
    """ลงทะเบียน ui:// resource + entry-point tool. คืน list ชื่อสิ่งที่ register
    (ไว้ log/test). เรียกจาก main.py ต่อเมื่อ `mcp_app_enabled()` เป็น True.

    `get_sutta` = ฟังก์ชัน get_sutta จาก main (inject เพื่อเลี่ยง circular import).
    """
    from fastmcp.apps import AppConfig
    from fastmcp.utilities.mime import UI_MIME_TYPE

    registered: list[str] = []

    @mcp.resource(
        UI_SUTTA_VIEWER,
        name="Tipiṭaka sutta viewer",
        description="Inline bilingual (Pāli + English) sutta reader rendered in-chat.",
        mime_type=UI_MIME_TYPE,
        # SDK ถูก bundle ใน HTML แล้ว (vite singlefile) → ไม่ต้องการ external
        # origin ใดๆ — ไม่ประกาศ CSP = sandbox แน่นสุด + offline ได้
    )
    def _sutta_viewer_ui() -> str:
        return _SUTTA_VIEWER_HTML

    registered.append(UI_SUTTA_VIEWER)

    @mcp.tool(
        name="open_sutta_viewer",
        app=AppConfig(resource_uri=UI_SUTTA_VIEWER),
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def open_sutta_viewer(
        sutta_id: str,
        around: str | None = None,
        window: int = 12,
    ) -> dict:
        """Open an interactive bilingual sutta viewer inside the chat.

        Renders Pāli and the Bhikkhu Sujato English translation side by side
        in an in-conversation panel. Prefer this over dumping raw segments when
        the user wants to *read* a sutta.

        - `sutta_id` — standard SuttaCentral id, e.g. `sn56.11`, `mn10`, `dn22`.
        - `around` — a segment_id (e.g. `dn22:18.1`, from a search hit) to centre
          on; that segment is highlighted and scrolled into view. Use this after
          a search so the reader lands on the exact cited line.
        - `window` — segments before/after `around` to include (default 12).

        Without `around`, shows the sutta from the top (capped for long suttas).
        """
        sutta = get_sutta(
            sutta_id,
            language="all",
            around=around,
            window=window,
        )
        # get_sutta อาจคืน error dict (เช่น sutta ไม่พบ) — ส่งต่อให้โมเดลเห็น
        if "segments" not in sutta:
            return sutta
        return _to_viewer_payload(sutta, target_segment_id=around)

    registered.append("open_sutta_viewer")
    return registered
