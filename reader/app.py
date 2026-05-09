"""Tripitaka Reader — bilingual Pāli/English web viewer.

Run locally:
    uvicorn reader.app:app --reload --port 8090

Routes:
    GET  /                  → landing redirect (placeholder)
    GET  /healthz           → liveness probe
    GET  /read/{sutta_id}   → bilingual reader (Pāli + English segments)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from reader.queries import fetch_sutta

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Tripitaka Reader", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/healthz", response_class=HTMLResponse)
def healthz() -> str:
    return "ok"


@app.get("/")
def index() -> RedirectResponse:
    # MVP-min: รากของ reader ยังไม่มี landing — ส่งไปสูตรตัวอย่าง
    return RedirectResponse(url="/read/dn16", status_code=302)


@app.get("/read/{sutta_id}", response_class=HTMLResponse)
def read_sutta(request: Request, sutta_id: str) -> HTMLResponse:
    sutta_id = sutta_id.strip().lower()
    if not sutta_id or len(sutta_id) > 50:
        raise HTTPException(status_code=400, detail="invalid sutta_id")

    data = fetch_sutta(sutta_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"sutta not found: {sutta_id}")

    return templates.TemplateResponse(
        request=request,
        name="sutta.html",
        context={"sutta": data},
    )
