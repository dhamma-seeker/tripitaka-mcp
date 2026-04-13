# 🚢 Tripitaka MCP Server — Production Deployment Guide

คู่มือนี้สำหรับเตรียมการขึ้นระบบจริง (Production) โดยเน้นความเร็วและความประหยัดทรัพยากรด้วยการใช้ **Database Dump** แทนการโหลดข้อมูลใหม่

---

## 🏗️ 1. เตรียมความพร้อมของฐานข้อมูล (Database)

หากคุณได้รันสคริปต์โหลดข้อมูลและสร้าง Vector Embeddings ครบถ้วนแล้วบนเครื่องพัฒนา ให้ทำการ Backup ข้อมูลออกมาดังนี้:

### บนเครื่องพัฒนา (Development):
```bash
# Export ข้อมูลผ่าน Docker
docker exec -t tripitaka-db pg_dump -U admin -d tripitaka_db -F c -b > tripitaka_production_data.dump
```

---

## 🚀 2. การติดตั้งบน Server Production

### ขั้นตอนที่ 1: เตรียมไฟล์บน Server
Copy ไฟล์ต่อไปนี้ขึ้นไปไว้บน Server:
- `docker-compose.yml`
- `Dockerfile`
- `.env` (ปรับจูนค่าต่างๆ)
- `tripitaka_production_data.dump`

### ขั้นตอนที่ 2: เริ่มต้นฐานข้อมูล
```bash
# เริ่มเฉพาะบริการฐานข้อมูลก่อน
docker compose up db -d
```

### ขั้นตอนที่ 3: Restore ข้อมูล
```bash
# นำข้อมูลที่ dump ไว้เข้าไปในฐานข้อมูลใหม่
docker exec -i tripitaka-db pg_restore -U admin -d tripitaka_db -v < tripitaka_production_data.dump
```

---

## ⚙️ 3. การตั้งค่า Environment Variables (.env)

สำคัญมากสำหรับการ Deploy จริง:

| ตัวแปร | คำอธิบาย |
|---|---|
| `DATABASE_URL` | URL สำหรับเชื่อมต่อฐานข้อมูล (เช่น `postgresql://user:pass@db:5432/tripitaka_db`) |
| `MCP_TRANSPORT` | `stdio` (สำหรับ AI Agents) หรือ `sse` (สำหรับ HTTP/Web) |
| `EMBEDDING_MODEL` | ชื่อโมเดลที่ต้องการโหลด (ต้องตรงกับที่ใช้ตอนสร้าง dump) |

---

## 🖥️ 4. การเชื่อมต่อกับ Client

### หากใช้ผ่าน Claude Desktop หรือ Cursor:
ระบุคำสั่งให้เรียกใช้งาน Docker ดังนี้:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "docker",
      "args": ["exec", "-i", "tripitaka-mcp-server", "python", "main.py"],
      "env": {
        "DATABASE_URL": "postgresql://admin:password123@db:5432/tripitaka_db"
      }
    }
  }
}
```

---

## ⚠️ ข้อควรระวัง (Notes)

1. **ทรัพยากร (Resources):**
   - **RAM:** แนะนำอย่างน้อย 4GB (สำหรับ PostgreSQL + Vector Index + AI Model Cache)
   - **Disk:** พื้นที่ว่างอย่างน้อย 2-5GB สำหรับฐานข้อมูลและตัวโมเดล
2. **GPU:** โปรเจคนี้รันบน CPU ได้ดีผ่าน `sentence-transformers` แต่หากมีจำนวนข้อมูลมหาศาล การมี GPU จะช่วยเรื่องความเร็วในการสร้างตัวเลือกใหม่ๆ ได้ดีขึ้น (อย่างไรก็ตาม สำหรับการค้นหาด้วย Vector Index ไม่จำเป็นต้องใช้ GPU)
3. **Security:** อย่าลืมเปลี่ยน `POSTGRES_PASSWORD` และจำกัดการเข้าถึงพอร์ต `5432` ให้เฉพาะภายใน Docker Network เท่านั้น

---

💡 **Tip:** การใช้ไฟล์ `.dump` จะช่วยประหยัดเวลาการ Deploy ได้มากกว่า **1-2 ชั่วโมง** เนื่องจากไม่ต้องรัน AI Model เพื่อสร้างเวกเตอร์ใหม่บน Server ครับ
