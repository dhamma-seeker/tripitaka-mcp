# 📊 Capacity Planning — Tripitaka MCP

Estimates of how much load each VPS spec can handle,
so self-hosters can plan budget and scale to the right size.

> Numbers come from real-world testing on a VPS with **2 vCPU / 4 GB RAM** (Asia region, SSD)
> during the staging phase — embedding model = `paraphrase-multilingual-MiniLM-L12-v2` (384 dim)

---

## 📈 Baseline — 2 vCPU / 4 GB RAM (~$24/mo)

| Resource | Idle | Peak (1 query) | Theoretical ceiling |
|---|---|---|---|
| CPU | 5-8% | 20-26% | 200% (2 vCPU) |
| Memory | 23% (~920MB) | 37% (~1.5GB) | 100% (4GB + 2GB swap) |
| Load (1m avg) | 0.1 | 0.75 | 2.0 (above → queued) |
| Disk I/O | 0 | 7.5 MB/s burst | NVMe SSD |
| Bandwidth | ~5 kb/s | ~10 kb/s | not a bottleneck |

**Primary bottleneck = CPU** (embedding inference runs on CPU, no GPU)

### Capacity estimate

| Pattern | Count |
|---|---|
| Concurrent active queries (no lag) | **4-6 at once** |
| Active SSE connections (idle) | **50-100** |
| Daily users (occasional, not continuous) | **200-500 users/day** |
| Sustained queries per second | **~1-2 qps** |

### Warning signs (time to upgrade)

- Memory > 80% sustained → swap kicks in → latency spikes
- Load (1m) > 2.0 for more than 5 minutes → long queue
- `/health` responds slower than 1s
- Error rate > 1% due to timeouts

---

## 🚀 Scaling path

As traffic grows, this is the recommended order:

### Step 1 — Enable Cloudflare orange proxy (free)

- Cache static responses + block bot traffic
- Reduces origin CPU by ~20-40% (depending on share of repeat queries)
- No spec change needed

### Step 2 — Bump RAM (~$36/mo, 2 vCPU / 8 GB)

- Addresses memory pressure before CPU
- Postgres cache fits better → faster queries
- CPU stays the same → doesn't raise concurrency much
- **Good when**: memory > 70% but CPU still has headroom

### Step 3 — Bump CPU (~$48/mo, 4 vCPU / 8 GB)

- Concurrent queries ~2x (8-12 at once)
- Supports ~500-1000 users/day
- **Good when**: load avg stays high, queue is long

### Step 4 — Offload embedding to an external API

- Use [Jina Embeddings API](https://jina.ai/embeddings/) / OpenAI / Cohere instead of local sentence-transformers
- Origin CPU drops to just Postgres + Caddy → handles several times more traffic
- **Tradeoff**: per-call cost, no longer self-contained, query privacy depends on the provider
- **Good when**: traffic > 1000 users/day, or response time matters more than cost

### Step 5 — Horizontal scaling

- Separate mcp-server from the DB
- DB: Managed Postgres (RDS / equivalent) with a read replica
- mcp-server: multiple instances behind a load balancer
- **Good when**: traffic > 10k users/day

---

## 🧪 How to measure your own load

### Quick check (on the VPS)

```bash
# CPU/memory snapshot
htop

# Docker resource usage per container
docker stats --no-stream

# Postgres connection count + long queries
docker exec tripitaka-db psql -U admin -d tripitaka_db \
  -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
```

### Cloud provider monitoring

Most cloud providers ship built-in monitoring (CPU / Memory / Load graphs)
and alert policies (email/Slack) — use whatever native tool your provider offers.

Recommended alert thresholds: CPU > 80% / Memory > 85% / Disk > 80% (5-minute window).

### Synthetic load test

```bash
# From your laptop — fire 10 concurrent queries
for i in {1..10}; do
  curl -sS https://mcp.example.org/sse > /dev/null &
done
wait
```

Watch the CPU spike during this in your provider's dashboard — if it stays < 80% the current spec still has headroom.

---

## 💰 Cost summary

Pricing references typical VPS providers (DigitalOcean / Linode / Vultr / Hetzner — comparable specs).

| Spec | Price (approx) | Concurrent | Daily users (est) | Best for |
|---|---|---|---|---|
| 1 vCPU / 2 GB | ~$12/mo | 1-2 | 50-100 | PoC, personal |
| 2 vCPU / 2 GB | ~$18/mo | 2-3 | 100-200 | risky (OOM) |
| **2 vCPU / 4 GB** | **~$24/mo** | **4-6** | **200-500** | **recommended starting point** |
| 2 vCPU / 8 GB | ~$36/mo | 5-7 | 400-700 | RAM pressure |
| 4 vCPU / 8 GB | ~$48/mo | 8-12 | 500-1000 | growing traffic |
| CPU-optimized 4-core | ~$84/mo | 15-20 | 1500-3000 | embedding-heavy |

> Numbers are conservative estimates — real workloads can vary by 2-3x depending on cache hit rate and query complexity.
