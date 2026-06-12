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

from pydantic import BaseModel

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


class SegmentTranslation(BaseModel):
    """คำแปล 1 segment ในภาษาของผู้ใช้ — สร้างโดย AI ฝั่ง client ระหว่างบทสนทนา.

    หลักการ: DB เก็บเฉพาะบาลี + อังกฤษ (แก่นต้นฉบับ) — คำแปลภาษาที่สามเป็นของ
    ชั่วคราวประจำบทสนทนา ไม่ persist. viewer แสดงบาลี+อังกฤษเหนือคำแปลเสมอ
    เพื่อให้ผู้ใช้ตรวจสอบได้ทุกบรรทัด.
    """

    segment_id: str
    text: str


def _to_viewer_payload(
    sutta: dict,
    target_segment_id: str | None,
    translations: list["SegmentTranslation"] | None = None,
    translation_language: str | None = None,
    translation_disclaimer: str | None = None,
    reader_base: str | None = None,
) -> dict:
    """แปลงผลจาก get_sutta(...) → shape ที่ UI ใช้: {ref,title,target_segment_id,
    segments:[{id,pali,en,tr?}], total, truncated, translation_language?, ...}."""
    segs_in = sutta.get("segments") or []
    truncated = False
    if target_segment_id is None and len(segs_in) > _VIEWER_MAX_SEGMENTS:
        segs_in = segs_in[:_VIEWER_MAX_SEGMENTS]
        truncated = True
    # คำแปลผูกกับ segment ที่แสดงจริงเท่านั้น — id แปลกถูกทิ้ง (รายงานผ่าน dropped)
    tr_map = {t.segment_id: t.text for t in (translations or [])}
    segments = []
    for s in segs_in:
        seg_id = s.get("segment_id", "")
        seg = {
            "id": seg_id,
            "pali": s.get("text_pali") or "",
            "en": s.get("text_english") or "",
        }
        if seg_id in tr_map:
            seg["tr"] = tr_map.pop(seg_id)
        segments.append(seg)
    # title อาจเป็น dict {pali,thai,english} หรือ str → ทำเป็น string เดียวให้ UI
    raw_title = sutta.get("title")
    if isinstance(raw_title, dict):
        parts = [raw_title.get("english"), raw_title.get("pali")]
        title = " · ".join(p for p in parts if p) or sutta.get("sutta_id", "")
    else:
        title = raw_title or sutta.get("sutta_id", "")
    payload = {
        "ref": sutta.get("sutta_id", ""),
        "title": title,
        "target_segment_id": target_segment_id,
        "segments": segments,
        "total": sutta.get("total_segments", len(segments)),
        "truncated": truncated,
    }
    # Two-Door ประตู B: ลิงก์ออกไป reader เต็มบนเบราว์เซอร์ (ปุ่มใน viewer header)
    if reader_base:
        sutta_id = sutta.get("sutta_id", "")
        payload["reader_url"] = f"{reader_base}/read/{sutta_id}" + (
            f"#{target_segment_id}" if target_segment_id else ""
        )
    if translation_language:
        payload["translation_language"] = translation_language
    if translation_disclaimer:
        payload["translation_disclaimer"] = translation_disclaimer
    if tr_map:
        # คำแปลที่ไม่ match segment ใดที่แสดง — บอกโมเดลให้รู้ว่าหล่นเพราะอะไร
        payload["translations_dropped"] = sorted(tr_map.keys())
    if not translations:
        # payload-level steering (บทเรียน: hint ใน result ที่โมเดลอ่านทันที >
        # docstring ที่อ่านผ่านตอน list tools) — จับ case โมเดลเรียก viewer
        # ก่อน get_sutta แล้วไม่มีข้อความให้แปล (พบจริง: Fable 5 + คำถามญี่ปุ่น)
        payload["translation_hint"] = (
            "The viewer is currently showing Pali + English only. If the "
            "user's conversation language is NOT English or Pali, translate "
            "the segments above (from the Pali, guided by the English) and "
            "call open_sutta_viewer AGAIN with the same selector plus "
            "translations=[{segment_id, text}, ...], translation_language "
            "(BCP-47), and a one-line translation_disclaimer in the user's "
            "language. The segments in this result give you the exact text "
            "to translate."
        )
    return payload


def register_mcp_app_ui(mcp, get_sutta, reader_base: str | None = None) -> list[str]:
    """ลงทะเบียน ui:// resource + entry-point tool. คืน list ชื่อสิ่งที่ register
    (ไว้ log/test). เรียกจาก main.py ต่อเมื่อ `mcp_app_enabled()` เป็น True.

    `get_sutta` = ฟังก์ชัน get_sutta จาก main (inject เพื่อเลี่ยง circular import).
    `reader_base` = base URL ของ bilingual reader (ปุ่ม "Open in reader" ใน viewer).
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
        translations: list[SegmentTranslation] | None = None,
        translation_language: str | None = None,
        translation_disclaimer: str | None = None,
    ) -> dict:
        """Open an interactive sutta viewer inside the chat — Pāli + English,
        plus an optional third row in the user's own language translated BY YOU.

        Renders each segment as: Pāli on top (canonical), the Bhikkhu Sujato
        English below it (verification anchor), and — when you supply
        `translations` — your translation in the user's language, clearly
        badged as AI-generated. Prefer this over dumping raw segments when the
        user wants to *read* a sutta.

        - `sutta_id` — standard SuttaCentral id, e.g. `sn56.11`, `mn10`, `dn22`.
        - `around` — a segment_id (e.g. `dn22:18.1`, from a search hit) to centre
          on; that segment is highlighted and scrolled into view. Use this after
          a search so the reader lands on the exact cited line.
        - `window` — segments before/after `around` to include (default 12).

        🌐 **Translating for the user (important):** when the conversation
        language is neither English nor Pāli, you SHOULD translate the displayed
        segments and pass them via `translations` so the user reads in their own
        language while still seeing the originals:
        1. Fetch the segments first (`get_sutta` with the same selector) so you
           have the exact Pāli + English text. (Already called this tool without
           translations? The result contains the segments — translate them and
           call this tool AGAIN with the same selector plus `translations` to
           upgrade the view.)
        2. Translate **from the Pāli as the source, using the English as a
           semantic guide** — never relay-translate from English alone. Preserve
           untranslatable doctrinal terms (dukkha, jhāna, taṇhā…) as loanwords
           with a brief gloss instead of forcing equivalents.
        3. Call this tool with `translations=[{segment_id, text}, ...]` covering
           ONLY the segments being displayed (never a whole long sutta),
           `translation_language` (BCP-47, e.g. "th", "es"), and
           `translation_disclaimer` — one short line IN THE USER'S LANGUAGE
           saying the translation is AI-generated in this conversation and
           should be checked against the Pāli/English above.
        Translations are conversation-ephemeral: nothing is stored server-side;
        the canon stays Pāli + English only. Translations whose segment_id is
        not in the displayed window are dropped (reported in
        `translations_dropped`).

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
        return _to_viewer_payload(
            sutta,
            target_segment_id=around,
            translations=translations,
            translation_language=translation_language,
            translation_disclaimer=translation_disclaimer,
            reader_base=reader_base,
        )

    registered.append("open_sutta_viewer")
    return registered
