# Installing Tripitaka MCP — instructions for AI installer agents

> This document is written for AI agents (Cline, Claude Desktop with MCP install skill, etc.) that install MCP servers on the user's behalf. Humans should follow [README.md](./README.md) instead.

## Overview

Tripitaka MCP is a **hosted public service** offered as Dhamma Dāna. The maintainer runs a free, rate-limited instance — **no installation, no Docker, no GPU required**. The user only needs:

1. [Node.js](https://nodejs.org/) installed (any recent version, for the `npx` bridge)
2. An MCP-capable client (Claude Desktop, Cline, Cursor, Codex, Continue.dev, etc.)
3. A working internet connection

Self-hosting is also supported but is the secondary path — only choose it if the user explicitly asks for an offline setup or wants to fork the data.

## Recommended install path — connect to the hosted service

This is the path Cline / installer agents should default to.

### Step 1: Find the user's `npx` path

Claude Desktop, Cline, and similar clients spawn MCP servers as subprocesses without inheriting the user's shell PATH. Always use an **absolute path** to `npx`. Find it:

```bash
which npx
```

Typical results:

- `nvm` user: `/Users/<USERNAME>/.nvm/versions/node/v<VERSION>/bin/npx`
- macOS Homebrew: `/opt/homebrew/bin/npx` (Apple Silicon) or `/usr/local/bin/npx` (Intel)
- Windows: `C:\Program Files\nodejs\npx.cmd`
- Linux apt: `/usr/bin/npx`

Capture the parent directory too — it goes into `env.PATH`:

```bash
dirname "$(which npx)"
```

### Step 2: Add the entry to the client's MCP config

For Claude Desktop, the file is at:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

For Cline, it's the project's `cline_mcp_settings.json` (Cline UI → MCP Servers → Settings) — the schema is identical to Claude Desktop's.

Insert this entry under `mcpServers`:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "<NPX_ABSOLUTE_PATH>",
      "args": ["-y", "mcp-remote", "https://mcp.tripitaka-mcp.com/mcp"],
      "env": {
        "PATH": "<NODE_BIN_DIR>:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

Replace `<NPX_ABSOLUTE_PATH>` with the output from Step 1, and `<NODE_BIN_DIR>` with that path's parent directory.

### Step 3: Restart the client

The client must be **fully quit and reopened** — closing the window is not enough. On macOS, `⌘Q` then reopen.

### Step 4: Verify

After restart, the client's MCP indicator (🔌 in Claude Desktop's bottom-left) should show `tripitaka` connected with **10 tools** and **3 resources**.

> First-run takes 5–10 seconds while `npx` downloads the `mcp-remote` package on demand. Subsequent restarts are instant.

The available tools are:

| Tool | Purpose |
| --- | --- |
| `search_hybrid` | Best-default — combined keyword + semantic via RRF |
| `search_by_keyword` | Trigram fuzzy match for exact Pāli terms |
| `search_semantic` | Pure vector similarity (Pāli-trained model not yet) |
| `get_sutta` | Fetch any sutta in full by ID |
| `get_reference` | Generate an academic citation |
| `compare_translations` | Side-by-side renderings of one segment across editions |
| `list_structure` | Tipiṭaka tree with segment counts |
| `list_editions` | Available translation editions |
| `get_word_definition` | Pāli ↔ Thai/English dictionary lookup |
| `parse_pali_word` | Strip inflectional suffixes to recover root forms |

Resources: `tripitaka://structure`, `tripitaka://sutta/{sutta_id}`, `tripitaka://word/{word}`.

## Sample tool call to verify the install

Ask the user (or the LLM agent) to send a query like:

> "Use the tripitaka tools to fetch DN 22 (Mahāsatipaṭṭhāna Sutta) and quote the opening passage in Pāli with the SuttaCentral cross-reference URL."

Expected behaviour: client calls `get_sutta(sutta_id="dn22")`, receives ~454 segments with `cross_reference.suttacentral.pali_url` populated, and surfaces the URL as a clickable link.

If the client returns "tool not found" or hangs > 30 seconds after restart, see [Troubleshooting](#troubleshooting).

## Self-host alternative (only if user asks)

For users who want offline data or to fork:

```bash
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git
cd tripitaka-mcp
./scripts/install.sh
```

The installer downloads a prepared HuggingFace database dump (~444K segments + embeddings) and restores it locally — about 5 minutes vs 2-4 hours for a fresh load + embedding generation. After completion, the script prints a ready-to-paste local-stdio config.

Full self-host details: [README.md](./README.md) and [DEPLOYMENT.md](./DEPLOYMENT.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Client shows `tripitaka` disconnected | `command` is generic `npx` | Use absolute `which npx` output |
| Connection errors after restart | `env.PATH` missing node bin dir | Add `<NODE_BIN_DIR>` as the first PATH entry |
| Hangs > 30s on first connect | `npx` is downloading `mcp-remote` | Wait one minute, then check |
| `tool not found` errors | Restarted only the window, not the client | `⌘Q` (or tray → Quit) then reopen |
| All requests return 429 | Hit rate limit (10 req/10s + 60 req/min per IP) | Pace queries; the limit is per-client-IP |

## License & ethos

MIT (code) — see [NOTICE.md](./NOTICE.md) for data licenses (some data is non-commercial only). Project offered as **Dhamma Dāna**: free, non-commercial use for study, research, and practice. Do not include this server in paid products without checking NOTICE.md.

## Contact

Issues and feedback: <https://github.com/dhamma-seeker/tripitaka-mcp/issues>.
