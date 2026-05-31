# Getting Started — Tripitaka MCP

A practical guide for AI clients (Claude Desktop, Cline, Cursor, etc.) and humans who want to query the Pāli Canon through this MCP server. If you're an installer agent, see [`/llms-install.md`](https://github.com/dhamma-seeker/tripitaka-mcp/blob/main/llms-install.md) instead.

## What this server does

The Tripitaka MCP server exposes **11 tools and 3 resources** giving an AI assistant first-class access to the Pāli Tipiṭaka — the foundational scripture of Theravāda Buddhism. The corpus loaded here is at parity with [SuttaCentral's bilara-data](https://github.com/suttacentral/bilara-data):

- **Sutta Piṭaka** (~284K segments) — Pāli + Bhikkhu Sujato English
- **Vinaya Piṭaka** (~71K segments) — Pāli + Bhikkhu Brahmali English
- **Abhidhamma Piṭaka** (~88K segments) — Pāli only (bilara has no English)

Total: ~444,000 segments, all searchable via trigram + vector hybrid, all retrievable in full, all linked back to canonical sources for verification.

## Connect

| You're using | Path |
| --- | --- |
| Claude Desktop / Cline / Cursor / Continue.dev | Add an `mcpServers` entry pointing at the hosted endpoint — see the [README's "No setup" section](https://github.com/dhamma-seeker/tripitaka-mcp#-no-setup--connect-to-the-public-dhamma-dāna-server) |
| Other MCP-capable client | Endpoint: `https://mcp.tripitaka-mcp.com/mcp` (Streamable HTTP, MCP spec 2025-03-26) or `https://mcp.tripitaka-mcp.com/sse` (legacy SSE) |
| Local install (offline) | `git clone` + `./scripts/install.sh` — see [README](https://github.com/dhamma-seeker/tripitaka-mcp#-fastest-local-path--use-the-installer-recommended-for-non-developers) |

The hosted instance is rate-limited (10 req/10s + 60 req/min per IP) and offered as Dhamma Dāna — free, non-commercial use only.

## Choosing the right tool

Tools are gated by question shape, not topic. Match what the user is asking against the table below.

| Question shape | Tool | Why |
| --- | --- | --- |
| "How many times does X appear / every place it's mentioned — exhaustive, don't miss any" | `survey_corpus` | Exact total + per-pitaka breakdown + matched word-forms; `mode=thorough` adds concept-level recall |
| "Best few passages for a word / quick lookup" | `search_by_keyword` | Trigram match — ranked top results for canonical Pāli terms (`appamāda`, `ānāpānassati`) |
| "Which suttas teach concept Z / discourses about X?" | `search_hybrid` | Combined keyword + semantic via RRF — best for concept landscape |
| "Show me sutta X in full / quote it" | `get_sutta` | Returns every segment with cross-reference URLs |
| "Compare translations of segment X" | `compare_translations` | Side-by-side renderings across editions |
| "Generate a citation for sutta X" | `get_reference` | Properly formatted academic citation + source URLs |
| "What does Pāli word X mean?" | `get_word_definition` | Looks up in P. A. Payutto's Thai Buddhist dictionary, PTS, DPPN |
| "Decompose this Pāli compound / inflected form" | `parse_pali_word` | Strips suffixes to recover the root form (`bhikkhūnaṁ` → `bhikkhu`) |
| "What's the structure of the canon / what's loaded?" | `list_structure` | Tipiṭaka tree with live segment counts |
| "Which translation editions exist?" | `list_editions` | Lists all loaded editions per language |

`search_semantic` is also exposed but rarely the best choice on its own — `search_hybrid` (which includes semantic ranking) is almost always preferred.

## Prompt patterns that work well

These come from real Claude Desktop sessions and are the same patterns the bundled [`tipitaka-research`](https://github.com/dhamma-seeker/tripitaka-mcp/blob/main/skills/tipitaka-research.md) skill enforces.

### Verify before claiming

The Pāli Canon is a **closed, verifiable corpus**. Don't recite from training memory — call the tool, quote the actual segment, surface the cross-reference URL. If a recalled fact contradicts a tool result, trust the tool.

### Translate the user's query to canonical Pāli first

If the user asks about *"การเจริญเมตตา"* or *"loving-kindness meditation,"* translate to canonical Pāli (`mettābhāvanā`) **before** calling `search_by_keyword`. The corpus is indexed in Pāli; matching English or Thai keywords against the index will miss the actual content.

### Surface URLs by user language

Every tool response includes a `cross_reference` block with deep links:

- For Thai users → emphasize `cross_reference.tipitaka_84000.url` (ฉบับมหาจุฬาฯ on 84000.org) as the primary citation, SuttaCentral as secondary
- For English users → emphasize `cross_reference.suttacentral.english_url` as primary
- Always include `segment_url` (deep link to the specific verse) when quoting a passage

### Use `limit` deliberately

Default `limit=10` is often too low for surveys. For "list all suttas about X" queries, set `limit=20` for hybrid search (its max) or `limit=30-50` for keyword surveys.

### Be honest about gaps

When the corpus or your understanding is incomplete, say so. Distinguish:

- **In this server**: all three piṭakas at SuttaCentral parity (Pāli + Sujato/Brahmali English; no Abhidhamma English because bilara has none)
- **Not in this server**: Atthakathā (commentaries), Mahāvaṃsa, Sri Lankan chronicles, Visuddhimagga, modern reinterpretations

## Worked example — "What does the Buddha teach about mindfulness of breathing?"

A capable agent's flow:

1. **Translate**: "mindfulness of breathing" → `ānāpānassati` (Pāli)
2. **Survey**: `search_hybrid(query="mindfulness of breathing", limit=20)` to find the concept landscape
3. **Drill**: Pick the locus classicus (likely **MN 118 Ānāpānassati Sutta**) → `get_sutta(sutta_id="mn118", language="all")`
4. **Quote**: Lift specific segments verbatim — quote the Pāli, the English, surface `segment_url`
5. **Cross-reference**: Note the parallel teaching in **DN 22** (`ānāpānapabba` section of the Mahāsatipaṭṭhāna Sutta) and **SN 54** (the dedicated Saṁyutta on breathing)
6. **Caveat**: Note that the literal word `ānāpāna` appears mainly in section markers; the body of teaching uses `assasati` / `passasati` / `dīghaṁ` / `rassaṁ` — so a keyword search for "ānāpāna" alone will miss most teaching content

That's the level of grounding scholarly content needs.

## Anti-patterns to avoid

- ❌ Reciting sutta content from memory without calling `get_sutta`
- ❌ Claiming a sutta exists without a verifiable URL
- ❌ Translating Pāli loosely when the corpus has Bhikkhu Sujato's published translation — use `text_english` from the tool
- ❌ Promising "every X" — the corpus is too large; offer tiered scope instead
- ❌ Surfacing URLs as plain text — use markdown `[text](url)` so clients render clickables

## Other reference pages

- [tipitaka-overview.md](tipitaka-overview.md) — Canon structure, segment counts, three piṭakas
- [places.md](places.md) — Locations across the suttas, by Mahājanapada and sacred sites
- People (planned) — Chief disciples, lay supporters, kings, opponents
- Themes (planned) — Major teachings (Four Noble Truths, Eightfold Path, Dependent Origination) with locus classicus

## License

Dhamma Dāna — free to use, share, and adapt for non-commercial purposes. Source data licenses vary; see the project [NOTICE.md](https://github.com/dhamma-seeker/tripitaka-mcp/blob/main/NOTICE.md) before redistributing.
