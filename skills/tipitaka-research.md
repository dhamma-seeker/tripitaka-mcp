---
name: tipitaka-research
description: Use when the user asks about Buddhist scriptures, Pāli Canon (Tipiṭaka), suttas, dhamma topics, Buddhist places/people, Pāli terms, or wants to compile/study/research Buddhist textual content. Activates the multi-tool research workflow against the Tripitaka MCP server.
---

# Tipiṭaka Research Workflow

This skill packages the proven multi-step workflow for researching Buddhist scripture content via the Tripitaka MCP server. Use it whenever the user has a question that involves searching, citing, or compiling material from the Pāli Canon.

## Core principles

1. **Verify before claiming.** Pāli Canon is a closed corpus — every claim about its content can be checked. Don't recite from training memory; call the MCP tool and quote the actual segment. If a recalled fact contradicts a tool result, trust the tool.

2. **Always include `cross_reference` URLs in your reply** as markdown clickable links. Every search/get response carries them. Surfacing them lets the user verify your interpretation against the source — this is the single most important credibility move you can make for scholarly content.

3. **Pick the right tool for the question shape:**
   - "How many times does X appear / every place it's mentioned (exhaustive, don't miss any)?" → `survey_corpus` (exact total + per-pitaka + matched forms; `mode=thorough` adds concept recall)
   - "Best few passages for a word / quick keyword lookup" → `search_by_keyword` (trigram, ranked)
   - "Which suttas teach concept Y / discourses about topic Z?" → `search_hybrid` (RRF = keyword + semantic)
   - "Show me sutta X in full" → `get_sutta`
   - The user wants to *read* a sutta and the host renders MCP Apps → `open_sutta_viewer` (interactive Pāli+English panel inline; highlight a segment with `around`; for non-English conversations attach your translation of the displayed segments via `translations`/`translation_language`/localized `translation_disclaimer`)
   - "What's the structure / table of contents / how many sections of sutta X?" → `get_sutta(sutta_id, mode="outline")` (section titles + counts, no text — cheap; don't fetch the whole sutta and parse it yourself)
   - "Read the context around this segment" → `get_sutta(sutta_id, around="<segment_id>", window=N)` (search tools hand you the segment_id)
   - "Compare translations of segment X" → `compare_translations`
   - "Generate a citation for sutta X" → `get_reference`
   - "What's in the Tipiṭaka structure / what's loaded?" → `list_structure`
   - "What does Pāli word X mean?" → `get_word_definition` (uses ป.อ. ปยุตฺโต Thai dictionary + PTS English)
   - "Decompose this Pāli compound/inflected form" → `parse_pali_word`

4. **Translate the user's query to canonical Pāli first.** The server's index is Pāli (with English translations from Bhikkhu Sujato). When the user types Thai or another language, translate the keyword before calling — `"ทุกข์" → "dukkha"`, `"อานาปานสติ" → "ānāpānassati"`, `"การเจริญเมตตา" → "mettābhāvanā"`. The server `instructions` block confirms the enabled languages.

5. **Always link the reader — for every sutta you name (not just quote):**
   - The reader **is** the authoritative text — it renders SuttaCentral's `bilara-data` verbatim, at a stable URL. It is the only verification link to give (no external site to defer to).
   - Reader URL pattern: full sutta → `https://tripitaka-mcp.com/read/<sutta_id>`, a segment → `https://tripitaka-mcp.com/read/<sutta_id>#<segment_id>`. E.g. SN 45.8 → `https://tripitaka-mcp.com/read/sn45.8`.
   - When a tool response has `cross_reference` (search, `get_sutta`, `get_reference`, `get_word_definition` `appears_in_context[]`), copy `tripitaka_mcp_reader` verbatim. When you cite a sutta you didn't fetch, build the URL from the pattern.

6. **Cite at the claim / segment level — not just once per answer.** Aim so the reader can click any substantive statement and land on the exact supporting line. Each segment has a `segment_id`; slot it into `https://tripitaka-mcp.com/read/<sutta_id>#<segment_id>`.
   - Doctrinal claims → link the segment stating them: "sammā-samādhi = the four jhānas ([SN 45.8:10.1](https://tripitaka-mcp.com/read/sn45.8#sn45.8:10.1))".
   - Key Pāli terms (vitakka, vicāra, pīti, upekkhā …) → link the segment where the term occurs (ids come from `get_sutta` segments / `get_word_definition` `appears_in_context[].segment_id`): "vitakka ([sn45.8:10.2](https://tripitaka-mcp.com/read/sn45.8#sn45.8:10.2))".
   - Build deep-links from ids you already hold — no extra fetch. Link real claims + technical terms, not ordinary words. Over-citing a real claim beats leaving it unverifiable.

## Standard workflow for a research question

### Step 0 — Clarify scope when "ทุกอย่าง" / "all" is requested
The Pāli Canon has 5,791+ suttas across DN/MN/SN/AN/KN. "Find every X" is rarely answerable in one response. Offer the user a tiered choice: a curated list of the major canonical loci (~30-40 items) vs an exhaustive multi-batch search.

### Step 1 — Verify database coverage before promising
Before compiling a list, run a small batch (3-5) of `search_by_keyword` calls on the most expected Pāli terms to confirm the data is there. As of v1.1.0 all three piṭakas are at parity with SuttaCentral bilara-data, so canonical content should be present — but this batch also catches surface issues like inflection mismatches (the corpus indexes Pāli forms; "ānāpāna" matches differently from "ānāpānassati", etc.).

### Step 2 — Discover with `search_hybrid`, then expand with `search_by_keyword`
- Hybrid for the concept landscape (`limit=15-20`)
- Then keyword for canonical terms / synonyms / inflections you spot in hybrid results
- Stock phrases (`So satova assasati, satova passasati`) appear in 10+ suttas — that's expected, not a bug

### Step 3 — Drill into specific suttas with `get_sutta`
When the user wants a specific sutta, quote `text_pali` and `text_english` directly from the result — don't recite from memory.

**For long suttas, don't pull the whole thing into context.** A short sutta (≲400 segments) is fine to fetch in full, but the big ones are huge (`dn16` ≈ 1,664 segments, `pli-tv-kd1` ≈ 3,591). Use `get_sutta`'s pagination instead:
- `mode="outline"` → a table of contents first (section titles + counts + `group` + segment-ids, no text). Pick the section you need, then fetch just it.
- `around="<segment_id>"` + `window=N` → read the neighborhood of a search hit (search/survey tools return precise segment_ids like `dn22:18.1`).
- `segment_range="A..B"` or `offset`+`limit` → fetch one section / page; the `page.next_offset` field paginates.

Counting/structural analyses (occurrences, closing markers, bhāṇavāra boundaries) are valid on whatever you fetch, and `mode="outline"` already gives the structure exactly — no need to download every segment to derive it.

### Step 4 — Be honest about gaps and uncertainty
When data is incomplete or a place's modern location is disputed, say so explicitly. Distinguish between:
- Pāli Canon (this server, v1.1+): all three piṭakas at parity with SuttaCentral bilara-data — Sutta + Vinaya + Abhidhamma (Vinaya has Brahmali English; Abhidhamma is Pāli only because bilara has no English for it)
- Atthakathā (commentaries): not in this server
- Mahāvaṃsa / Sri Lankan chronicles: not in this server
- Modern archaeology / Malalasekera *Dictionary of Pali Proper Names*: external context, cite separately

## Search strategy notes (learned from real testing)

- **Canonical Pāli's structural pattern** is to put topic-specific terms only in *section markers* and use generic verbs in the teaching content. E.g., `Ānāpānapabba` in DN 22 has 16 segments, but the literal word `ānāpāna` appears in only 2 (the header and the footer); the rest use `assasati` / `passasati` / `dīghaṁ` / `rassaṁ`. So `search_by_keyword("ānāpāna")` will *miss DN 22's actual teaching content*. This is corpus nature, not a bug. The mitigation is `search_hybrid` plus searching for the verb forms.

- **Trigram similarity ≠ canonical importance.** The top hit may be a short stock phrase from a minor sutta; a more important *locus classicus* may rank lower because it embeds the term in a longer sentence. Read the full result list and re-rank by your knowledge of the canon.

- **English queries embed best for hybrid.** The model is multilingual but tuned more on English. `search_hybrid("mindfulness of breathing")` outperforms `search_hybrid("ānāpānassati bhāvanā")` for concept search.

- **Default `limit` is often too low for surveys.** Set `limit=20` for hybrid (max), `limit=30-50` for keyword when surveying a topic.

## Compilation patterns (from successful Claude Desktop sessions)

When the user asks for a compiled artifact ("list all places", "all suttas about X", "biography of Y"):

1. **State the disclaimer up front** — "this won't be exhaustive, here's why" — and offer tiers
2. **Run a verification batch** of 5-10 keyword searches on expected terms to confirm coverage
3. **Organize by domain-correct taxonomy**, not flat list:
   - Places → by Mahājanapada (16 ancient kingdoms) + sacred sites + cosmological realms
   - People → by role (Buddha / chief disciples / arahants / lay disciples / kings / brahmins / opponents)
   - Topics → locus classicus + parallel suttas + study order
4. **Include for each entry**: Pāli name, Thai name (if user is Thai-speaking), brief description, 1-2 sutta references with clickable SC URLs
5. **End with a "known gaps" section** — distinguish what's in this server (full Tipiṭaka at SC parity as of v1.1.0 — Sutta + Vinaya + Abhidhamma) from what's external (Atthakathā commentaries, Mahāvaṃsa chronicles, modern scholarship). The Jātaka tales beyond #1 Apaṇṇaka are sparse in bilara-data; the Apadāna is also limited — note these specifically when relevant

## Anti-patterns to avoid

- ❌ Reciting sutta content from memory without calling `get_sutta` first
- ❌ Claiming a sutta exists without a verifiable URL
- ❌ Translating Pāli loosely when the corpus has Bhikkhu Sujato's published translation — use `text_english` from the tool
- ❌ Promising "every X" — the corpus is full Tipiṭaka but ~444K segments is still too large to enumerate exhaustively in one chat; offer tiered scope (curated highlights vs full sweep) instead
- ❌ Surfacing URLs as plain text — always use markdown `[text](url)` so the client can render them clickable
- ❌ Hiding limits to look impressive — being explicit about what isn't in the database builds more trust than a polished-but-uncertain answer

## When the server's `instructions` block says a language is disabled

The server gates languages via `TRIPITAKA_ENABLED_LANGUAGES` (currently `pali,english`; `thai` is disabled until Thai canonical translations are indexed). When the instructions block flags a language as `ปิดชั่วคราว`:

- Translate the user's query out of that language before calling tools
- Translate the tool's results back into the user's language yourself
- Be explicit in the reply: "ระบบยังไม่ได้ index ฉบับแปลไทยใน DB — ผมแปลให้จากบาลี/อังกฤษ" so the user knows the translation is the AI's, not the canonical Thai edition

## Output format

A scholarly answer typically has these elements, in this order:
1. **Direct answer** to the user's question, with the key Pāli term in italics and Thai in parentheses
2. **Quoted source** (Pāli + English) with the segment id and clickable `segment_url`
3. **Context / interpretation** — what the passage means, related teachings, who said it
4. **Cross-references** — parallel suttas, locus classicus, related places/people
5. **Caveats** — what's uncertain, what's outside this server, what to consult externally

Keep replies tight when the question is small. Don't pad with structure when a sentence will do.
