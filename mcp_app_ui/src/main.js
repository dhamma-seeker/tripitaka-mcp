// Tipiṭaka sutta viewer — MCP App (renders inside the host's sandboxed iframe).
// The MCP Apps SDK is bundled at build time (vite + singlefile) so the viewer
// has ZERO runtime network dependencies — works offline with the local
// SQLite install, no esm.sh/CDN.
import { App } from "@modelcontextprotocol/ext-apps";

// static fallback sample — shown until the host pushes a real tool result,
// so the iframe is never blank (e.g. in previews without a connected host)
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

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

function render(data) {
  const target = data.target_segment_id || null;
  document.getElementById("ref").textContent = data.ref || "";
  document.getElementById("title").textContent = data.title || "";
  const box = document.getElementById("segments");
  box.innerHTML = "";
  let targetEl = null;
  for (const s of data.segments || []) {
    const div = document.createElement("div");
    div.className = "seg" + (s.id === target ? " target" : "");
    const sid = document.createElement("div");
    sid.className = "sid";
    sid.textContent = s.id || "";
    const pali = document.createElement("div");
    pali.className = "pali";
    pali.textContent = s.pali || "";
    const en = document.createElement("div");
    en.className = "en";
    en.textContent = s.en || "";
    div.append(sid, pali, en);
    box.appendChild(div);
    if (s.id === target) targetEl = div;
  }
  if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
}

function renderResult(result) {
  // tool result arrives as { structuredContent: {...} } (FastMCP dict return)
  const data = (result && result.structuredContent) || result || {};
  if (!data.segments) {
    if (data.error || data.message) setStatus("Server: " + (data.error || data.message));
    return;
  }
  render(data);
  setStatus(
    "Rendered " + data.segments.length + " segments" +
    (data.truncated ? " (truncated — long sutta)" : "") + "."
  );
}

// render the sample immediately so the iframe is never blank
render(SAMPLE);
setStatus("Connecting to host…");

try {
  const app = new App({ name: "Tipiṭaka Sutta Viewer", version: "0.1.0" });
  app.ontoolresult = (result) => renderResult(result);
  app.onerror = (e) => console.error("MCP App error:", e);
  await app.connect();
  setStatus("Connected — call open_sutta_viewer to load a sutta.");
} catch (e) {
  console.error("MCP Apps SDK connect failed:", e);
  setStatus("Showing sample (no MCP host detected).");
}
