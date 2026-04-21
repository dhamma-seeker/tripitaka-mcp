# 🛕 Tripitaka MCP Server

An MCP Server for searching and citing content from the Pāli Tipiṭaka.
Gives AI agents (such as Claude or Cursor) the ability to look up suttas, quote the teachings, and compare translations across languages.

> 🙏 **This project is offered as Dhamma Dāna** — 100% free, non-commercial only.
> License details: [LICENSE](./LICENSE) (code) + [NOTICE.md](./NOTICE.md) (data)

## ✨ Features

- ⚖️ **Hybrid Search** — highest precision by combining keyword and semantic search through Reciprocal Rank Fusion (RRF). Ready to use.
- 🔍 **Keyword Search** — keyword lookup across three languages (Pāli, Thai, English) with trigram fuzzy matching and cross-language alignment.
- 🧠 **Semantic Search** — meaning-based search that captures the intent of a passage via vector similarity (pgvector).
- 📖 **Translation Comparison** — view and compare renderings across different editions, aligned line-by-line at the segment level.
- 📚 **Dictionary Bridge** — built-in dictionary of 20,000+ entries (P. A. Payutto, PTS, DPPN).
- 📖 **Get Sutta & Reference** — fetch sutta content by ID (e.g. `mn1`) and generate properly formatted academic citations.
- 📮 **Postman Ready** — ships with a Postman collection for testing the API in SSE mode so you can wire it up to your dev workflow immediately.

## 🏗️ Tech Stack

| Technology | Role |
|---|---|
| Python + FastMCP | MCP Server |
| PostgreSQL + pgvector | Database + Vector Search |
| sentence-transformers | Embeddings for semantic search |
| Docker Compose | Infrastructure |

## 🚀 Quick Start

### 🏎️ Fastest path — use the installer (recommended for non-developers)

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

### Local (stdio)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "python",
      "args": ["/path/to/tripitaka-mcp/main.py"],
      "env": {
        "DATABASE_URL": "postgresql://admin:password123@localhost:5432/tripitaka_db"
      }
    }
  }
}
```

### Remote (self-hosted on a server)

If you've deployed the MCP server to a VPS, use [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) to bridge SSE → stdio:

```json
{
  "mcpServers": {
    "tripitaka-remote": {
      "command": "/Users/YOU/.nvm/versions/node/v22.x/bin/npx",
      "args": ["-y", "mcp-remote", "https://mcp.example.org/sse", "--transport", "sse-only"],
      "env": {
        "PATH": "/Users/YOU/.nvm/versions/node/v22.x/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

A fully annotated example is in [`claude_desktop_config.example.json`](./claude_desktop_config.example.json).

## 📦 MCP Tools

| Tool | Description |
|---|---|
| `search_hybrid` | **(Recommended)** Combined search using RRF for maximum precision. |
| `search_by_keyword` | Keyword search (trigram fuzzy match). |
| `search_semantic` | Semantic search (vector similarity) — ⚠️ best with **Pāli / English** queries (see note below). |
| `get_sutta` | Fetch sutta content by ID along with all available translations. |
| `compare_translations`| Compare renderings across editions at the segment level. |
| `get_word_definition` | Cross-language dictionary lookup (PTS, DPPN, and the Payutto dictionary). |
| `list_structure` | Display the structure of the Tipiṭaka canon. |
| `get_reference` | Generate a properly formatted academic citation. |

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
├── main.py                 # Main MCP Server (all tools)
├── db/
│   ├── connection.py       # Database connection pool
│   └── schema.py           # Database schema (supports translation table)
├── embedding/
│   └── model.py            # SentenceTransformer wrapper
├── scripts/
│   ├── seed_metadata.py    # Seed pitaka/nikāya metadata
│   ├── data_loader.py      # Load Pāli/English from SuttaCentral
│   ├── load_thai_cc0.py    # Sentence-by-sentence Thai translation loader
│   ├── load_dictionary.py  # Load dictionary data into the system
│   ├── scrape_payutto.py   # Web scraper for the Payutto dictionary
│   └── generate_embeddings.py  # Generate vector embeddings
├── data/
│   └── payutto_dict.json   # Thai dictionary dataset scraped from the web
├── docker-compose.yml
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
