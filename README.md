# Tripitaka MCP Server

<p align="center">
  <img src="https://tripitaka-mcp.com/favicon-192.png" alt="Tripitaka MCP logo: folded hands over a dhammacakka in pixel art" width="160" height="160">
</p>

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![MCP Spec](https://img.shields.io/badge/MCP-2025--03--26-8b6914)](https://spec.modelcontextprotocol.io/)
[![Coverage](https://img.shields.io/badge/Tipi%E1%B9%ADaka-%7E444K%20segments-8b6914)](https://tripitaka-mcp.com/)
[![Hosted](https://img.shields.io/badge/hosted-tripitaka--mcp.com-8b6914)](https://tripitaka-mcp.com/)
[![Dhamma Dāna](https://img.shields.io/badge/offered%20as-Dhamma%20D%C4%81na-8b6914?labelColor=fafaf7&color=8b6914)](./NOTICE.md)
[![Glama](https://glama.ai/mcp/servers/dhamma-seeker/tripitaka-mcp/badges/score.svg)](https://glama.ai/mcp/servers/dhamma-seeker/tripitaka-mcp)
[![Smithery](https://smithery.ai/badge/dhamma-seeker/tripitaka-mcp)](https://smithery.ai/server/dhamma-seeker/tripitaka-mcp)

An MCP server for searching and citing content from the Pāli Tipiṭaka.
It lets AI clients such as Claude or Cursor look up suttas, quote the teachings, and compare translations across languages.

> 🙏 **This project is offered as Dhamma Dāna:** 100% free, non-commercial only.
> License details: [LICENSE](./LICENSE) (code) and [NOTICE.md](./NOTICE.md) (data)

## ✨ Features

- **Full Tipiṭaka coverage, at parity with SuttaCentral.** All three baskets are indexed, about 444K segments. Sutta carries Pāli plus English from `bilara-data`'s translators (Bhikkhu Sujato for DN/MN/SN/AN and most of the Khuddaka Nikāya, with John Kelly, Bhikkhu Kovilo and others for a few KN books). Vinaya carries Pāli plus Bhikkhu Brahmali's English. Abhidhamma is Pāli only, because upstream `bilara-data` has no English for any Abhidhamma book. `list_structure` reports live counts.
- **Hybrid search** merges keyword and semantic results through Reciprocal Rank Fusion (RRF). It is the most precise of the search tools and needs no configuration.
- **Keyword search** with trigram fuzzy matching and cross-language alignment.
- **Semantic search** by meaning, using vector similarity (pgvector).
- **Translation comparison** across editions, aligned segment by segment.
- **Dictionary bridge** with 20,000+ entries (P. A. Payutto, PTS, DPPN).
- **Sutta fetch and citations.** Get a sutta by ID (`mn1`, `pli-tv-bu-vb-pj1`, `patthana1.1`) and generate a properly formatted academic citation.
- **Pāli word analyzer** that strips inflectional suffixes to find the root form when a dictionary lookup misses (`bhikkhūnaṁ` → `bhikkhu`).
- **Cross-reference URLs in every response:** a clickable deep link into the project's own bilingual reader (Pāli + English, with a segment anchor that highlights the cited verse). The reader renders SuttaCentral's `bilara-data` verbatim, so it is the authoritative text, and AI clients surface the link so users can verify the source in one click.
- **Dual transport:** legacy SSE (`/sse`) and canonical Streamable HTTP (`/mcp`, MCP spec 2025-03-26).
- **MCP resources:** `tripitaka://structure`, `tripitaka://sutta/{id}`, `tripitaka://word/{w}`, for clients that pin context as resources.
- **Curated reference pages** at [`/topics/*`](https://mcp.tripitaka-mcp.com/topics/): six markdown pages covering canon structure, getting started and tool selection, places (Mahājanapada, holy sites, cosmology), 10 foundational themes with locus classicus, about 30 major figures, and a phase-based timeline of the Buddha's 45-year mission. Sutta IDs are verified against live data, and an AI client can fetch one page instead of running 30+ tool calls.
- **Claude skill.** `skills/tipitaka-research.md` is a ready-to-install workflow file that turns on a multi-step research pattern (clarify → verify coverage → search → drill in → cite) on Claude Desktop and Claude Code.
- **Postman collection** included for testing the API.

## 🏗️ Tech stack

| Technology | Role |
|---|---|
| Python + FastMCP | MCP Server |
| PostgreSQL + pgvector | Database + Vector Search |
| sentence-transformers | Embeddings for semantic search |
| Docker Compose | Infrastructure |

## 🚀 Quick start

### 🌐 No setup: connect to the public Dhamma Dāna server

The maintainers run a free public instance at [tripitaka-mcp.com](https://tripitaka-mcp.com).

| Endpoint | Use |
|---|---|
| `https://mcp.tripitaka-mcp.com/mcp` | Streamable HTTP (MCP spec 2025-03-26) |
| `https://mcp.tripitaka-mcp.com/sse` | Legacy SSE (older clients) |

Connecting Claude Desktop takes three steps. Nothing to install but [Node.js](https://nodejs.org/), and no Docker or GPU.

**1.** Find your absolute `npx` path. Claude Desktop doesn't read your shell profile, so a bare `npx` won't resolve. Open a terminal:

```bash
which npx
# example: /Users/you/.nvm/versions/node/v22.14.0/bin/npx
```

**2.** Open `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows) and add the entry below. Substitute `YOUR_NPX_PATH` with the output from step 1, and `YOUR_NODE_BIN_DIR` with that path's parent directory:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "YOUR_NPX_PATH",
      "args": ["-y", "mcp-remote", "https://mcp.tripitaka-mcp.com/mcp"],
      "env": { "PATH": "YOUR_NODE_BIN_DIR:/usr/local/bin:/usr/bin:/bin" }
    }
  }
}
```

**3.** Quit Claude Desktop completely (`⌘Q` on macOS, tray → Quit on Windows) and reopen. The 🔌 indicator in the bottom-left should show `tripitaka` with 14 tools available.

> _The first connection takes 5 to 10 seconds_ while `npx` downloads `mcp-remote` on demand. Give Claude Desktop a moment after the restart before deciding it failed.

Once connected, try asking Claude things like:

- "What does the Buddha teach about mindfulness of breathing? Quote the relevant passages from MN 118."
- "Show me the full text of the Karaṇīyamettasutta in Pāli and English."
- "What does the Pāli word _sati_ mean according to the Payutto dictionary?"
- "Find suttas where the Buddha discusses anger."

Claude will pick the right tool, fetch the canonical Pāli, and surface a clickable link to the project's bilingual reader for verification.

The hosted server is a small free service offered for personal study, research, and dhamma practice. Keep your request rate reasonable; bursts may be throttled at the edge. Read [NOTICE.md](./NOTICE.md) before redistributing it or using it commercially.

### 💻 Run it fully offline (`pipx`, local SQLite, no server)

If you would rather keep everything on your own machine, with no network calls to the hosted server, install the local edition. It carries the whole Pāli canon as a single SQLite file (~120 MB) and runs as a local stdio MCP server.

```bash
pipx install tripitaka-mcp     # needs Python 3.10+
tripitaka-mcp init             # one-time: downloads the SQLite database
tripitaka-mcp serve            # runs the MCP server over stdio
```

**If the install fails like this:**

```
Because the current Python version (3.9.6) does not satisfy Python>=3.10
```

pipx is using a different interpreter than you think. It builds its own
isolated environment on purpose and ignores whatever venv you have active, so
an old system Python gets picked even when the shell you typed in has 3.12.
Tell it which to use:

```bash
pipx install --python python3.12 tripitaka-mcp
```

(Any 3.10 or newer works; `pipx environment` shows what it defaults to.)

Then point Claude Desktop or Cursor at the local command, with no `npx` bridge and no internet:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "tripitaka-mcp",
      "args": ["serve"]
    }
  }
}
```

(If `tripitaka-mcp` isn't on the client's `PATH`, use the absolute path from `which tripitaka-mcp`.)

**Need a URL instead of stdio?** Scripts, notebooks, and anything that shares
one server across several clients want an HTTP endpoint rather than a
subprocess:

```bash
tripitaka-mcp serve --http                 # http://127.0.0.1:8765/mcp
tripitaka-mcp serve --http --port 9000     # or MCP_HOST / MCP_PORT
```

It binds `127.0.0.1` unless you say otherwise; the canon is read-only, but
nothing here asks who is calling, so think before binding a public interface.

**Hosted vs local**

Both serve the same ~444K-segment canon. The differences:

| | Hosted (`mcp.tripitaka-mcp.com`) | Local (`pipx`) |
|---|---|---|
| Tools | all 14 | 11, or 12 with `TRIPITAKA_MCP_APP=1`; no `search_semantic` or `search_hybrid` |
| Concept / semantic search | ✅ vector search (pgvector) | ❌ use `search_by_keyword` instead |
| Keyword search | PostgreSQL trigram: fuzzy, typo tolerant, similarity ranked | SQLite FTS5: whole-word / token match, so **results and ranking can differ** from hosted |
| Canon data | always current | a snapshot from when you ran `init`; re-run `tripitaka-mcp init` to refresh |
| Updates | automatic | `pipx upgrade tripitaka-mcp` for code; re-run `init` for data |
| Privacy | queries reach the hosted server (nothing logged, see the [Privacy Policy](https://tripitaka-mcp.com/privacy/)) | nothing leaves your machine |
| Internet | required | not needed after `init` |
| Rate limit | bursts may be throttled at the edge | none |
| Setup | zero / one-click | Python 3.10+, pipx, one-time ~120 MB download |

`search_semantic`, `search_hybrid`, and the trigram keyword index need PostgreSQL, pgvector, and a ~1 GB embedding model, which is more than a lightweight local install should carry, so they stay hosted-only. In local mode those two tools are never registered: a connected client sees only the 11 it can actually call.

Because the local server is a standard stdio MCP server, it also gives you a fully offline AI stack. Pair it with a local model such as Ollama and any MCP-capable chat UI, and nothing leaves your machine.

### 🏎️ Fastest local path: the installer (recommended for non-developers)

```bash
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git
cd tripitaka-mcp
./scripts/install.sh
```

The installer downloads a prepared database dump from Hugging Face ([dhamma-seeker/tripitaka-mcp-dump](https://huggingface.co/datasets/dhamma-seeker/tripitaka-mcp-dump)) and restores it for you, which brings setup down from two to four hours (loading the data, then generating embeddings) to about five minutes.
(If a dump file is already on disk, the installer uses that copy instead.)

The installer will:

1. Verify that `docker`, `compose`, `openssl`, and `curl` are installed
2. Generate `.env` with random passwords (for both the admin and the readonly user)
3. Download the dump from Hugging Face (if not already local)
4. Start the DB and restore the dump
5. Set up the readonly role and runtime timeouts
6. Print a ready-to-paste Claude Desktop config

Options:

```bash
./scripts/install.sh --dump PATH          # use an existing dump file
./scripts/install.sh --dump-url URL       # override the dump source
./scripts/install.sh --no-dump            # skip restore (load data yourself later)
```

---

### 🔧 Manual setup (for developers)

#### 1. Clone & setup

```bash
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git
cd tripitaka-mcp
cp .env.example .env
# Set POSTGRES_PASSWORD in .env to a random password
```

#### 2. Start database

```bash
docker compose up db -d
```

#### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Initialize database & load data

```bash
# 1. Seed metadata (pitaka, nikāya)
python scripts/seed_metadata.py

# 2. Download & load Sutta Piṭaka data from SuttaCentral
python scripts/data_loader.py

# 3. Load Thai CC0 translations (Dhīranando & Jayasāro)
python scripts/load_thai_cc0.py

# 4. Load dictionaries (DPD, PTS, DPPN, and the Payutto dictionary)
python scripts/load_dictionary.py

# 5. Generate embeddings for semantic / hybrid search
python scripts/generate_embeddings.py
```

#### 5. Run MCP server

```bash
python main.py
```

### 🧪 Testing with Postman

You can drive the tools from Postman in SSE mode:

1. Run the server with: `MCP_TRANSPORT=sse python main.py`
2. Import [postman_collection.json](./postman_collection.json) into Postman
3. Invoke the tools directly

## 🚢 Production deployment

For production, restore from a database dump instead of re-loading the data and re-running the embedding model.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The production stack runs 5 services:

- `db`: PostgreSQL + pgvector (internal only, no exposed port)
- `mcp-server`: FastMCP over legacy SSE, behind `/sse` (readonly DB user, read-only FS, `cap_drop: ALL`)
- `mcp-server-http`: the same server over Streamable HTTP, behind `/mcp`
- `reader`: the bilingual reader that every cross-reference URL points at, behind `/read/*`
- `caddy`: reverse proxy and Let's Encrypt. Its `rate_limit` block for the MCP site is declared but
  does not run as written, which [DEPLOYMENT.md](./DEPLOYMENT.md) explains

For another layer of hardening, put Cloudflare in front of Caddy (DNS proxy, rate-limit rules, and DDoS protection on the free tier).

Full details are in [DEPLOYMENT.md](./DEPLOYMENT.md).

## 🔧 Connecting to Claude Desktop

The repo ships [`claude_desktop_config.example.json`](./claude_desktop_config.example.json) with three ready-to-use entries. Copy whichever fits your setup into `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows), then edit the absolute paths:

| Entry | When to use | Transport |
|---|---|---|
| `tripitaka-local` | You ran the installer locally on the same machine as Claude Desktop | stdio (no network) |
| `tripitaka-remote` | You self-hosted the server on a VPS and want the modern transport | Streamable HTTP (`/mcp`) |
| `tripitaka-remote-sse` | Your client doesn't support Streamable HTTP yet | Legacy SSE (`/sse`) |

The remote entries route through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), a bridge from Claude Desktop through npx to the remote MCP server. The example file comments every field; remove the `_comment` keys before saving.

> **For nvm users:** `command` and `env.PATH` need absolute node paths, because Claude Desktop doesn't read your shell profile. Get them from `which npx` and `which python` while your normal shell is active.

### Optional: install the research skill

On Claude Desktop and Claude Code, copying the bundled skill turns on the multi-step research workflow:

```bash
mkdir -p ~/.claude/skills
cp skills/tipitaka-research.md ~/.claude/skills/
# Restart Claude Desktop (Cmd+Q then reopen) to pick up the skill
```

Details in [`skills/README.md`](./skills/README.md).

## 📦 MCP tools (14 total)

| Tool | Description |
|---|---|
| `search_hybrid` | Combined keyword + semantic search via RRF. Recommended for concept search, when you are after "discourses about X". |
| `search_by_keyword` | Trigram keyword search, best for the top few matches of an exact word (`appamāda`, `ānāpānassati`). |
| `survey_corpus` | Exhaustive corpus survey: exact total, per-pitaka breakdown, and the matched word-forms. For "how many times" or "every place X appears", where you need every occurrence rather than the best matches. `mode=thorough` adds concept-level semantic recall. |
| `search_semantic` | Pure vector similarity. Usually `search_hybrid` is the better choice. |
| `verify_quote` | Check a quote against the canon before repeating it. Returns `exact` / `close` / `not_found` with the matching segments, so a line can be attributed to a source instead of to a memory of one. |
| `get_sutta` | Fetch a sutta by ID (e.g. `mn1`, `dn22`, `dhp1-20`) with cross-reference URLs. Whole sutta by default; for long ones use `mode="outline"` (table of contents, no text), `around="<segment_id>"`+`window` (context around a hit), or `segment_range`/`offset`+`limit` to fetch just a slice. |
| `open_sutta_viewer` | Interactive sutta viewer (MCP Apps). Renders the sutta inline in the chat as Pāli + English side by side, with the cited segment highlighted. The calling model can attach an AI translation of the displayed segments into the user's own language (`translations` param) as a clearly badged third row; the canon itself stays Pāli + English. Needs an MCP Apps-capable host (Claude, Claude Desktop, VS Code Copilot, and others); on other hosts it falls back to text. |
| `get_reference` | Generate a properly formatted academic citation with all source URLs. |
| `compare_translations` | Compare renderings of a single segment across editions. |
| `list_structure` | Show the Tipiṭaka structure with segment-count coverage per nikāya. |
| `list_editions` | List any additional translation editions loaded beyond the bundled Pāli + English. The public server currently carries none, so it answers plainly that there are no extra editions. |
| `get_word_definition` | Pāli dictionary lookup (PTS, DPPN, and the Payutto Thai dictionary). |
| `define_from_suttas` | Find how the suttas and Vinaya define a term in their own words: canonical formulas like "Katamañca X? ... ayaṁ vuccati X", "X adhivacana", and the Vinaya's "X nāma". Gives primary-source definitions where `get_word_definition` gives dictionary glosses. |
| `parse_pali_word` | Strip Pāli suffixes to recover the root form when `get_word_definition` misses (`bhikkhūnaṁ` → `bhikkhu`). |

### ⚠️ Note on `search_semantic`

The vector index is built only on `text_pali`, using a multilingual MiniLM model that was not trained specifically on Pāli. (`bilara-data` carries Thai for 6 files in all, and the public server loads no Thai edition.) So:

- Pāli and English queries come back accurate, with good cross-lingual alignment.
- Thai queries return loose matches and aren't recommended.
- For an exact keyword like `appamāda`, `search_by_keyword` is more precise.
- For general-purpose search, `search_hybrid` (keyword + semantic) tolerates the limitation best.

Moving to a Pāli-trained embedding model such as bge-m3, and embedding the Thai edition, are both on the roadmap.

## 📁 Project structure

```text
tripitaka-mcp/
├── main.py                       # Main MCP Server (14 tools, 1 resource + 2 resource templates)
├── cli.py                        # `tripitaka-mcp` CLI (init / serve) for the pipx edition
├── sutta_verify.py               # Quote matching behind `verify_quote`
├── sutta_definitions.py          # Canonical definition formulas behind `define_from_suttas`
├── sutta_titles.py               # Sutta title resolution
├── mcp_app.py                    # MCP Apps registration (env-gated, `TRIPITAKA_MCP_APP`)
├── db/
│   ├── connection.py             # Database connection pool
│   └── schema.py                 # Schema (supports translation table)
├── embedding/
│   └── model.py                  # SentenceTransformer wrapper
├── scripts/
│   ├── install.sh                    # One-shot installer (HF dump → DB)
│   ├── deploy.sh                     # Deploy / restart on a VPS
│   ├── backup.sh                     # pg_dump → S3-compatible store
│   ├── dump_and_publish.sh           # Verify embeddings → pg_dump → upload to HuggingFace
│   ├── seed_metadata.py              # Seed pitaka/nikāya metadata
│   ├── data_loader.py                # Load Sutta Piṭaka (Pāli + bilara EN, per-book translator)
│   ├── load_vinaya.py                # Vinaya loader (Vibhaṅga + Pātimokkha + Khandhaka + Parivāra, Brahmali EN)
│   ├── load_abhidhamma.py            # Abhidhamma loader (7 books, Pāli — bilara has no EN)
│   ├── load_thai_cc0.py              # Thai translation loader
│   ├── load_dictionary.py            # Load dictionary data
│   ├── scrape_payutto.py             # Web scraper for the Payutto dictionary
│   ├── generate_embeddings.py        # Generate vector embeddings
│   ├── run_embedding_with_retry.sh   # Resilient wrapper around embedding generation (retries on DB drop)
│   ├── check_embedding_progress.py   # Live progress snapshot (or --watch mode) for the embedding job
│   ├── smoke_test.sh                 # Endpoint smoke test (TLS + /sse + /mcp + /health)
│   ├── test_full_sutta.py            # Full-content smoke test (22 size-tiered suttas, exact pinned counts)
│   ├── test_corpus_parity.py         # Check the corpus against the bilara-data clone it claims parity with
│   ├── test_definitions.py           # `define_from_suttas` regression + snapshot + backend parity
│   ├── test_verify_quote.py          # `verify_quote` regression, both backends
│   ├── test_survey_counts.py         # `survey_corpus` count drift
│   ├── test_pagination.py            # Slice / window / offset behaviour
│   └── test_mcp_prompts.py           # Prompt-level test — a real model picks the tools, a judge reads the answer
├── reader/                       # Bilingual reader served at /read/* (FastAPI)
│   ├── app.py                    # Routes: /read/, /read/{sutta_id}, search, browse
│   ├── queries.py                # Read-side queries
│   ├── featured.py               # Landing-page sutta cards
│   └── sutta_id_decoder.py       # Turn a sutta id into a human-readable location
├── site/                         # Static landing page served at the apex domain
├── topics/                       # Static markdown pages served at /topics/*
│   ├── README.md                 # Index of available topic pages
│   ├── tipitaka-overview.md      # Canon structure + coverage
│   ├── getting-started.md        # Connection paths, tool selection, prompt patterns
│   ├── places.md                 # Geography of the suttas (Mahājanapada, holy sites, cosmology)
│   ├── themes.md                 # 10 foundational teachings + locus classicus
│   ├── people.md                 # ~30 major figures (chief disciples, lay supporters, kings)
│   └── timeline.md               # Phase-based timeline of the 45-year teaching career
├── skills/                       # Portable Claude skills for AI clients
│   ├── README.md                 # How to install
│   └── tipitaka-research.md      # Multi-step research workflow
├── infra/                        # Reverse proxy + deploy config
│   ├── Caddyfile                 # Caddy: TLS, CORS for /mcp, /topics, /sse, /mcp
│   ├── Dockerfile.caddy          # Caddy + caddy-ratelimit plugin
│   ├── cloud-init.yml            # VPS bootstrap
│   └── *.tf                      # Terraform (provider-agnostic)
├── docs/
│   └── CAPACITY.md               # Capacity planning per VPS spec
├── claude_desktop_config.example.json
├── docker-compose.yml            # Dev (single mcp-server)
├── docker-compose.prod.yml       # Prod (db + 2 mcp-server + reader + caddy)
├── Dockerfile
└── requirements.txt
```

## 📜 Data sources & license

This project aggregates data from several sources under different licenses.
Please read [NOTICE.md](./NOTICE.md) in full before redistributing.

| Source | License | Note |
| --- | --- | --- |
| Source code | **MIT** | Free to use, fork, modify |
| [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) | **CC0** | Public domain |
| Thai translations (Dhīranando, Jayasāro) | **CC0** | Via SuttaCentral |
| [Dictionary of Buddhism](https://www.watnyanaves.net) by Somdet Phra Buddhaghosacariya (P. A. Payutto) | **Dhamma Dāna** | ⚠️ Non-commercial use only |
| PTS / DPPN / Dhammika Dictionaries | Public Domain / CC | |

### ⚠️ If you plan to fork or redistribute

- ✅ Use in free, dhamma-dāna, or educational projects
- ✅ Run it on your own machine, for personal use
- ❌ Don't use it in any paid product or service, because of the Payutto dictionary
- ❌ Don't modify the dictionary content

For commercial use: remove the dictionary component, or contact Wat Nyanavesakavan for permission.

### 🙏 Credits & attribution

See [CREDITS.md](./CREDITS.md) for contributor details and [NOTICE.md](./NOTICE.md) for license terms.

**Gratitude to:**

- Somdet Phra Buddhaghosacariya (P. A. Payutto) + Wat Nyanavesakavan
- SuttaCentral and the Thai & English translators
- 84000.org

---

**Sādhu 🙏**

May the sharing of this Dhamma bring benefit and happiness to all beings.
