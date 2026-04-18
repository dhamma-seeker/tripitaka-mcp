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

ใน Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripitaka": {
      "url": "https://mcp.example.org/sse"
    }
  }
}
```

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

## ⚠️ ข้อควรระวัง

1. **ทรัพยากร**: RAM 4GB แนะนำ (swap 2GB ช่วยเสริม — cloud-init ตั้งไว้แล้ว)
2. **ห้าม commit `.env`**: `chmod 600` + เก็บสำรองใน password manager
3. **Dump file**: ~500MB-1GB — ลบออกหลัง restore เสร็จ (`rm tripitaka_production_data.dump`) ประหยัด disk
4. **Let's Encrypt rate limit**: ถ้า deploy ผิดซ้ำๆ อาจโดน ban 1 สัปดาห์ — ทดสอบด้วย `--staging` ก่อนถ้าไม่แน่ใจ
