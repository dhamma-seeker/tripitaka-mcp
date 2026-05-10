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

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from reader.featured import FEATURED_SUTTAS
from reader.queries import (
    fetch_neighbors,
    fetch_nikaya,
    fetch_structure,
    fetch_sutta,
    lookup_word,
    search_text,
)
from reader.sutta_id_decoder import decode_sutta_id

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
# Pedagogical: every <code class="sid"> tooltip teaches the canonical-ID
# format by decoding it. New users absorb the system through repeated
# exposure rather than needing to read a docs page first.
templates.env.filters["decode_sid"] = decode_sutta_id

# Validate identifiers tightly — DB only has lowercase alphanumerics, dots,
# and hyphens (e.g. mn128, pli-tv-bu-vb-pj1, mil3.1.1). Reject anything else
# at the route boundary so we never form ill-formed SQL parameters.
_SUTTA_ID_RE = re.compile(r"^[a-z0-9.\-]{1,50}$")
_NIKAYA_CODE_RE = re.compile(r"^[a-z0-9\-]{1,30}$")

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
    be at least 2 chars. Returns `{word, definitions: [{source, language,
    text}]}` so the frontend can render a small popup card without further
    parsing. Cache-Control short to keep responses snappy on repeat clicks.
    """
    w = w.strip().lower()[:60]
    if len(w) < 2:
        return JSONResponse({"word": w, "definitions": []})
    defs = lookup_word(w)
    return JSONResponse(
        {"word": w, "definitions": defs},
        headers={"Cache-Control": "public, max-age=300"},
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
