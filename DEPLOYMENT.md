# 🚢 Tripitaka MCP — Deployment Runbook

Guide for deploying to staging → production on any VPS that runs Docker
(Caddy reverse proxy + readonly DB + rate limit + Cloudflare).

> This file is a **generic runbook** for anyone forking to deploy their own instance.
> Examples use `example.org` — replace with your real domain.
> The infra reference in [`infra/`](infra/) is written as Terraform for DigitalOcean —
> adapt to whichever cloud provider you use (AWS, GCP, Linode, etc.).

---

## 📋 Gate 1 — Staging Deploy Checklist

### 0. Prerequisites (on your laptop)

- [ ] [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5
- [ ] A new SSH key for production (separate from your personal key):

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/tripitaka_prod -C "tripitaka-deploy"
  ```

- [ ] Cloud provider API token (if using the Terraform in this repo — default provider is DigitalOcean; you can switch)
- [ ] A domain whose NS points to a supported DNS provider (Cloudflare / cloud-provider DNS / etc.)

### 1. Provision the VPS with Terraform

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in do_token, public_key_path, domain_name

# Find your own IP to lock down SSH:
curl ifconfig.me
# Add to tfvars: ssh_allowed_cidrs = ["YOUR.IP/32"]

terraform init
terraform plan      # Review before applying
terraform apply     # Confirm with `yes` — takes about 3–5 minutes
```

The output shows the VPS IP + SSH command.

### 2. Configure DNS

Point an `A record` for your domain (e.g. `mcp.example.org`) → VPS IP.

- If using **Cloudflare**: enable the proxy (orange icon) to hide the origin IP
- If using your **cloud provider's DNS**: the Terraform in this repo creates the A record for you (DO case)

Verify with: `dig mcp.example.org` — should return the VPS IP.

### 3. SSH in and deploy

```bash
ssh deploy@<VPS_IP>              # Use the `deploy` user, not root
cd /opt/tripitaka
git clone <REPO_URL> .
./scripts/deploy.sh --domain mcp.example.org
```

The script will:

1. Generate `.env` with random passwords
2. Download the dump from Hugging Face
3. Restore the DB
4. Set up the `tripitaka_ro` readonly user
5. Build + start docker-compose.prod.yml
6. Wait for Caddy to obtain the Let's Encrypt certificate

### 4. Verify from your laptop

```bash
# From your laptop
./scripts/smoke_test.sh https://mcp.example.org
```

All checks should pass:

- ✓ DNS resolves
- ✓ TLS cert valid
- ✓ /health → ok
- ✓ security headers (HSTS, X-Content-Type-Options, etc.)
- ✓ Server header hidden
- ✓ rate limit works (returns 429 on burst)
- ✓ /sse → text/event-stream

### 5. Test real MCP tools

Claude Desktop bridges remote MCP servers through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote). The server exposes both transports — pick whichever your client prefers.

Add to `claude_desktop_config.json` (Streamable HTTP, recommended):

```json
{
  "mcpServers": {
    "tripitaka-staging": {
      "command": "/Users/YOU/.nvm/versions/node/v22.x/bin/npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.example.org/mcp"
      ],
      "env": {
        "PATH": "/Users/YOU/.nvm/versions/node/v22.x/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

To force the legacy SSE transport instead, change the URL to `.../sse` and add `"--transport", "sse-only"` to `args`. See [`claude_desktop_config.example.json`](./claude_desktop_config.example.json) for both side by side.

**Things to know:**

- `command` must be the **full path** to `npx` (Claude Desktop doesn't see your shell's `PATH`) — find it with `which npx`
- `env.PATH` is required when using **nvm**: otherwise `node` may resolve to an older version that lacks the `node:path` module
- `--transport sse-only` forces SSE — without it, mcp-remote tries Streamable HTTP first and gets 502
- Full annotated example: [`claude_desktop_config.example.json`](./claude_desktop_config.example.json)

Restart Claude and try:

- `search_hybrid("metta")` — should return results
- `get_word_definition("sati")` — should include attribution
- `get_sutta("mn1")` — should return content

---

## 📋 Gate 2 — Production Promotion

### Cloudflare hardening (free tier)

DNS → Proxied (orange cloud):

- **Security → WAF → Rate limiting rules**: add rule `50 req / 10min / IP → Challenge`
- **Security → Bots → Bot Fight Mode**: On
- **Security → Settings → Security Level**: Medium
- **Speed → Optimization → Caching**: Standard
- **SSL/TLS → Overview**: Full (strict)
- **SSL/TLS → Edge Certificates → Always Use HTTPS**: On
- **SSL/TLS → Edge Certificates → Minimum TLS Version**: 1.2

### Monitoring + Alerts

Set up **three layers** (every cloud provider has native tools for these):

1. **Uptime check** — HTTPS `GET /health` every 1–5 minutes from ≥2 regions → alert on failure
2. **VPS metrics** — CPU >80%, Memory >85%, Disk >80% (5-minute window) → alert
3. **Billing alert** — set a monthly spend threshold → email

Route alerts to wherever is convenient: Slack / email / PagerDuty / Discord
(most cloud providers offer native integrations).

### Backup automation

Cron on the VPS: `pg_dump` → **S3-compatible object storage** daily, keep N days.
See the script: [`scripts/backup.sh`](scripts/backup.sh) (works with any S3 provider: AWS S3, DO Spaces, Cloudflare R2, MinIO, etc. — configured via env vars).

---

## 🔄 Operations

### View logs

```bash
docker compose -f docker-compose.prod.yml logs -f              # all
docker compose -f docker-compose.prod.yml logs -f mcp-server   # server only
docker compose -f docker-compose.prod.yml logs -f caddy        # access logs + TLS
```

### Restart

```bash
# restart the whole stack
docker compose -f docker-compose.prod.yml restart

# restart a single service
docker compose -f docker-compose.prod.yml restart mcp-server
```

### Update (pull latest code)

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

### Restore from backup

```bash
# Stop mcp-server first (prevent reads during restore)
docker compose -f docker-compose.prod.yml stop mcp-server

# Drop + restore
docker exec tripitaka-db psql -U admin -d tripitaka_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -i tripitaka-db pg_restore -U admin -d tripitaka_db --no-owner --no-acl < backup.dump

# Re-create the readonly user (dump may carry an old role)
docker exec -i tripitaka-db psql -U admin -d tripitaka_db < scripts/setup_readonly_user.sql
docker exec tripitaka-db psql -U admin -d tripitaka_db \
    -c "ALTER ROLE tripitaka_ro PASSWORD '$(grep TRIPITAKA_RO_PASSWORD .env | cut -d= -f2)'"

# Restart
docker compose -f docker-compose.prod.yml up -d
```

### Watch for abuse patterns

```bash
# Top IPs in access log
docker logs tripitaka-caddy 2>&1 | jq -r '.request.remote_ip' | sort | uniq -c | sort -rn | head
```

---

## 🩺 Troubleshooting

### `/sse` returns 502 from Caddy

Common causes:

1. **mcp-server bound to `127.0.0.1`** — `.env` must set `MCP_HOST=0.0.0.0`, otherwise the Caddy container can't connect
   - Check: `docker logs tripitaka-mcp-server | grep 'Uvicorn running'` — should show `http://0.0.0.0:8080`
2. **`MCP_TRANSPORT=stdio`** — must be `sse` (otherwise there's no HTTP port open at all)
3. **Port mismatch** — Caddy proxies to `:8080` but the server listens on `:8000` (the default when `MCP_PORT` isn't set)

### SSH refused (Connection refused) after previously working

Your public IP changed (VPN / mobile / ISP) → the cloud firewall `ssh_allowed_cidrs` blocks you.
Fix: update the new IP in [infra/terraform.tfvars](infra/terraform.tfvars), then run
`terraform apply -target=<firewall_resource>` (find the resource name in `infra/main.tf`).

### Claude Desktop: `Cannot find module 'node:path'`

Claude Desktop is running an older `node` (< 16) that lacks the `node:` protocol.
Fix: set the full `PATH` in `env` to point at node ≥ 18, and/or run `nvm alias default 22`.

### Claude Desktop: `Streamable HTTP error: Non-200 status code (502)`

`mcp-remote` tries Streamable HTTP first, but our server only offers SSE.
Fix: add `--transport sse-only` to args.

---

## ⚠️ Things to Watch

1. **Resources**: 4 GB RAM recommended (with 2 GB swap as a safety net — already set by cloud-init).
   For capacity estimates and scaling guidance: [docs/CAPACITY.md](./docs/CAPACITY.md)
2. **Never commit `.env`**: `chmod 600` and keep a backup in a password manager
3. **Dump file**: ~500 MB–1 GB — remove after restoring (`rm tripitaka_production_data.dump`) to save disk
4. **Let's Encrypt rate limit**: repeated failed deploys can get you banned for a week — test with `--staging` first if unsure
