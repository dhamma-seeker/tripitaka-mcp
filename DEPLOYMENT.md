# 🚢 Tripitaka MCP — Deployment Runbook

คู่มือการ deploy ขึ้น staging → production บน VPS ใดก็ได้ที่รัน Docker
(Caddy reverse proxy + readonly DB + rate limit + Cloudflare)

> ไฟล์นี้เป็น **generic runbook** สำหรับคนที่ต้องการ fork/deploy instance ของตัวเอง
> ตัวอย่างที่ให้ใช้ `example.org` — แทนด้วยโดเมนจริงของคุณ
> Infra reference ใน [`infra/`](infra/) เขียนเป็น Terraform สำหรับ DigitalOcean —
> ปรับให้เข้ากับ cloud provider ที่คุณใช้ได้ (AWS, GCP, Linode, ฯลฯ)

---

## 📋 Gate 1 — Staging Deploy Checklist

### 0. Prerequisites (บน laptop)

- [ ] [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [ ] SSH key ใหม่สำหรับ production (แยกจาก personal):

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/tripitaka_prod -C "tripitaka-deploy"
  ```

- [ ] Cloud provider API token (ถ้าใช้ Terraform ใน repo นี้ — provider = DigitalOcean; เปลี่ยน provider ได้)
- [ ] Domain ที่ชี้ NS มาที่ DNS provider ที่รองรับ (Cloudflare / cloud-provider DNS / etc.)

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

ชี้ `A record` ของโดเมน (เช่น `mcp.example.org`) → VPS IP

- ถ้าใช้ **Cloudflare**: เปิด proxy (icon ส้ม) เพื่อซ่อน origin IP
- ถ้าใช้ **cloud provider DNS** ในตัว: Terraform ใน repo นี้สร้าง A record ให้แล้ว (สำหรับ DO)

ตรวจด้วย: `dig mcp.example.org` ต้องคืน VPS IP

### 3. SSH เข้า VPS แล้ว deploy

```bash
ssh deploy@<VPS_IP>              # ใช้ user deploy ไม่ใช่ root
cd /opt/tripitaka
git clone <REPO_URL> .
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

### Monitoring + Alerts

แนะนำตั้ง **3 ระดับ** (ทุก cloud provider มีให้ใน native tools):

1. **Uptime check** — HTTPS `GET /health` ทุก 1-5 นาที จาก ≥2 regions → alert เมื่อ fail
2. **VPS metrics** — CPU >80%, Memory >85%, Disk >80% (window 5 นาที) → alert
3. **Billing alert** — ตั้ง threshold monthly spend → email

ส่ง alert เข้าช่องทางที่สะดวก: Slack / email / PagerDuty / Discord
(cloud provider ส่วนใหญ่มี native integration ให้เลือก)

### Backup automation

Cron บน VPS: `pg_dump` → **S3-compatible object storage** ทุกวัน เก็บ N วัน
ดูสคริปต์: [`scripts/backup.sh`](scripts/backup.sh) (รองรับ S3 ทุกเจ้า: AWS S3, DO Spaces, Cloudflare R2, MinIO, ฯลฯ — ตั้งผ่าน env vars)

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

IP สาธารณะของคุณเปลี่ยน (VPN / มือถือ / ISP) → cloud firewall `ssh_allowed_cidrs` บล็อก
แก้: อัปเดต IP ใหม่ใน [infra/terraform.tfvars](infra/terraform.tfvars) แล้ว
`terraform apply -target=<firewall_resource>` (ดูชื่อ resource ใน `infra/main.tf`)

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
