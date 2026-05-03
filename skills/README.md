# Tripiṭaka MCP — Claude Skills

Reusable skill definitions for AI clients that load Tripiṭaka MCP. Drop a skill file into the client's skill directory and the client will auto-activate it on matching prompts.

## Available skills

| File | Activates on | Purpose |
| --- | --- | --- |
| [`tipitaka-research.md`](tipitaka-research.md) | Buddhist scripture / Pāli Canon / dhamma research questions | Multi-tool workflow: clarify → verify coverage → search → drill into suttas → cite with URLs |

## Install

### Claude Desktop / Claude Code (project-scoped)

Copy the skill into the project's `.claude/skills/` directory:

```bash
mkdir -p ~/<your-project>/.claude/skills
cp skills/tipitaka-research.md ~/<your-project>/.claude/skills/
```

Restart the client. The skill will activate automatically on matching prompts (the `description` frontmatter is the trigger).

### Claude Desktop (user-scoped, applies to all projects)

```bash
mkdir -p ~/.claude/skills
cp skills/tipitaka-research.md ~/.claude/skills/
```

### Claude Code (global plugin)

Add to your global plugin location and restart `claude`.

## Why ship this with the MCP server

Tipiṭaka research has a specific shape — clarify scope, verify coverage, multi-tool workflow, scholarly caveats — that we have proven works empirically through Claude Desktop testing. Without the skill, every user has to rediscover this workflow on their own. With the skill, any client that supports skills picks it up automatically.

The skill encodes lessons learned from real testing sessions, including:

- The DN 22 `Ānāpānapabba` case (canonical Pāli puts topic terms in section markers, not teaching content)
- The AN 10.7 hallucination case (always verify before claiming)
- Cross-reference URL surfacing (rendering as markdown clickable, picking primary source by user language)
- Tiered scope offering when "all of X" is requested

Update this skill whenever a new pattern emerges from production usage.
