# 🚢 Tripitaka MCP — Deployment Runbook

คู่มือการ deploy ขึ้น staging → production บน DigitalOcean
(Caddy reverse proxy + readonly DB + rate limit + Cloudflare)

---

## 📋 Gate 1 — Staging Deploy Checklist

### 0. Prerequisites (บน laptop)

- [ ] [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [ ] SSH key ใหม่สำหรับ production (แยกจาก personal):

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/tripitaka_prod -C "tripitaka-deploy"
  ```

- [ ] DigitalOcean API token: [cloud.digitalocean.com/account/api/tokens](https://cloud.digitalocean.com/account/api/tokens)
- [ ] Domain ที่เพิ่มใน DO DNS หรือ Cloudflare แล้ว

### 1. Provision droplet ด้วย Terraform

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# แก้ do_token, public_key_path, domain_name

# ดู IP ตัวเองเพื่อจำกัด SSH:
curl ifconfig.me
# เพิ่มใน tfvars: ssh_allowed_cidrs = ["YOUR.IP/32"]

terraform init
terraform plan      # ตรวจก่อน apply
terraform apply     # ยืนยันด้วย yes — รอประมาณ 3-5 นาที
```

Output จะแสดง droplet IP + คำสั่ง SSH

### 2. ตั้ง DNS

ชี้ `A record` ของโดเมน (เช่น `mcp.example.org`) → droplet IP

- ถ้าใช้ **Cloudflare**: เปิด proxy (icon ส้ม) เพื่อซ่อน origin IP
- ถ้าใช้ **DO DNS**: terraform สร้าง A record ให้แล้ว

ตรวจด้วย: `dig mcp.example.org` ต้องคืน droplet IP

### 3. SSH เข้า droplet แล้ว deploy

```bash
ssh deploy@<DROPLET_IP>          # ใช้ user deploy ไม่ใช่ root
cd /opt/tripitaka
git clone https://github.com/dhamma-seeker/tripitaka-mcp.git .
./scripts/deploy.sh --domain mcp.example.org
```

สคริปต์จะ:

1. สร้าง `.env` ด้วย password สุ่ม
2. ดาวน์โหลด dump จาก Hugging Face
3. Restore DB
4. ตั้ง `tripitaka_ro` readonly user
5. Build + start docker-compose.prod.yml
6. รอ Caddy ขอ Let's Encrypt cert

### 4. Verify จาก laptop

```bash
# จาก laptop
./scripts/smoke_test.sh https://mcp.example.org
```

ต้องผ่านทุก check:

- ✓ DNS resolves
- ✓ TLS cert valid
- ✓ /health → ok
- ✓ security headers (HSTS, X-Content-Type-Options, etc.)
- ✓ Server header ถูกซ่อน
- ✓ rate limit ทำงาน (มี 429 เมื่อ burst)
- ✓ /sse → text/event-stream

### 5. ทดสอบ MCP tools จริง

Claude Desktop ปัจจุบัน **ไม่รองรับ remote SSE โดยตรง** ต้องใช้ [`mcp-remote`](https://www.npmjs.com/package/mcp-remote)
bridge SSE → stdio ให้

เพิ่มใน `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripitaka-staging": {
      "command": "/Users/YOU/.nvm/versions/node/v22.x/bin/npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.example.org/sse",
        "--transport",
        "sse-only"
      ],
      "env": {
        "PATH": "/Users/YOU/.nvm/versions/node/v22.x/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**ข้อควรรู้:**

- `command` ต้อง**ระบุ path เต็ม**ของ `npx` (Claude Desktop ไม่เห็น `PATH` ของ shell) — หา path ด้วย `which npx`
- `env.PATH` จำเป็นเมื่อใช้ **nvm**: ไม่งั้น `node` อาจ resolve ไปเวอร์ชันอื่นที่ไม่มี `node:path` module (เวอร์ชันเก่า)
- `--transport sse-only` บังคับใช้ SSE — ถ้าไม่ใส่ mcp-remote จะลอง Streamable HTTP ก่อนแล้วได้ 502
- ดูตัวอย่างเต็มที่: [`claude_desktop_config.example.json`](./claude_desktop_config.example.json)

Restart Claude แล้วลอง:

- `search_hybrid("metta")` — ต้องคืนผลลัพธ์
- `get_word_definition("sati")` — ต้องมี attribution
- `get_sutta("mn1")` — ต้องคืนเนื้อหา

---

## 📋 Gate 2 — Production Promotion

### Cloudflare hardening (free tier)

DNS → Proxied (orange cloud):

- **Security → WAF → Rate limiting rules**: เพิ่ม rule `50 req / 10min / IP → Challenge`
- **Security → Bots → Bot Fight Mode**: On
- **Security → Settings → Security Level**: Medium
- **Speed → Optimization → Caching**: Standard
- **SSL/TLS → Overview**: Full (strict)
- **SSL/TLS → Edge Certificates → Always Use HTTPS**: On
- **SSL/TLS → Edge Certificates → Minimum TLS Version**: 1.2

### Telegram Alert Bridge (monitoring)

รับ webhook จาก UptimeRobot + DigitalOcean → forward เข้า Telegram group

#### 1. สร้าง Telegram bot + หา chat id

- แชทกับ [@BotFather](https://t.me/botfather) → `/newbot` → ได้ **bot token**
- สร้าง group, invite bot เข้ามา, ส่งข้อความสักข้อความ
- เปิด `https://api.telegram.org/bot<TOKEN>/getUpdates` → หา `"chat":{"id":...}` (group จะเป็นเลขติดลบ)

#### 2. เพิ่มตัวแปรใน `.env`

```bash
TG_BOT_TOKEN=123456:ABCxxxx
TG_CHAT_ID=-1001234567890
WEBHOOK_SECRET=$(openssl rand -hex 32)   # random 32-byte hex
```

#### 3. Deploy (จะขึ้น service `alert-bridge` เพิ่มมา)

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

#### 4. ทดสอบจาก laptop

```bash
curl -X POST "https://mcp.example.org/webhooks/uptime/<SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"monitorFriendlyName":"test","alertType":"1","alertDetails":"manual test"}'
```

ควรเห็นข้อความใน Telegram group ภายใน 1-2 วินาที

#### 5. ตั้งค่า UptimeRobot

- Dashboard → Monitors → New Monitor → `HTTPS`, URL = `https://mcp.example.org/health`
- Interval 5 min
- Alert Contacts → Add → Type **Webhook**
  - URL: `https://mcp.example.org/webhooks/uptime/<SECRET>`
  - POST Value (JSON): ใช้ macros ของ UptimeRobot

    ```json
    {
      "monitorFriendlyName": "*monitorFriendlyName*",
      "monitorURL": "*monitorURL*",
      "alertType": "*alertType*",
      "alertDetails": "*alertDetails*"
    }
    ```

  - ติ๊ก "Send as JSON"

#### 6. ตั้งค่า DigitalOcean Alert Policy

- Monitoring → Alert Policies → Create → เลือก metric (CPU 80% / Memory 90% / Disk 85%)
- Notification → Slack (**ไม่ใช่ native Telegram**) — DO เรียก Slack webhook format
  - URL: `https://mcp.example.org/webhooks/do/<SECRET>`
  - (alert-bridge parse payload ที่ได้มา defensive จะ render ข้อความภาษาไทยเอง)

#### Troubleshooting

- `docker logs tripitaka-alert-bridge` — ดู log ว่า webhook เข้ามาหรือยัง
- ถ้าเห็น `secret mismatch` → SECRET ใน URL ไม่ตรงกับ `.env`
- ถ้า Telegram ไม่ส่ง → ตรวจ TG_BOT_TOKEN/TG_CHAT_ID ด้วย curl test ใน step 4

### Backup automation (ยังไม่ได้ทำ — ดู todo)

Cron บน droplet: `pg_dump` → DO Spaces ทุกวัน เก็บ 7 วัน

### Monitoring

- **UptimeRobot** free: HTTPS ping `/health` ทุก 5 นาที → alert email/Discord
- **DigitalOcean billing alert**: ตั้งที่ $25/mo

---

## 🔄 Operations

### ดู logs

```bash
docker compose -f docker-compose.prod.yml logs -f              # all
docker compose -f docker-compose.prod.yml logs -f mcp-server   # เฉพาะ server
docker compose -f docker-compose.prod.yml logs -f caddy        # access logs + TLS
```

### Restart

```bash
# restart ทั้ง stack
docker compose -f docker-compose.prod.yml restart

# restart เฉพาะ service
docker compose -f docker-compose.prod.yml restart mcp-server
```

### Update (pull code ใหม่)

```bash
cd /opt/tripitaka
git pull
./scripts/deploy.sh                  # reuses existing .env
```

### Rollback

```bash
cd /opt/tripitaka
git log --oneline -10
git checkout <commit-sha>
./scripts/deploy.sh
```

### Restore จาก backup

```bash
# stop mcp-server ก่อน (กัน read ขณะ restore)
docker compose -f docker-compose.prod.yml stop mcp-server

# drop + restore
docker exec tripitaka-db psql -U admin -d tripitaka_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -i tripitaka-db pg_restore -U admin -d tripitaka_db --no-owner --no-acl < backup.dump

# ตั้ง readonly user ใหม่ (dump อาจมี role เก่า)
docker exec -i tripitaka-db psql -U admin -d tripitaka_db < scripts/setup_readonly_user.sql
docker exec tripitaka-db psql -U admin -d tripitaka_db \
    -c "ALTER ROLE tripitaka_ro PASSWORD '$(grep TRIPITAKA_RO_PASSWORD .env | cut -d= -f2)'"

# restart
docker compose -f docker-compose.prod.yml up -d
```

### ดู abuse patterns

```bash
# top IPs ใน access log
docker logs tripitaka-caddy 2>&1 | jq -r '.request.remote_ip' | sort | uniq -c | sort -rn | head
```

---

## 🩺 Troubleshooting

### `/sse` คืน 502 จาก Caddy

สาเหตุที่พบบ่อย:

1. **mcp-server bind `127.0.0.1`** — ใน `.env` ต้อง `MCP_HOST=0.0.0.0` ไม่งั้น Caddy container อื่นเชื่อมไม่ได้
   - เช็ค: `docker logs tripitaka-mcp-server | grep 'Uvicorn running'` ต้องเห็น `http://0.0.0.0:8080`
2. **MCP_TRANSPORT=stdio** — ต้องเป็น `sse` (ไม่งั้นไม่มี HTTP port เปิดเลย)
3. **Port mismatch** — Caddy proxy ไป `:8080` แต่ server ฟัง `:8000` (default ถ้าไม่ตั้ง `MCP_PORT`)

### SSH เชื่อมไม่ได้ (Connection refused) หลังจากที่เคยเข้าได้

IP สาธารณะของคุณเปลี่ยน (VPN / มือถือ / ISP) → DO firewall `ssh_allowed_cidrs` บล็อก
แก้: อัปเดต IP ใหม่ใน [infra/terraform.tfvars](infra/terraform.tfvars) แล้ว
`terraform apply -target=digitalocean_firewall.main`

### Claude Desktop: `Cannot find module 'node:path'`

Claude Desktop เรียก `node` เวอร์ชันเก่า (< 16) ซึ่งไม่มี `node:` protocol
แก้: ระบุ `PATH` เต็มใน `env` ที่ชี้ไป node ≥ 18 และ/หรือ `nvm alias default 22`

### Claude Desktop: `Streamable HTTP error: Non-200 status code (502)`

`mcp-remote` พยายามใช้ Streamable HTTP ก่อน แต่ server เราให้ SSE เท่านั้น
แก้: เพิ่ม `--transport sse-only` ใน args

---

## ⚠️ ข้อควรระวัง

1. **ทรัพยากร**: RAM 4GB แนะนำ (swap 2GB ช่วยเสริม — cloud-init ตั้งไว้แล้ว)
   ดูประเมินความจุและแนวทาง scale: [docs/CAPACITY.md](./docs/CAPACITY.md)
2. **ห้าม commit `.env`**: `chmod 600` + เก็บสำรองใน password manager
3. **Dump file**: ~500MB-1GB — ลบออกหลัง restore เสร็จ (`rm tripitaka_production_data.dump`) ประหยัด disk
4. **Let's Encrypt rate limit**: ถ้า deploy ผิดซ้ำๆ อาจโดน ban 1 สัปดาห์ — ทดสอบด้วย `--staging` ก่อนถ้าไม่แน่ใจ
