"""
Tripitaka Alert Bridge — Webhook to Telegram

รับ webhook จาก UptimeRobot และ DigitalOcean แล้ว forward เป็นข้อความภาษาไทย
เข้า Telegram group ผ่าน Bot API

Endpoints:
    GET  /health                       — liveness probe
    POST /webhooks/uptime/{secret}     — UptimeRobot custom webhook
    POST /webhooks/do/{secret}         — DigitalOcean alert webhook

Env:
    TG_BOT_TOKEN    — จาก @BotFather
    TG_CHAT_ID      — chat id ของ group (ติดลบ สำหรับ group)
    WEBHOOK_SECRET  — random token (openssl rand -hex 32) — ใส่ใน URL path
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from html import escape

import httpx
from fastapi import FastAPI, HTTPException, Request

TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

TG_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("alert_bridge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(timeout=10.0) as client:
        app.state.http = client
        log.info("alert_bridge started")
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


def verify_secret(secret: str, client_ip: str) -> None:
    # compare_digest กัน timing attack
    if not secrets.compare_digest(secret, WEBHOOK_SECRET):
        log.warning("webhook secret mismatch from %s", client_ip)
        # คืน 404 ไม่ใช่ 401 — ไม่บอกว่ามี endpoint นี้อยู่
        raise HTTPException(status_code=404, detail="Not Found")


async def send_telegram(text: str) -> None:
    try:
        r = await app.state.http.post(
            TG_API,
            json={
                "chat_id": TG_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.error("telegram send failed: %s", e)


def _get(d: dict, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/webhooks/uptime/{secret}")
async def uptime_webhook(secret: str, req: Request):
    verify_secret(secret, req.client.host if req.client else "?")
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    name = _get(data, "monitorFriendlyName", "monitor_friendly_name", default="Unknown")
    url = _get(data, "monitorURL", "monitor_url")
    alert_type = str(_get(data, "alertType", "alert_type"))
    details = _get(data, "alertDetails", "alert_details")

    # UptimeRobot alertType: 1=down, 2=up
    if alert_type == "1":
        header = "🔴 <b>UptimeRobot — เว็บล่ม</b>"
    elif alert_type == "2":
        header = "🟢 <b>UptimeRobot — เว็บกลับมาแล้ว</b>"
    else:
        header = f"⚠️ <b>UptimeRobot — เหตุการณ์ ({escape(alert_type) or 'unknown'})</b>"

    lines = [header, ""]
    lines.append(f"<b>Monitor:</b> {escape(str(name))}")
    if url:
        lines.append(f"<b>URL:</b> {escape(str(url))}")
    if details:
        lines.append(f"<b>รายละเอียด:</b> {escape(str(details))}")

    await send_telegram("\n".join(lines))
    return {"ok": True}


@app.post("/webhooks/do/{secret}")
async def do_webhook(secret: str, req: Request):
    verify_secret(secret, req.client.host if req.client else "?")
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # DO payload มักมี "alert" ซ้อนอยู่ — defensive parse
    alert = data.get("alert") if isinstance(data.get("alert"), dict) else data

    description = _get(alert, "description", default="DigitalOcean alert")
    droplet = _get(alert, "droplet_name", "resource_name")
    region = _get(alert, "region")
    policy = alert.get("policy") if isinstance(alert.get("policy"), dict) else {}
    metric = _get(policy, "description", "compare")

    lines = ["🚨 <b>DigitalOcean Alert</b>", ""]
    lines.append(f"<b>เหตุการณ์:</b> {escape(str(description))}")
    if metric:
        lines.append(f"<b>Metric:</b> {escape(str(metric))}")
    if droplet:
        lines.append(f"<b>Droplet:</b> {escape(str(droplet))}")
    if region:
        lines.append(f"<b>Region:</b> {escape(str(region))}")

    await send_telegram("\n".join(lines))
    return {"ok": True}
