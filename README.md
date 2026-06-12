# Tripitaka MCP Server

<p align="center">
  <img src="https://tripitaka-mcp.com/favicon-192.png" alt="Tripitaka MCP logo — folded hands over a dhammacakka in pixel art" width="160" height="160">
</p>

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![MCP Spec](https://img.shields.io/badge/MCP-2025--03--26-8b6914)](https://spec.modelcontextprotocol.io/)
[![Coverage](https://img.shields.io/badge/Tipi%E1%B9%ADaka-%7E444K%20segments-8b6914)](https://tripitaka-mcp.com/)
[![Hosted](https://img.shields.io/badge/hosted-tripitaka--mcp.com-8b6914)](https://tripitaka-mcp.com/)
[![Dhamma Dāna](https://img.shields.io/badge/offered%20as-Dhamma%20D%C4%81na-8b6914?labelColor=fafaf7&color=8b6914)](./NOTICE.md)
[![Glama](https://glama.ai/mcp/servers/dhamma-seeker/tripitaka-mcp/badges/score.svg)](https://glama.ai/mcp/servers/dhamma-seeker/tripitaka-mcp)
[![Smithery](https://smithery.ai/badge/dhamma-seeker/tripitaka-mcp)](https://smithery.ai/server/dhamma-seeker/tripitaka-mcp)

An MCP Server for searching and citing content from the Pāli Tipiṭaka.
Gives AI agents (such as Claude or Cursor) the ability to look up suttas, quote the teachings, and compare translations across languages.

> 🙏 **This project is offered as Dhamma Dāna** — 100% free, non-commercial only.
> License details: [LICENSE](./LICENSE) (code) + [NOTICE.md](./NOTICE.md) (data)

## ✨ Features

- 📚 **Full Tipiṭaka coverage at parity with SuttaCentral** — all three baskets indexed (~444K segments): Sutta (Pāli + Sujato English), Vinaya (Pāli + Brahmali English), and Abhidhamma (Pāli only — no English in upstream `bilara-data` for any Abhidhamma book). Live counts via `list_structure`.
- ⚖️ **Hybrid Search** — highest precision by combining keyword and semantic search through Reciprocal Rank Fusion (RRF). Ready to use.
- 🔍 **Keyword Search** — trigram fuzzy matching with cross-language alignment.
- 🧠 **Semantic Search** — meaning-based search via vector similarity (pgvector).
- 📖 **Translation Comparison** — view and compare renderings across editions, aligned at the segment level.
- 📚 **Dictionary Bridge** — built-in dictionary of 20,000+ entries (P. A. Payutto, PTS, DPPN).
- 📖 **Get Sutta & Reference** — fetch sutta content by ID (e.g. `mn1`, `pli-tv-bu-vb-pj1`, `patthana1.1`) and generate properly formatted academic citations.
- 🔬 **Pāli word analyzer** — strip inflectional suffixes to find the root form when dictionary lookup misses (`bhikkhūnaṁ` → `bhikkhu`).
- 🔗 **Cross-reference URLs in every response** — a clickable deep link to the project's own bilingual reader (Pāli + English, with a segment anchor that highlights the cited verse). The reader renders SuttaCentral's `bilara-data` verbatim, so it is the authoritative text; AI clients surface this link so users verify the source in one click.
- 📡 **Dual transport** — both legacy SSE (`/sse`) and canonical Streamable HTTP (`/mcp`, MCP spec 2025-03-26).
- 📦 **MCP Resources** — `tripitaka://structure`, `tripitaka://sutta/{id}`, `tripitaka://word/{w}` for clients that pin context as resources.
- 📄 **Curated reference pages** at [`/topics/*`](https://mcp.tripitaka-mcp.com/topics/) — six markdown pages covering canon structure, getting-started + tool selection, places (Mahājanapada + holy sites + cosmology), 10 foundational themes with locus classicus, ~30 major figures, and a phase-based timeline of the Buddha's 45-year mission. Sutta IDs verified against live data; AI clients can fetch a page in one shot instead of running 30+ tool calls.
- 🤖 **Claude skill** — `skills/tipitaka-research.md` ships a ready-to-install workflow file that activates a multi-step research pattern (clarify → verify coverage → search → drill in → cite) on Claude Desktop / Claude Code.
- 📮 **Postman Ready** — ships with a Postman collection for testing the API.

## 🏗️ Tech Stack

| Technology | Role |
|---|---|
| Python + FastMCP | MCP Server |
| PostgreSQL + pgvector | Database + Vector Search |
| sentence-transformers | Embeddings for semantic search |
| Docker Compose | Infrastructure |

## 🚀 Quick Start

### 🌐 No setup — connect to the public Dhamma Dāna server

The maintainers run a free public instance at **[tripitaka-mcp.com](https://tripitaka-mcp.com)**.

| Endpoint | Use |
|---|---|
| `https://mcp.tripitaka-mcp.com/mcp` | Streamable HTTP (MCP spec 2025-03-26) |
| `https://mcp.tripitaka-mcp.com/sse` | Legacy SSE (older clients) |

**Connect Claude Desktop in three steps** (no install, no Docker, no GPU — you just need [Node.js](https://nodejs.org/)):

**1.** Find your absolute `npx` path. Claude Desktop doesn't read your shell profile, so a bare `npx` won't resolve. Open a terminal:

```bash
which npx
# example: /Users/you/.nvm/versions/node/v22.14.0/bin/npx
```

**2.** Open `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows) and add the entry below — substitute `YOUR_NPX_PATH` with the output from step 1, and `YOUR_NODE_BIN_DIR` with that path's parent directory:

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

**3.** Quit Claude Desktop completely (`⌘Q` on macOS, tray → Quit on Windows) and reopen. The 🔌 indicator in the bottom-left should show `tripitaka` with 12 tools available.

> _First connection takes 5–10 seconds_ while `npx` downloads `mcp-remote` on demand — give Claude Desktop a moment after restart before assuming it failed.

Once connected, try asking Claude things like:

- "What does the Buddha teach about mindfulness of breathing? Quote the relevant passages from MN 118."
- "Show me the full text of the Karaṇīyamettasutta in Pāli and English."
- "What does the Pāli word _sati_ mean according to the Payutto dictionary?"
- "Find suttas where the Buddha discusses anger."

Claude will pick the right tool, fetch the canonical Pāli, and surface a clickable link to the project's bilingual reader for verification.

The hosted server is rate-limited (10 req/10s + 60 req/min per IP) and offered for personal study, research, and dhamma practice — see [NOTICE.md](./NOTICE.md) before redistributing or using commercially.

### 💻 Run it fully offline (`pipx` — local SQLite, no server)

Prefer to keep everything on your own machine — no network calls to the hosted server? Install the local edition. It ships the whole Pāli canon as a single SQLite file (~120 MB) and runs as a local stdio MCP server.

```bash
pipx install tripitaka-mcp     # needs Python 3.10+
tripitaka-mcp init             # one-time: downloads the SQLite database
tripitaka-mcp serve            # runs the MCP server over stdio
```

Then point Claude Desktop / Cursor at the local command — no `npx`, no `mcp-remote`, no internet:

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

**Hosted vs local — what's different**

Both serve the same ~444K-segment canon. The differences:

| | Hosted (`mcp.tripitaka-mcp.com`) | Local (`pipx`) |
|---|---|---|
| Tools | all 12 | 9 (10 with `TRIPITAKA_MCP_APP=1`) — no `search_semantic` / `search_hybrid` |
| Concept / semantic search | ✅ vector search (pgvector) | ❌ — use `search_by_keyword` instead |
| Keyword search | PostgreSQL trigram — fuzzy, typo-tolerant, similarity-ranked | SQLite FTS5 — whole-word / token match; **results and ranking can differ** from hosted |
| Canon data | always current | a snapshot from when you ran `init` — re-run `tripitaka-mcp init` to refresh |
| Updates | automatic | `pipx upgrade tripitaka-mcp` for code; re-run `init` for data |
| Privacy | queries reach the hosted server (nothing logged — see [Privacy Policy](https://tripitaka-mcp.com/privacy/)) | nothing leaves your machine |
| Internet | required | not needed after `init` |
| Rate limit | 10 req / 10 s, 60 req / min per IP | none |
| Setup | zero / one-click | Python 3.10+, pipx, one-time ~120 MB download |

`search_semantic` / `search_hybrid` and the trigram keyword index need PostgreSQL + pgvector + a ~1 GB embedding model — too heavy for a lightweight local install, so they stay hosted-only. In local mode those two tools aren't registered at all: a connected client sees only the 9 available tools, so it never tries to call a tool that can't work.

Because the local server is a standard stdio MCP server, it also enables a **fully offline AI stack** — pair it with a local model (e.g. Ollama) and any MCP-capable chat UI, and nothing leaves your machine.

### 🏎️ Fastest local path — use the installer (recommended for non-developers)

```bash
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git
cd tripitaka-mcp
./scripts/install.sh
```

The installer **downloads a prepared database dump from [Hugging Face — dhamma-seeker/tripitaka-mcp-dump](https://huggingface.co/datasets/dhamma-seeker/tripitaka-mcp-dump) and restores it automatically** — cutting setup time from 2–4 hours (loading data + generating embeddings) down to ~5 minutes.
(If a local dump file already exists, the local copy is used instead.)

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

#### 1. Clone & Setup

```bash
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git
cd tripitaka-mcp
cp .env.example .env
# Set POSTGRES_PASSWORD in .env to a random password
```

#### 2. Start Database

```bash
docker compose up db -d
```

#### 3. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Initialize Database & Load Data

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

#### 5. Run MCP Server

```bash
python main.py
```

### 🧪 Testing with Postman

The project supports Postman testing in SSE mode:

1. Run the server with: `MCP_TRANSPORT=sse python main.py`
2. Import [postman_collection.json](./postman_collection.json) into Postman
3. Invoke the tools directly

## 🚢 Production Deployment

To deploy to production without re-loading the data and re-running the embedding model, restoring from a database dump is the recommended path.

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The production stack runs 3 services:

- `db` — PostgreSQL + pgvector (internal only, no exposed port)
- `mcp-server` — FastMCP (runs as a readonly user, read-only FS, `cap_drop: ALL`)
- `caddy` — reverse proxy + Let's Encrypt + **rate limit** (10 req/10s and 60 req/1 min per IP)

For an extra hardening layer, front Caddy with **Cloudflare** (DNS proxy + rate-limit rules + DDoS protection on the free tier).

👉 Full details: **[DEPLOYMENT.md](./DEPLOYMENT.md)**

## 🔧 Connecting to Claude Desktop

The repo ships [`claude_desktop_config.example.json`](./claude_desktop_config.example.json) with **three ready-to-use entries** — copy whichever fits your setup into `claude_desktop_config.json` (`~/Library/Application Support/Claude/` on macOS, `%APPDATA%\Claude\` on Windows), then edit the absolute paths:

| Entry | When to use | Transport |
|---|---|---|
| `tripitaka-local` | You ran the installer locally on the same machine as Claude Desktop | stdio (no network) |
| `tripitaka-remote` | You self-hosted the server on a VPS and want the modern transport | Streamable HTTP (`/mcp`) |
| `tripitaka-remote-sse` | Your client doesn't support Streamable HTTP yet | Legacy SSE (`/sse`) |

The remote entries route through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) — Claude Desktop ↔ npx bridge ↔ remote MCP. The example file has annotated comments explaining each field; remove the `_comment` keys before saving.

> **Heads-up for nvm users:** `command` and `env.PATH` need absolute node paths — Claude Desktop doesn't read your shell profile. Find the right paths with `which npx` / `which python` while your normal shell is active.

### Optional: install the research skill

For Claude Desktop / Claude Code users, copying the bundled skill activates the multi-step research workflow automatically:

```bash
mkdir -p ~/.claude/skills
cp skills/tipitaka-research.md ~/.claude/skills/
# Restart Claude Desktop (Cmd+Q then reopen) to pick up the skill
```

Details in [`skills/README.md`](./skills/README.md).

## 📦 MCP Tools (12 total)

| Tool | Description |
|---|---|
| `search_hybrid` | **(Recommended for concept search)** Combined keyword + semantic via RRF — best when looking for "discourses about X". |
| `search_by_keyword` | Trigram keyword search — best for the top few matches of an exact word (`appamāda`, `ānāpānassati`). |
| `survey_corpus` | **Exhaustive** corpus survey — exact total + per-pitaka breakdown + the matched word-forms, for "how many times / every place X appears" (coverage, not just best matches). `mode=thorough` adds concept-level semantic recall. |
| `search_semantic` | Pure vector similarity — usually you want `search_hybrid` instead. |
| `get_sutta` | Fetch a sutta by ID (e.g. `mn1`, `dn22`, `dhp1-20`) with cross-reference URLs. Whole sutta by default; for long ones use `mode="outline"` (table of contents, no text), `around="<segment_id>"`+`window` (context around a hit), or `segment_range`/`offset`+`limit` to fetch just a slice. |
| `open_sutta_viewer` | **Interactive sutta viewer (MCP Apps)** — renders the sutta inline in the chat as Pāli + English side by side, with the cited segment highlighted. The calling model can attach an AI translation of the displayed segments into the user's own language (`translations` param) as a clearly-badged third row — the canon itself stays Pāli + English. Requires an MCP Apps-capable host (Claude, Claude Desktop, VS Code Copilot, …); other hosts get a graceful text fallback. |
| `get_reference` | Generate a properly formatted academic citation with all source URLs. |
| `compare_translations` | Compare renderings of a single segment across editions. |
| `list_structure` | Show the Tipiṭaka structure with segment-count coverage per nikāya. |
| `list_editions` | List Thai/English translation editions currently loaded. |
| `get_word_definition` | Pāli dictionary lookup (PTS, DPPN, and the Payutto Thai dictionary). |
| `parse_pali_word` | Strip Pāli suffixes to recover the root form when `get_word_definition` misses (`bhikkhūnaṁ` → `bhikkhu`). |

### ⚠️ Note on `search_semantic`

The vector index is built only on `text_pali` (SuttaCentral's bilara-data does not yet include Thai translations) using a multilingual MiniLM model that is **not specifically trained on Pāli**. As a result:

- **Pāli / English queries** → accurate (good cross-lingual alignment)
- **Thai queries** → loose matches, not recommended
- For exact keywords like `appamāda`, `search_by_keyword` is more precise
- For general-purpose search, `search_hybrid` (keyword + semantic) tolerates this limitation best

Upgrading to a Pāli-trained embedding model (e.g. bge-m3) plus embedding the Thai edition is on the roadmap.

## 📁 Project Structure

```text
tripitaka-mcp/
├── main.py                       # Main MCP Server (12 tools + 3 resources)
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
│   ├── data_loader.py                # Load Sutta Piṭaka (Pāli + Sujato English)
│   ├── load_vinaya.py                # Vinaya loader (Vibhaṅga + Pātimokkha + Khandhaka + Parivāra, Brahmali EN)
│   ├── load_abhidhamma.py            # Abhidhamma loader (7 books, Pāli — bilara has no EN)
│   ├── load_thai_cc0.py              # Thai translation loader
│   ├── load_dictionary.py            # Load dictionary data
│   ├── scrape_payutto.py             # Web scraper for the Payutto dictionary
│   ├── generate_embeddings.py        # Generate vector embeddings
│   ├── run_embedding_with_retry.sh   # Resilient wrapper around embedding generation (retries on DB drop)
│   ├── check_embedding_progress.py   # Live progress snapshot (or --watch mode) for the embedding job
│   ├── smoke_test.sh                 # Endpoint smoke test (TLS + /sse + /mcp + /health)
│   └── test_full_sutta.py            # Full-content smoke test (22 size-tiered suttas across all 3 piṭakas)
├── topics/                       # Static markdown pages served at /topics/*
│   ├── README.md                 # Index of available topic pages
│   ├── tipitaka-overview.md      # Canon structure + coverage
│   ├── getting-started.md        # Connection paths, tool selection, prompt patterns
│   ├── places.md                 # Geography of the suttas (Mahājanapada, holy sites, cosmology)
│   ├── themes.md                 # 10 foundational teachings + locus classicus
│   └── people.md                 # ~30 major figures (chief disciples, lay supporters, kings)
├── skills/                       # Portable Claude skills for AI clients
│   ├── README.md                 # How to install
│   └── tipitaka-research.md      # Multi-step research workflow
├── infra/                        # Reverse proxy + deploy config
│   ├── Caddyfile                 # Caddy: TLS, rate limit, /topics, /sse, /mcp
│   ├── Dockerfile.caddy          # Caddy + caddy-ratelimit plugin
│   ├── cloud-init.yml            # VPS bootstrap
│   └── *.tf                      # Terraform (provider-agnostic)
├── docs/
│   └── CAPACITY.md               # Capacity planning per VPS spec
├── claude_desktop_config.example.json
├── docker-compose.yml            # Dev (single mcp-server)
├── docker-compose.prod.yml       # Prod (db + 2 mcp-server + caddy)
├── Dockerfile
└── requirements.txt
```

## 📜 Data Sources & License

This project aggregates data from multiple sources under different licenses.
**Please read [NOTICE.md](./NOTICE.md) in full before redistributing.**

| Source | License | Note |
| --- | --- | --- |
| Source code | **MIT** | Free to use, fork, modify |
| [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) | **CC0** | Public domain |
| Thai translations (Dhīranando, Jayasāro) | **CC0** | Via SuttaCentral |
| [Dictionary of Buddhism](https://www.watnyanaves.net) by Somdet Phra Buddhaghosacariya (P. A. Payutto) | **Dhamma Dāna** | ⚠️ Non-commercial use only |
| PTS / DPPN / Dhammika Dictionaries | Public Domain / CC | — |

### ⚠️ If you plan to fork or redistribute

- ✅ Use in **free / dhamma-dāna / educational** projects — allowed
- ✅ Run on your own machine / personal use — allowed
- ❌ **Do not use in any paid product or service** (because of the Payutto dictionary)
- ❌ **Do not modify the dictionary content**

For commercial use: remove the dictionary component, or contact Wat Nyanavesakavan for permission.

### 🙏 Credits & Attribution

See [CREDITS.md](./CREDITS.md) for contributor details and [NOTICE.md](./NOTICE.md) for license terms.

**Gratitude to:**

- Somdet Phra Buddhaghosacariya (P. A. Payutto) + Wat Nyanavesakavan
- SuttaCentral and the Thai & English translators
- 84000.org

---

**Sādhu 🙏** — May the sharing of this Dhamma bring benefit and happiness to all beings.
