// Tipiṭaka sutta viewer — MCP App (renders inside the host's sandboxed iframe).
// Trilingual: Pāli (canonical, top) + Sujato English (verification anchor) +
// optional AI translation in the user's language (conversation-ephemeral,
// supplied by the client model via the `translations` tool param — the DB
// stays Pāli + English only). The originals are ALWAYS visible above the AI
// row so every line can be verified.
// The MCP Apps SDK is bundled at build time (vite + singlefile) — zero runtime
// network deps, works offline with the local SQLite install.
import { App } from "@modelcontextprotocol/ext-apps";

// static fallback sample — shown until the host pushes a real tool result
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
  ],
};

const state = {
  data: SAMPLE,
  view: "bi",        // "tri" | "bi" | "pali" | "en"
  app: null,
  loading: false,    // true while callServerTool load-more is in flight
};

function autonym(code) {
  if (!code) return "";
  try {
    return new Intl.DisplayNames([code], { type: "language" }).of(code) || code;
  } catch {
    return code;
  }
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function untranslatedRange(data) {
  const ids = (data.segments || []).filter((s) => !s.tr).map((s) => s.id);
  return ids.length ? { first: ids[0], last: ids[ids.length - 1], count: ids.length } : null;
}

function requestTranslation() {
  const d = state.data;
  const range = untranslatedRange(d);
  if (!range || !state.app) return;
  const lang = d.translation_language || "the user's language";
  const text =
    `Translate the sutta segments currently shown in the viewer ` +
    `(${d.ref}: ${range.first}..${range.last}) into ${lang}. ` +
    `Translate from the Pāli, using the English as a semantic guide, ` +
    `then call open_sutta_viewer again with the same selector and the ` +
    `translations, translation_language and a localized translation_disclaimer.`;
  state.app
    .sendMessage({ role: "user", content: [{ type: "text", text }] })
    .catch((e) => console.error("sendMessage failed:", e));
}

function renderChips() {
  const d = state.data;
  const box = document.getElementById("chips");
  box.innerHTML = "";
  const hasTr = (d.segments || []).some((s) => s.tr);
  const name = autonym(d.translation_language);
  const options = [];
  if (hasTr) options.push(["tri", `Pāḷi + EN + ${name || "AI"}`]);
  options.push(["bi", "Pāḷi + EN"], ["pali", "Pāḷi"], ["en", "EN"]);
  if (hasTr && state.view === "bi" && !state.userPickedView) state.view = "tri";
  for (const [key, label] of options) {
    const chip = el("button", "chip" + (state.view === key ? " on" : ""), label);
    chip.addEventListener("click", () => {
      state.view = key;
      state.userPickedView = true;
      renderAll();
    });
    box.appendChild(chip);
  }
}

function renderSegments() {
  const d = state.data;
  const target = d.target_segment_id || null;
  const box = document.getElementById("segments");
  box.innerHTML = "";
  const name = autonym(d.translation_language);
  let targetEl = null;
  for (const s of d.segments || []) {
    const div = el("div", "seg" + (s.id === target ? " target" : ""));
    div.appendChild(el("div", "sid", s.id || ""));
    if (state.view !== "en") div.appendChild(el("div", "pali", s.pali || ""));
    if (state.view !== "pali") div.appendChild(el("div", "en", s.en || ""));
    if (state.view === "tri") {
      if (s.tr) {
        const tr = el("div", "tr-row");
        tr.appendChild(el("span", "tr-badge", "AI " + (name || "")));
        tr.appendChild(el("div", "tr-text", s.tr));
        div.appendChild(tr);
      } else {
        const miss = el("div", "tr-missing");
        miss.appendChild(el("span", "tr-missing-label", "no translation yet"));
        const btn = el("button", "tr-btn", "Translate shown segments ↗");
        btn.addEventListener("click", requestTranslation);
        miss.appendChild(btn);
        div.appendChild(miss);
      }
    }
    box.appendChild(div);
    if (s.id === target) targetEl = div;
  }
  if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function loadMoreSegments() {
  if (state.loading || !state.app || state.data.next_offset == null) return;
  state.loading = true;
  renderAll(); // disable button immediately
  try {
    const result = await state.app.callServerTool({
      name: "open_sutta_viewer",
      arguments: { sutta_id: state.data.ref, offset: state.data.next_offset },
    });
    if (result && !result.isError) {
      renderResult(result);
    } else {
      setStatus("Could not load more segments.");
    }
  } catch (e) {
    console.error("callServerTool failed:", e);
    setStatus("Could not load more segments.");
  } finally {
    state.loading = false;
    renderAll();
  }
}

function renderFooter() {
  const d = state.data;
  const foot = document.getElementById("footer");
  const hasTr = (d.segments || []).some((s) => s.tr);
  foot.innerHTML = "";
  let hasContent = false;

  if (hasTr && state.view === "tri") {
    const disc = el("div", null,
      d.translation_disclaimer ||
      "AI-translated in this conversation — not an official translation. Verify against the Pāli and English above.");
    foot.appendChild(disc);
    hasContent = true;
  } else if (!hasTr && state.app) {
    // ไม่มีคำแปลเลย (โมเดลเรียก viewer แบบ bilingual) — ให้ผู้ใช้กดขอแปลเองได้
    const label = el("span", "tr-missing-label", "Reading in another language?");
    const btn = el("button", "tr-btn", "Translate to my language ↗");
    btn.addEventListener("click", requestTranslation);
    const wrap = el("div", "footer-translate");
    wrap.append(label, btn);
    foot.appendChild(wrap);
    hasContent = true;
  }

  if (d.next_offset != null && state.app) {
    const total = d.total || 0;
    const shown = (d.segments || []).length;
    const label = el("span", "tr-missing-label",
      `Showing ${shown} of ${total} segments.`);
    const btn = el("button", "tr-btn",
      state.loading ? "Loading…" : "Load more ↓");
    if (state.loading) btn.disabled = true;
    btn.addEventListener("click", loadMoreSegments);
    const wrap = el("div", "footer-translate");
    wrap.append(label, btn);
    foot.appendChild(wrap);
    hasContent = true;
  }

  foot.style.display = hasContent ? "" : "none";
}

function renderHeaderActions() {
  const box = document.getElementById("header-actions");
  box.innerHTML = "";
  const url = state.data.reader_url;
  if (!url || !state.app) return;
  // Two-Door ประตู B: ออกไป reader เต็มบนเบราว์เซอร์ — host เด้ง dialog
  // ยืนยันก่อนเปิดลิงก์เอง (พฤติกรรม built-in ของ openLink)
  const btn = el("button", "tr-btn", "Open in reader ↗");
  btn.title = url;
  btn.addEventListener("click", () => {
    state.app.openLink({ url }).catch((e) => console.error("openLink failed:", e));
  });
  box.appendChild(btn);
}

function renderAll() {
  const d = state.data;
  document.getElementById("ref").textContent = d.ref || "";
  document.getElementById("title").textContent = d.title || "";
  renderHeaderActions();
  renderChips();
  renderSegments();
  renderFooter();
}

function renderResult(result) {
  // tool result arrives as { structuredContent: {...} } (FastMCP dict return)
  // or directly as the data dict (callServerTool direct call)
  const data = (result && result.structuredContent) || result || {};
  if (!data.segments) {
    if (data.error || data.message) setStatus("Server: " + (data.error || data.message));
    state.loading = false;
    return;
  }

  // Append mode: same sutta, offset > 0 (viewer-initiated load-more)
  const isAppend = (data.offset > 0) && state.data && (data.ref === state.data.ref);
  if (isAppend) {
    state.data = {
      ...state.data,
      segments: [...state.data.segments, ...data.segments],
      next_offset: data.next_offset,
      truncated: data.next_offset != null,
    };
    state.loading = false;
    renderAll();
    const total = state.data.total || 0;
    const shown = state.data.segments.length;
    setStatus(`Loaded ${shown}${total > shown ? "/" + total : ""} segments.`);
    return;
  }

  // Replace mode: new sutta or offset=0
  state.data = data;
  state.loading = false;
  state.userPickedView = false;
  state.view = data.segments.some((s) => s.tr) ? "tri" : "bi";
  renderAll();
  const trCount = data.segments.filter((s) => s.tr).length;
  const shown = data.segments.length;
  const total = data.total || shown;
  setStatus(
    `Rendered ${shown}${total > shown ? "/" + total : ""} segments` +
    (trCount ? ` (${trCount} translated)` : "") + "."
  );
}

renderAll();
setStatus("Connecting to host…");

try {
  const app = new App({ name: "Tipiṭaka Sutta Viewer", version: "0.2.0" });
  state.app = app;
  app.ontoolresult = (result) => renderResult(result);
  app.onerror = (e) => console.error("MCP App error:", e);
  await app.connect();
  setStatus("Connected — call open_sutta_viewer to load a sutta.");
} catch (e) {
  console.error("MCP Apps SDK connect failed:", e);
  setStatus("Showing sample (no MCP host detected).");
}
