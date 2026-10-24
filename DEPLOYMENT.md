# 🚢 Tripitaka MCP — Deployment Runbook

Guide for deploying your own instance on any VPS that runs Docker
(Caddy reverse proxy + readonly DB + rate limit + Cloudflare).

> This file is a **generic runbook** for anyone forking to deploy their own instance.
> Examples use `example.org` — replace with your real domain.
> The infra reference in [`infra/`](infra/) is written as Terraform for DigitalOcean —
> adapt to whichever cloud provider you use (AWS, GCP, Linode, etc.).

---

## 📋 Gate 1 — Initial Deploy Checklist

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
- ✓ /mcp → POST endpoint (Streamable HTTP, MCP spec 2025-03-26)
- ✓ /sse → text/event-stream (legacy transport)

### 5. Test real MCP tools

Claude Desktop bridges remote MCP servers through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote). The server exposes both transports — `mcp-remote` will try Streamable HTTP first and fall back to SSE if needed.

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripitaka": {
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

To pin the legacy SSE transport instead, change the URL to `.../sse` and add `"--transport", "sse-only"` to `args`. See [`claude_desktop_config.example.json`](./claude_desktop_config.example.json) for both side by side.

**Things to know:**

- `command` must be the **full path** to `npx` (Claude Desktop doesn't see your shell's `PATH`) — find it with `which npx`
- `env.PATH` is required when using **nvm**: otherwise `node` may resolve to an older version that lacks the `node:path` module
- First connection takes 5–10 seconds while `npx` downloads `mcp-remote` on demand
- Full annotated example: [`claude_desktop_config.example.json`](./claude_desktop_config.example.json)

Restart Claude and try:

- `search_hybrid("metta")` — should return results
- `get_word_definition("sati")` — should include attribution
- `get_sutta("dn22")` — should return ~454 segments of the Mahāsatipaṭṭhāna Sutta

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

> **After editing `.env`**, prefer `up -d --force-recreate` over `restart` — plain `restart` may not reload environment variables from `.env` reliably (compose env-cache behavior). Pattern proven during a password rotation: `restart` showed containers up but they were still using the previous `DATABASE_URL`.
>
> ```bash
> docker compose -f docker-compose.prod.yml up -d --force-recreate mcp-server mcp-server-http
> ```

### Update (pull latest code)

```bash
cd /opt/tripitaka
git pull
./scripts/deploy.sh                  # reuses existing .env
```

### What a deploy restarts

A routine deploy rebuilds and recreates the application services only:

| Service | Touched by a routine deploy | Why |
| --- | --- | --- |
| `mcp-server` | yes | carries the code being deployed |
| `mcp-server-http` | yes | same image, modern transport |
| `reader` | yes | same image, serves `/read/*` |
| `db` | no | the code being deployed is not in it; data lives in a volume |
| `caddy` | no | it holds ports 80 and 443, so recreating it drops **every** service for 10 to 15 seconds |

Pass `--with-caddy` on the rounds where you actually changed `infra/Caddyfile` or
`infra/Dockerfile.caddy`, and accept that short outage. On a machine that has no
caddy container yet, the first deploy starts it without the flag, otherwise a new
install would come up with no reverse proxy.

Caddy serves `site/` and `topics/` through bind mounts, which attach to a
directory by inode. If a checkout replaces either directory rather than editing
the files in place, a running caddy keeps the old, now empty one and serves 404s
with nothing in its log. Compare them after a pull that touched those paths:

```bash
stat -c '%i %n' site topics
docker compose -f docker-compose.prod.yml exec caddy stat -c '%i %n' /var/www/site /var/www/topics
```

Different numbers mean caddy needs recreating:
`docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps caddy`

### Allow a browser app to call `/mcp` (CORS)

Browser apps need CORS to call `/mcp`; desktop and hosted MCP clients don't.
The allowlist is `MCP_CORS_ORIGINS` in `.env`, space-separated, each entry an
exact `scheme://host[:port]` with no trailing slash (`https://example.github.io`,
not `https://example.github.io/app/`). Unset, it falls back to the default in
`docker-compose.prod.yml`. Caddy reads it at start, so recreate caddy after a
change, which drops every service for 10 to 15 seconds:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate --no-deps caddy
curl -si -X OPTIONS https://$TRIPITAKA_DOMAIN/mcp \
  -H 'Origin: https://example.github.io' -H 'Access-Control-Request-Method: POST' \
  | grep -i '^access-control'
```

No `access-control-*` lines in the output means the origin did not match.

### Image versions

`deploy.sh` tags each build with the git short sha of the commit it built, and
points `latest` at that same image. A tag is a second name for an image, not a
copy, so the extra name costs no disk.

```bash
docker image ls tripitaka-mcp
# REPOSITORY      TAG       IMAGE ID       SIZE
# tripitaka-mcp   8ec1a0d   1a2b3c4d5e6f   9.14GB   <- latest points here too
# tripitaka-mcp   latest    1a2b3c4d5e6f   9.14GB
# tripitaka-mcp   d594198   0f9e8d7c6b5a   9.14GB   <- previous deploy
```

The `SIZE` column shows the whole image, not what each version adds. Versions
share every layer the commit did not change, so a second version costs only the
layers that differ. Measured on the production image:

| layer | size | shared between versions |
|---|---|---|
| `COPY /install /usr/local` (pip install) | 5.49 GB | yes, while `requirements.txt` is unchanged |
| base `python:3.12-slim` layers | 134 MB | yes |
| `COPY . .` (the source tree) | size of the build context | no, this is the per-commit layer |

The build context is the checkout minus what `.dockerignore` excludes, which is
16 MB on the server today. So an ordinary deploy adds tens of megabytes, and
keeping 3 versions costs a few tens of megabytes over keeping one.

A deploy that changes `requirements.txt` is the exception. The 5.49 GB layer is
rebuilt, the previous version keeps its own copy, and that one deploy costs
about 5.5 GB. Lower `TRIPITAKA_KEEP_VERSIONS` before a run of dependency
changes if disk is tight.

Image versions are not what fills the disk. The buildkit cache is far larger
than every version put together, and it is pruned on its own schedule.

The version running is pinned in `.env` as `APP_VERSION`, and every deploy
appends a line to `.deploy-history`. Both files are gitignored and exist on the
server only. Compose reads `.env` by itself, so `docker compose up -d` with
nothing set in the environment starts the pinned version rather than whatever
`latest` happens to point at.

`deploy.sh` keeps the 3 most recent versions and removes older tags after a
successful build. Set `TRIPITAKA_KEEP_VERSIONS` in `.env` to keep more or fewer.

### Rollback

Swap back to an earlier version's image. Nothing is rebuilt, so this costs a
container restart rather than the several minutes a rebuild takes.

```bash
cd /opt/tripitaka
./scripts/rollback.sh --list       # versions whose images are still on disk
./scripts/rollback.sh              # back to the previous version
./scripts/rollback.sh 8ec1a0d      # back to a named version
./scripts/rollback.sh --dry-run    # print what it would do, change nothing
```

It pins `APP_VERSION` in `.env`, moves the `latest` tag, and recreates
mcp-server, mcp-server-http, reader and caddy with `--no-build`. Caddy holds
ports 80 and 443, so every service is unreachable for 10 to 15 seconds while it
restarts.

Only the code inside the image goes back. `infra/Caddyfile`, `site/` and
`topics/` are bind mounts and still come from the checkout, so when the breakage
is in one of those, revert the commit instead:

```bash
# on your laptop
git revert <commit> && git push origin main

# on the server
git pull origin main && ./scripts/deploy.sh
```

Revert is also the way back when the version you want was already removed by
retention, or when the server has no `.deploy-history` yet because it has not
been deployed with the version-tagging `deploy.sh`. `rollback.sh` names the case
it hit and exits instead of failing halfway.

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

### `/mcp` or `/sse` returns 502 from Caddy

Common causes:

1. **mcp-server bound to `127.0.0.1`** — the running container's `.env` must set `MCP_HOST=0.0.0.0`, otherwise Caddy (in a sibling container) can't connect
   - Check: `docker logs tripitaka-mcp-server | grep 'Uvicorn running'` — should show `http://0.0.0.0:8080`
2. **Wrong `MCP_TRANSPORT`** — for the HTTP/SSE container, must be one of `streamable-http` or `sse` (`stdio` gives no HTTP listener at all). The prod stack runs both: `mcp-server` with `MCP_TRANSPORT=sse` for `/sse`, `mcp-server-http` with `MCP_TRANSPORT=streamable-http` for `/mcp`.
3. **Port mismatch** — Caddy proxies to `:8080` but the server listens on `:8000` (the default when `MCP_PORT` isn't set in the container env)
4. **Auth failure to DB** — server starts on port but tools fail. Check `docker logs tripitaka-mcp-server | grep -iE "fatal|auth"` — likely `password authentication failed for user "tripitaka_ro"` after a stale `.env` reload (see Restart note above; use `--force-recreate`)

### SSH refused (Connection refused) after previously working

Your public IP changed (VPN / mobile / ISP) → the cloud firewall `ssh_allowed_cidrs` blocks you.
Fix: update the new IP in [infra/terraform.tfvars](infra/terraform.tfvars), then run
`terraform apply -target=<firewall_resource>` (find the resource name in `infra/main.tf`).

### Claude Desktop: `Cannot find module 'node:path'`

Claude Desktop is running an older `node` (< 16) that lacks the `node:` protocol.
Fix: set the full `PATH` in `env` to point at node ≥ 18, and/or run `nvm alias default 22`.

### Claude Desktop: `Streamable HTTP error: Non-200 status code (502)`

`mcp-remote` connects to a URL that's not reachable. Possibilities:

- DNS hasn't propagated yet — `dig <your-domain>` from your laptop should resolve to the proxy/origin IP
- Cloudflare proxy is pointing at the wrong origin or origin is down — check `/health` directly
- Origin is on the wrong transport — make sure `mcp-server-http` (Streamable HTTP) is up if your URL ends in `/mcp`, or `mcp-server` (SSE) if it ends in `/sse`

---

## ⚠️ Things to Watch

1. **Resources**: 4 GB RAM recommended (with 2 GB swap as a safety net — already set by cloud-init).
   For capacity estimates and scaling guidance: [docs/CAPACITY.md](./docs/CAPACITY.md)
2. **Never commit `.env`**: `chmod 600` and keep a backup in a password manager
3. **Dump file**: ~800 MB for the current full Tipiṭaka data (Sutta + Vinaya + Abhidhamma + embeddings, ~444K segments) — remove after restoring (`rm tripitaka_production_data.dump`) to save disk
4. **Let's Encrypt rate limit**: repeated failed deploys can get you banned for a week — test with `--staging` first if unsure (the `--staging` flag here refers to Let's Encrypt's staging CA, not a separate environment)
