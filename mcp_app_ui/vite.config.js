import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Build the viewer into ONE self-contained HTML file (JS/CSS inlined).
// `npm run build` then embeds it into ../mcp_app_viewer_html.py via embed.mjs.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // single-file output must not split or hash assets
    cssCodeSplit: false,
    // MCP App hosts are modern webviews — allow top-level await
    target: "esnext",
  },
});
