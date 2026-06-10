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
# Self-contained HTML (inline CSS/JS — ไม่พึ่ง external origin → CSP สะอาด)
#
# QW0: render ตัวอย่าง bilingual แบบ static + ติดตั้ง postMessage listener ที่
# จะ render segment จริงเมื่อ host ส่ง tool result มา (scaffold สำหรับ QW1).
# ──────────────────────────────────────────────────────────────────────────
_SUTTA_VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tipiṭaka — Sutta Viewer</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 16px;
    font: 15px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: transparent;
  }
  .header { margin-bottom: 12px; }
  .header .ref { font-size: 13px; opacity: 0.6; letter-spacing: 0.03em; }
  .header .title { font-size: 18px; font-weight: 600; margin-top: 2px; }
  .seg {
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    padding: 8px 10px; border-radius: 8px;
    border-left: 3px solid transparent;
  }
  .seg + .seg { margin-top: 2px; }
  .seg:hover { background: rgba(127,127,127,0.07); }
  .seg.target {
    background: rgba(214,158,46,0.14);
    border-left-color: #d69e2e;
  }
  .pali { font-style: italic; }
  .en { opacity: 0.92; }
  .seg .sid { grid-column: 1 / -1; font-size: 11px; opacity: 0.4; margin-bottom: 2px; }
  @media (max-width: 560px) { .seg { grid-template-columns: 1fr; gap: 4px; } }
  .poc-note {
    margin-top: 16px; padding: 8px 12px; border-radius: 8px;
    background: rgba(127,127,127,0.08); font-size: 12px; opacity: 0.7;
  }
</style>
</head>
<body>
  <div class="header">
    <div class="ref" id="ref">SN 56.11</div>
    <div class="title" id="title">Dhammacakkappavattana Sutta · Setting in Motion the Wheel of Dhamma</div>
  </div>
  <div id="segments"></div>
  <div class="poc-note" id="status">QW0 PoC — static sample. Waiting for tool data via postMessage…</div>

<script>
  // ── static fallback sample (QW0 proof-of-render) ──────────────────────
  const SAMPLE = {
    ref: "SN 56.11",
    title: "Dhammacakkappavattana Sutta · Setting in Motion the Wheel of Dhamma",
    target_segment_id: "sn56.11:3.1",
    segments: [
      { id: "sn56.11:1.1", pali: "Evaṁ me sutaṁ—", en: "So I have heard." },
      { id: "sn56.11:2.1",
        pali: "ekaṁ samayaṁ bhagavā bārāṇasiyaṁ viharati isipatane migadāye.",
        en: "At one time the Buddha was staying near Varanasi, in the deer park at Isipatana." },
      { id: "sn56.11:3.1",
        pali: "Dveme, bhikkhave, antā pabbajitena na sevitabbā.",
        en: "There are these two extremes that one gone forth should not cultivate." },
      { id: "sn56.11:3.2",
        pali: "Yo cāyaṁ kāmesu kāmasukhallikānuyogo hīno gammo pothujjaniko anariyo anatthasaṁhito,",
        en: "Indulgence in sensual pleasures, which is low, crude, ordinary, ignoble, and pointless;" },
      { id: "sn56.11:3.3",
        pali: "yo cāyaṁ attakilamathānuyogo dukkho anariyo anatthasaṁhito.",
        en: "and indulgence in self-mortification, which is painful, ignoble, and pointless." },
    ],
  };

  function render(data) {
    const ref = data.ref || "";
    const title = data.title || "";
    const target = data.target_segment_id || null;
    const segs = data.segments || [];
    document.getElementById("ref").textContent = ref;
    document.getElementById("title").textContent = title;
    const box = document.getElementById("segments");
    box.innerHTML = "";
    let targetEl = null;
    for (const s of segs) {
      const div = document.createElement("div");
      div.className = "seg" + (s.id === target ? " target" : "");
      div.innerHTML =
        '<div class="sid">' + (s.id || "") + '</div>' +
        '<div class="pali">' + (s.pali || "") + '</div>' +
        '<div class="en">' + (s.en || "") + '</div>';
      box.appendChild(div);
      if (s.id === target) targetEl = div;
    }
    if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  // setStatus (NOT `status` — that collides with the legacy window.status property)
  window.setStatus = function (msg) {
    document.getElementById("status").textContent = msg;
  };

  window.renderResult = function (result) {
    // tool result arrives as { structuredContent: {...} } (FastMCP dict return)
    const data = (result && result.structuredContent) || result || {};
    if (!data.segments) {
      if (data.error || data.message) window.setStatus("Server: " + (data.error || data.message));
      return;
    }
    render(data);
    window.setStatus(
      "Rendered " + data.segments.length + " segments" +
      (data.truncated ? " (truncated — long sutta)" : "") + "."
    );
  };

  // render static sample immediately so the iframe is never blank
  render(SAMPLE);
  window.setStatus("Connecting to host…");
</script>

<!-- MCP Apps SDK — receives the tool result from the host and re-renders.
     Loaded from esm.sh (allowed via the resource CSP).
     NOTE: must be the `/app-with-deps` entry — the bare entry resolves zod v4
     through esm.sh to a broken module ("t.custom is not a function") and the
     import dies. Dynamic import keeps that failure catchable. -->
<script type="module">
  try {
    const { App } = await import(
      "https://esm.sh/@modelcontextprotocol/ext-apps@1.7.3/app-with-deps"
    );
    const app = new App({ name: "Tipiṭaka Sutta Viewer", version: "0.1.0" });
    app.ontoolresult = (result) => window.renderResult(result);
    app.onerror = (e) => console.error("MCP App error:", e);
    await app.connect();
    window.setStatus("Connected — call open_sutta_viewer to load a sutta.");
  } catch (e) {
    console.error("MCP Apps SDK failed to load:", e);
    window.setStatus("Showing sample (host SDK unavailable in this preview).");
  }
</script>
</body>
</html>
"""


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
    from fastmcp.apps import AppConfig, ResourceCSP
    from fastmcp.utilities.mime import UI_MIME_TYPE

    registered: list[str] = []

    @mcp.resource(
        UI_SUTTA_VIEWER,
        name="Tipiṭaka sutta viewer",
        description="Inline bilingual (Pāli + English) sutta reader rendered in-chat.",
        mime_type=UI_MIME_TYPE,
        # CSP: viewer โหลด MCP Apps SDK จาก esm.sh เพื่อรับ tool result จาก host.
        app=AppConfig(
            csp=ResourceCSP(
                resource_domains=["https://esm.sh"],
                connect_domains=["https://esm.sh"],
            )
        ),
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
