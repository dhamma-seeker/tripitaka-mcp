"""Tripitaka Reader — bilingual Pāli/English web viewer.

Run locally:
    uvicorn reader.app:app --reload --port 8090

Routes (all under /read/* namespace so apex Caddy can proxy a single path):
    GET  /read/healthz                 → liveness probe
    GET  /read/                        → browse tree (pitakas → nikayas)
    GET  /read/browse/{nikaya_code}    → list of books + suttas in a nikāya
    GET  /read/static/*                → CSS, fonts, etc.
    GET  /read/{sutta_id}              → bilingual reader (Pāli + English)

For local dev convenience, root `/` redirects to `/read/`. In production the
apex Caddy site handles `/` (landing) and only proxies `/read/*` to this app.
"""

from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Any

# Register MIME types that aren't in the stdlib defaults on every platform.
# StaticFiles relies on `mimetypes.guess_type()`, and the slim Python image
# we use in production doesn't ship with .webp registered — without this,
# the hero image gets served as text/plain and Safari/Firefox refuse to
# render it. Register before app construction so StaticFiles sees it.
mimetypes.add_type("image/webp", ".webp")

# Safe at module level: `reader*` is excluded from the installable package
# (pyproject), so this never reaches the lean local-install that must stay free
# of psycopg2. db/connection.py imports it lazily for exactly that reason.
from psycopg2.pool import PoolError

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from reader.featured import FEATURED_SUTTAS
from reader.queries import (
    check_words_have_entries,
    fetch_definitions_embed,
    fetch_neighbors,
    fetch_nikaya,
    fetch_segment_pali,
    fetch_structure,
    fetch_sutta,
    lookup_word,
    parse_sources,
    render_markup,
    term_forms,
    search_text,
    tokenize_pali,
)
from reader.sutta_id_decoder import decode_sutta_id

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
# Pedagogical: every <code class="sid"> tooltip teaches the canonical-ID
# format by decoding it. New users absorb the system through repeated
# exposure rather than needing to read a docs page first.
templates.env.filters["decode_sid"] = decode_sutta_id
# Segment text carries bilara-data's inline `<b>`; render it rather than
# printing the tag. See render_markup — it escapes first, so this is not
# the same as marking the field safe.
templates.env.filters["markup"] = render_markup

# Validate identifiers tightly — DB only has lowercase alphanumerics, dots,
# and hyphens (e.g. mn128, pli-tv-bu-vb-pj1, mil3.1.1). Reject anything else
# at the route boundary so we never form ill-formed SQL parameters.
_SUTTA_ID_RE = re.compile(r"^[a-z0-9.\-]{1,50}$")
_NIKAYA_CODE_RE = re.compile(r"^[a-z0-9\-]{1,30}$")
# Segments add `:n.m[.k]` suffix on top of sutta_id (e.g. sn56.11:0.2,
# pli-tv-kd1:79.4.131). Cap at 80 chars to cover the deepest known refs.
_SEGMENT_ID_RE = re.compile(r"^[a-z0-9.:\-]{1,80}$")

app = FastAPI(title="Tripitaka Reader", docs_url=None, redoc_url=None)
app.mount(
    "/read/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


@app.get("/read/healthz", response_class=HTMLResponse)
def healthz() -> str:
    return "ok"


@app.get("/")
def root_redirect() -> RedirectResponse:
    # Local dev convenience only — prod apex Caddy handles `/` directly
    return RedirectResponse(url="/read/", status_code=302)


@app.get("/read/", response_class=HTMLResponse)
def browse_index(request: Request) -> HTMLResponse:
    pitakas = fetch_structure()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"pitakas": pitakas, "featured": FEATURED_SUTTAS},
    )


@app.get("/read/jump")
def jump(id: str = "") -> RedirectResponse:
    """Quick-jump form on /read/ posts here. Validates lazily — invalid IDs
    fall through to /read/{sid} which 404s with a clear message. Empty input
    bounces back to landing.
    """
    sid = id.strip().lower()[:50]
    if not sid:
        return RedirectResponse(url="/read/", status_code=302)
    return RedirectResponse(url=f"/read/{sid}", status_code=302)


@app.get("/read/api/word")
def api_word(w: str = "") -> JSONResponse:
    """Dictionary lookup for the double-click tooltip on Pāli text.

    Tight bounds — `w` is trimmed, lower-cased, capped at 60 chars and must
    be at least 2 chars. Returns `{word, definitions, lemma?}` — the optional
    `lemma` object is populated when `lookup_word` resolved an inflected
    form via stem-fallback, so the popup can show "looked up as X (-ena,
    instrumental sg.)" and teach the case while delivering the result.
    """
    w = w.strip().lower()[:60]
    if len(w) < 2:
        return JSONResponse({"word": w, "definitions": []})
    defs, lemma_info = lookup_word(w)
    payload: dict[str, Any] = {"word": w, "definitions": defs}
    if lemma_info is not None:
        payload["lemma"] = lemma_info
    return JSONResponse(
        payload,
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/read/api/segment-words")
def api_segment_words(id: str = "") -> JSONResponse:
    """Per-word entry status for one segment's Pāli text.

    Drives the on-demand indicator that highlights words with a dictionary
    entry — only fires when the user focuses a segment (click/deep-link),
    so a 60-segment sutta on a passive scroll-through costs zero queries.

    Response: `{segment_id, words: [{word, has_entry, lemma?}, ...]}`.
    Aggressive Cache-Control because segment Pāli text is immutable — CDN
    and browser can cache for a long time. CF fronts this so repeat-clicks
    by different users on the same segment hit the edge, not origin.
    """
    sid = id.strip().lower()[:80]
    if not _SEGMENT_ID_RE.match(sid):
        return JSONResponse({"segment_id": sid, "words": []})
    text = fetch_segment_pali(sid)
    if not text:
        return JSONResponse({"segment_id": sid, "words": []})
    tokens = tokenize_pali(text)
    if not tokens:
        return JSONResponse({"segment_id": sid, "words": []})
    status = check_words_have_entries(tokens)
    words_payload = [
        {
            "word": w,
            "has_entry": status[w]["has_entry"],
            **({"lemma": status[w]["lemma"]} if status[w]["lemma"] else {}),
        }
        for w in tokens
    ]
    return JSONResponse(
        {"segment_id": sid, "words": words_payload},
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )


def _int_param(raw: str, default: int, lo: int, hi: int) -> int:
    """Read a numeric query param without ever refusing the request.

    Declaring these as `int` hands FastAPI's validator a veto, and it answers
    junk with a 422 and a JSON body. Fine for an API; wrong here, because this
    page renders inside someone else's iframe and that body shows up as a wall
    of error text where the widget should be. `?limit=` — empty, which any
    templated URL can produce from an unset variable — was enough to trigger
    it. Same reasoning as parse_sources: bad input should widen or fall back,
    never break the panel.
    """
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return max(lo, min(value, hi))


def _citation_url(link_base: str, sutta_id: str, segment_id: str) -> str:
    """Build the citation link for one result.

    `link_base` lets an embedding site send readers to its own reader instead
    of ours. Three placeholders, because sites anchor segments differently:

        {sutta_id}     mn141        the sutta alone
        {segment_id}   mn141:16.3   full canonical id — our reader, SuttaCentral
        {segment_num}  16.3         id minus the sutta prefix — dhamma.gift
                                    anchors on this, e.g.
                                    https://dhamma.gift/read/?q={sutta_id}#{segment_num}

    Falls back to our own reader when absent or rejected.

    SECURITY: this value comes straight off the query string and lands in an
    `href`, so the scheme check is load-bearing — without it
    `?link_base=javascript:...` is reflected XSS on our own origin. Only
    http/https, and only those two, no scheme-relative `//host` either (it
    inherits the current scheme and reads as a path otherwise).
    """
    if not link_base:
        return f"/read/{sutta_id}#{segment_id}"
    lowered = link_base.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return f"/read/{sutta_id}#{segment_id}"
    # Split on the first colon only — ids run `mn141:16.3` but also
    # `pli-tv-kd1:79.4.131`, and the tail can itself contain dots.
    segment_num = segment_id.split(":", 1)[1] if ":" in segment_id else segment_id
    return (
        link_base.replace("{sutta_id}", sutta_id)
        .replace("{segment_num}", segment_num)
        .replace("{segment_id}", segment_id)
    )


@app.get("/read/embed/define", response_class=HTMLResponse)
def embed_define(
    request: Request,
    term: str = "",
    limit: str = "5",
    theme: str = "light",
    link_base: str = "",
    sources: str = "",
    per_sutta: str = "0",
) -> HTMLResponse:
    """Public, iframe-embeddable widget for `define_from_suttas`.

    Unauthenticated by design — read-only, same trust boundary as the rest
    of /read/*. `/read/embed/*` gets a scoped `X-Frame-Options` override in
    the Caddy config (unlike the rest of this app, which is DENY) so this
    specific path can be embedded on allowlisted third-party origins.
    """
    term = term.strip().lower()[:60]
    n_limit = _int_param(limit, default=5, lo=1, hi=5)
    theme = theme if theme in ("light", "dark") else "light"
    link_base = link_base.strip()[:300]
    source_set = parse_sources(sources[:200])
    # 0 (the default) means no cap, so leaving the param off keeps the
    # behaviour every existing embed already has.
    per_sutta_cap = _int_param(per_sutta, default=0, lo=0, hi=n_limit) or None

    # A busy moment shouldn't read as a broken widget. The connection pool holds
    # 10, and this page is now embeddable from anywhere, so enough simultaneous
    # first-time viewers can drain it — measured: 20 concurrent requests, 10
    # served and 10 raising PoolError. Unhandled, FastAPI answers 500 and the
    # host page shows "Internal Server Error" inside the frame, which looks like
    # our fault rather than a passing spike. Caught here so the panel says so
    # plainly and invites a retry.
    busy = False
    try:
        definitions = (
            fetch_definitions_embed(
                term, limit=n_limit, sources=source_set, per_sutta=per_sutta_cap
            )
            if term
            else []
        )
    except PoolError:
        definitions, busy = [], True
    # Resolve links here rather than in the template — keeps the scheme check
    # in one place instead of relying on every future template edit to repeat it.
    for d in definitions:
        d["citation_url"] = _citation_url(
            link_base, d["sutta_id"], d["segment_id"]
        )
        # The anchor line is the match; the passage around it is where the
        # definition actually lives. Drop the anchor from the expandable body
        # so it isn't shown twice.
        d["passage"] = [
            s for s in (d.get("block") or []) if s["segment_id"] != d["segment_id"]
        ]

    # Split so a reader knows what they're getting before they read it: a
    # direct definition and a simile are different kinds of answer. Then group
    # each side by sutta, because a term is often defined several times over in
    # one discourse — five rows for `citta` are four from MN 138 and one from
    # SN 51.20, which reads as five findings until you look at the citations.
    # Sutta sits inside kind rather than outside it: a text can hold both a
    # definition and a simile, and hoisting it would split that kind heading in
    # two. Order follows rank throughout, so the best match stays first and its
    # sutta leads.
    groups = []
    for label, kind, noun in (
        ("Definitions", "direct", "definitions"),
        ("Similes", "simile", "similes"),
    ):
        items = [d for d in definitions if d["kind"] == kind]
        if not items:
            continue
        by_sutta: dict[str, list[dict[str, Any]]] = {}
        for d in items:
            by_sutta.setdefault(d["sutta_id"], []).append(d)
        # The noun travels with the group so the per-sutta count names the kind
        # it is counting. Hardcoding "definitions" told a reader that SN 35.245's
        # four similes for the parrot tree were four definitions of it, which is
        # the opposite of what that sutta does: it depicts kiṁsuka, it never says
        # what kiṁsuka is.
        groups.append((label, noun, list(by_sutta.items())))

    return templates.TemplateResponse(
        request=request,
        name="embed_define.html",
        context={
            "term": term,
            "definitions": definitions,
            "groups": groups,
            # ไฮไลต์รูปผันของศัพท์ในบรรทัดบาลี (Pavel ขอ — เขาทำแบบนี้บน Dhamma.Gift)
            "term_forms": term_forms(term),
            "theme": theme,
            "busy": busy,
        },
        # A busy answer must not be cached for five minutes — that would pin the
        # apology in place long after the spike passed.
        headers={
            "Cache-Control": "no-store" if busy else "public, max-age=300"
        },
    )


@app.get("/read/search", response_class=HTMLResponse)
def search(request: Request, q: str = "") -> HTMLResponse:
    q = q.strip()[:200]
    limit = 50
    results = search_text(q, limit=limit) if q else []
    return templates.TemplateResponse(
        request=request,
        name="search.html",
        context={
            "query": q,
            "results": results,
            "count": len(results),
            "limit": limit,
            "min_chars": 3,
        },
    )


@app.get("/read/browse/{nikaya_code}", response_class=HTMLResponse)
def browse_nikaya(request: Request, nikaya_code: str) -> HTMLResponse:
    nikaya_code = nikaya_code.strip().lower()
    if not _NIKAYA_CODE_RE.match(nikaya_code):
        raise HTTPException(status_code=400, detail="invalid nikaya code")

    data = fetch_nikaya(nikaya_code)
    if data is None:
        raise HTTPException(
            status_code=404, detail=f"nikāya not found: {nikaya_code}"
        )

    return templates.TemplateResponse(
        request=request,
        name="nikaya.html",
        context={"nikaya": data},
    )


@app.get("/read/{sutta_id}", response_class=HTMLResponse)
def read_sutta(request: Request, sutta_id: str) -> HTMLResponse:
    sutta_id = sutta_id.strip().lower()
    if not _SUTTA_ID_RE.match(sutta_id):
        raise HTTPException(status_code=400, detail="invalid sutta_id")

    data = fetch_sutta(sutta_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"sutta not found: {sutta_id}")

    neighbors = fetch_neighbors(sutta_id)

    return templates.TemplateResponse(
        request=request,
        name="sutta.html",
        context={"sutta": data, "neighbors": neighbors},
    )
