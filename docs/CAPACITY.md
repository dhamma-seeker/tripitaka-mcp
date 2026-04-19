# 📊 Capacity Planning — Tripitaka MCP

ประเมินความสามารถในการรับโหลดของแต่ละสเปก VPS
สำหรับ self-hoster วางแผนงบและ scale ได้ถูกตัว

> ตัวเลขนี้วัดจากการทดสอบจริงบน DigitalOcean `s-2vcpu-4gb` (SGP1)
> ช่วง staging phase — embedding model = `paraphrase-multilingual-MiniLM-L12-v2` (384 dim)

---

## 📈 Baseline — `s-2vcpu-4gb` ($24/mo)

| Resource | Idle | Peak (1 query) | เพดานทาง theory |
|---|---|---|---|
| CPU | 5-8% | 20-26% | 200% (2 vCPU) |
| Memory | 23% (~920MB) | 37% (~1.5GB) | 100% (4GB + swap 2GB) |
| Load (1m avg) | 0.1 | 0.75 | 2.0 (เกินแล้ว queue) |
| Disk I/O | 0 | 7.5 MB/s burst | NVMe SSD |
| Bandwidth | ~5 kb/s | ~10 kb/s | ไม่ใช่คอขวด |

**คอขวดหลัก = CPU** (embedding inference รันบน CPU ไม่มี GPU)

### ประเมินความจุ

| Pattern | จำนวน |
|---|---|
| Concurrent active queries (ไม่หน่วง) | **4-6 พร้อมกัน** |
| Active SSE connections (idle) | **50-100** |
| Daily users (ถามเป็นครั้งคราว, ไม่ต่อเนื่อง) | **200-500 คน/วัน** |
| Queries ต่อวินาที sustained | **~1-2 qps** |

### สัญญาณเตือน (ถึงเวลาอัพเกรด)

- Memory > 80% ต่อเนื่อง → swap ทำงาน → latency พุ่ง
- Load (1m) > 2.0 ค้างเกิน 5 นาที → queue ยาว
- `/health` ตอบช้า > 1s
- Error rate > 1% จาก timeout

---

## 🚀 แนวทาง scale

เมื่อ traffic เติบโต แนะนำลำดับนี้:

### ขั้น 1 — เปิด Cloudflare orange proxy (ฟรี)

- Cache static responses + block bot traffic
- ลด CPU origin ได้ ~20-40% (ตามสัดส่วน repeat queries)
- ไม่ต้องเปลี่ยน spec

### ขั้น 2 — อัพ RAM ($36/mo — `s-2vcpu-8gb`)

- แก้ memory pressure ก่อน CPU
- Postgres cache พอดีขึ้น → query เร็ว
- CPU ยังเท่าเดิม → ไม่เพิ่ม concurrent มาก
- **เหมาะเมื่อ**: memory > 70% แต่ CPU ยังว่าง

### ขั้น 3 — อัพ CPU ($48/mo — `s-4vcpu-8gb`)

- Concurrent queries ~2 เท่า (8-12 พร้อมกัน)
- รองรับ ~500-1000 คน/วัน
- **เหมาะเมื่อ**: load avg ค้างสูง, queue ยาว

### ขั้น 4 — Offload embedding ไป API ภายนอก

- ใช้ [Jina Embeddings API](https://jina.ai/embeddings/) / OpenAI / Cohere แทน sentence-transformers local
- CPU origin ลดเหลือแค่ Postgres + Caddy → รับ traffic ได้หลายเท่า
- **ข้อแลก**: ต้องจ่าย per-call, ไม่ self-contained, privacy ของ query ขึ้นกับ provider
- **เหมาะเมื่อ**: traffic > 1000 คน/วัน หรือ response time สำคัญกว่าต้นทุน

### ขั้น 5 — Horizontal scaling

- แยก mcp-server ออกจาก DB
- DB: Managed Postgres (DO/AWS RDS) พร้อม read replica
- mcp-server: หลาย instance หลัง load balancer
- **เหมาะเมื่อ**: traffic > 10k คน/วัน

---

## 🧪 วิธีวัดโหลดของตัวเอง

### Quick check (บน droplet)

```bash
# CPU/memory snapshot
htop

# Docker resource per container
docker stats --no-stream

# Postgres connection count + long queries
docker exec tripitaka-db psql -U admin -d tripitaka_db \
  -c "SELECT state, count(*) FROM pg_stat_activity GROUP BY state;"
```

### DigitalOcean Monitoring

- Droplet → **Insights** tab → ดู graph CPU / Memory / Load 1h–7d
- ตั้ง alert ที่ **Monitoring** → CPU > 80% for 5 min → email

### Synthetic load test

```bash
# ใน local — ยิง 10 concurrent queries
for i in {1..10}; do
  curl -sS https://mcp.example.org/sse > /dev/null &
done
wait
```

ดู CPU spike ระหว่างนี้จาก DO Insights — ถ้า < 80% แสดงว่าสเปกปัจจุบันยังเหลือ headroom

---

## 💰 สรุปตารางต้นทุน

| Spec | ราคา | Concurrent | Daily users (est) | เหมาะกับ |
|---|---|---|---|---|
| `s-1vcpu-2gb` | $12/mo | 1-2 | 50-100 | PoC, ส่วนตัว |
| `s-2vcpu-2gb` | $18/mo | 2-3 | 100-200 | เสี่ยง OOM |
| **`s-2vcpu-4gb`** | **$24/mo** | **4-6** | **200-500** | **แนะนำเริ่มต้น** |
| `s-2vcpu-8gb` | $36/mo | 5-7 | 400-700 | RAM pressure |
| `s-4vcpu-8gb` | $48/mo | 8-12 | 500-1000 | เติบโตแล้ว |
| `c-4` (CPU-opt) | $84/mo | 15-20 | 1500-3000 | เน้น embedding |

> ตัวเลขเป็นการประเมิน conservative — workload จริงอาจต่างจากนี้ได้ 2-3 เท่า ขึ้นกับ cache hit rate และ query complexity
