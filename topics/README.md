# Tripiṭaka Topic Pages

Curated reference pages compiled from the Pāli Canon (Tipiṭaka) — served as static markdown so AI clients can cite them, search engines can index them, and humans can browse them without round-tripping through the MCP server.

The MCP server at `/mcp` is the dynamic interface; the pages here are the **distilled cache**: things AI agents would otherwise need to compile by running 30+ tool calls every time, captured once for everyone.

## Available pages

| Page | What it covers | Status |
| --- | --- | --- |
| [tipitaka-overview.md](tipitaka-overview.md) | Structure of the Pāli Canon — pitakas, nikāyas, sub-books, segment counts | ready |
| [getting-started.md](getting-started.md) | How to connect, choose the right tool, prompt patterns, anti-patterns | ready |
| [places.md](places.md) | Locations mentioned across the suttas — by Mahājanapada, sacred sites, cosmological realms | ready (~main loci covered) |
| people.md | (planned) Chief disciples, lay supporters, kings, opponents — by role | tbd |
| [themes.md](themes.md) | Locus classicus + parallel suttas for 10 foundational teachings — 4 Noble Truths, 3 Marks, Dependent Origination, 5 Aggregates, Eightfold Path, Satipaṭṭhāna, Ānāpānassati, Mettā, Hindrances, Awakening Factors | ready |

## Why these exist

Real Claude Desktop sessions tend to compile the same artifacts repeatedly: places lists, sutta surveys by topic, biographies of major disciples. Each compile costs ~30 tool calls and rediscovers the same scholarly framing. By publishing the curated artifacts here:

- AI clients can pull the full page in one fetch (`https://mcp.tripitaka-mcp.com/topics/places.md`)
- Search engines index real content, not just a homepage — improves discoverability
- The work scholars do once benefits every later user
- Updates (new translations, new data, corrected facts) are version-controlled in git

## Contributing

Pages here are markdown only — no build step, no JS, no HTML. To add or improve a page:

1. Edit the file in `topics/` in the repo
2. Verify links work (cross-references should be either relative `[other.md](other.md)` or full URLs)
3. Open a PR; on merge the file is served live within minutes

Every fact on a page should be **citable** — link the SuttaCentral URL of any sutta you reference, and note the source for any external claim (Malalasekera, Bhikkhu Bodhi, archaeology, etc.). The conventions match the [`tipitaka-research`](../skills/tipitaka-research.md) skill that AI clients use.

## License

Content here is dhamma-dāna — free to use, share, and adapt for non-commercial purposes. The underlying Pāli text and Sujato translations are CC0 (SuttaCentral bilara-data). Where Thai or other commentary content is included, attribution and license terms are noted on the relevant page.
