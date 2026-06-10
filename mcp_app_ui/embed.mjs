// Post-build: embed dist/index.html into ../mcp_app_viewer_html.py as a
// Python string constant. The generated module is committed, so runtime and
// packaging need no data files and no node — `pip install .` just works.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "dist", "index.html"), "utf8");

// Escape only what a Python triple-double-quoted string can't hold verbatim.
const escaped = html.replaceAll("\\", "\\\\").replaceAll('"""', '\\"\\"\\"');

const py = `"""GENERATED FILE — do not edit by hand.

Built from mcp_app_ui/ (vite + vite-plugin-singlefile bundles the MCP Apps
SDK inline → no CDN/network needed at runtime, offline-capable).
Rebuild with:  cd mcp_app_ui && npm install && npm run build
"""

VIEWER_HTML = """${escaped}"""
`;

const out = join(here, "..", "mcp_app_viewer_html.py");
writeFileSync(out, py);
console.log(`wrote ${out} (${html.length} bytes of HTML)`);
