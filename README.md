# 🛕 Tripitaka MCP Server

MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก (Tipiṭaka)
ให้ AI Agent (เช่น Claude, Cursor) สามารถค้นหาพระสูตร อ้างอิงคำสอน และเปรียบเทียบคำแปลข้ามภาษาได้

> 🙏 **โครงการนี้เผยแผ่เป็นธรรมทาน (Dhamma Dāna)** — ฟรี 100%, ห้ามใช้เชิงพาณิชย์
> ดูรายละเอียด license: [LICENSE](./LICENSE) (code) + [NOTICE.md](./NOTICE.md) (data)

## ✨ Features

- ⚖️ **Hybrid Search** — ขีดสุดของความแม่นยำด้วยการนำ Keyword และ Semantic Search มารวมกันผ่านอัลกอริทึม Reciprocal Rank Fusion (RRF) (พร้อมใช้งานแล้ว!)
- 🔍 **Keyword Search** — ค้นหาด้วยคำสำคัญ รองรับ 3 ภาษา (บาลี, ไทย, อังกฤษ) แบบ Trigram Fuzzy Match ซิงก์ข้ามภาษา
- 🧠 **Semantic Search** — ค้นหาตามความหมาย สัมผัสถึงแก่นเจตนาด้วย Vector similarity (pgvector)
- 📖 **Translation Comparison** — เรียกดูและเทียบสำนวนการแปลข้ามฉบับ (Edition) โยงตรงตาม Segment บรรทัดต่อบรรทัด
- 📚 **Dictionary Bridge** — ระบบพจนานุกรมในตัวกว่า 20,000+ คำ (ป.อ. ปยุตฺโต, PTS, DPPN)
- 📖 **Get Sutta & Reference** — ดึงเนื้อหาสูตรตาม ID (เช่น mn1) และสร้างข้อความอ้างอิงวิชาการมาตรฐาน
- 📮 **Postman Ready** — มีคอลเลกชันสำหรับทดสอบ API ในโหมด sse เข้ากับโมเดลพัฒนาได้ทันที

## 🏗️ Tech Stack

| เทคโนโลยี | หน้าที่ |
|---|---|
| Python + FastMCP | MCP Server |
| PostgreSQL + pgvector | ฐานข้อมูล + Vector Search |
| sentence-transformers | Embedding สำหรับ Semantic Search |
| Docker Compose | Infrastructure |

## 🚀 Quick Start

### 🏎️ วิธีที่เร็วที่สุด — ใช้ installer (แนะนำสำหรับผู้ไม่ใช่สาย dev)

```bash
git clone https://github.com/Ipurak/tripitaka-mcp.git
cd tripitaka-mcp
./scripts/install.sh
```

ถ้ามี database dump (`tripitaka_production_data.dump`) วางไว้ในโฟลเดอร์ project
installer จะ **restore ให้อัตโนมัติ** — ประหยัดเวลาจาก 2-4 ชม. (load + embeddings) เหลือ ~5 นาที

ดาวน์โหลด dump ล่าสุดได้จาก:

- [Hugging Face Datasets — Ipurak/tripitaka-mcp-dump](https://huggingface.co/datasets/Ipurak/tripitaka-mcp-dump) _(เร็วๆ นี้)_

installer จะ:

1. ตรวจว่ามี docker / compose / openssl
2. สร้าง `.env` ด้วย password สุ่มให้ (ทั้ง admin และ readonly user)
3. เปิด DB + restore dump (ถ้าเจอ)
4. ตั้ง readonly role + timeout สำหรับ runtime
5. แสดง config Claude Desktop ที่ copy ไปวางได้เลย

---

### 🔧 วิธี manual (สำหรับ dev)

#### 1. Clone & Setup

```bash
git clone https://github.com/Ipurak/tripitaka-mcp.git
cd tripitaka-mcp
cp .env.example .env
# แก้ POSTGRES_PASSWORD ใน .env ให้เป็น random password
```

#### 2. Start Database

```bash
docker compose up db -d
```

#### 3. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Initialize Database & Load Data

```bash
# 1. Seed metadata (pitaka, nikaya)
python scripts/seed_metadata.py

# 2. Download & load Sutta Pitaka data จาก SuttaCentral
python scripts/data_loader.py

# 3. Load Thai CC0 Translations (Dhiranandi & Jayasaro)
python scripts/load_thai_cc0.py

# 4. Load Dictionary (DPD, PTS, DPPN และพจนานุกรม ป.อ. ปยุตฺโต)
python scripts/load_dictionary.py

# 5. Generate embeddings สำหรับ semantic/hybrid search
python scripts/generate_embeddings.py
```

#### 5. Run MCP Server

```bash
python main.py
```

### 🧪 การทดสอบด้วย Postman

โปรเจคนี้รองรับการทดสอบผ่าน Postman ในโหมด SSE:
1. รันเซิร์ฟเวอร์ด้วย: `MCP_TRANSPORT=sse python main.py`
2. Import ไฟล์ [postman_collection.json](./postman_collection.json) เข้าสู่ Postman
3. เรียกใช้ Tool ต่างๆ ได้ทันที

## 🚢 Production Deployment

หากต้องการ Deploy ขึ้น Production โดยไม่ต้องโหลดข้อมูลและรัน AI Model ใหม่ แนะนำให้ใช้การ Restore จาก Database Dump

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Production stack มี 3 services:

- `db` — PostgreSQL + pgvector (internal only, ไม่ expose port)
- `mcp-server` — FastMCP (รันด้วย readonly user, read-only FS, cap_drop ALL)
- `caddy` — reverse proxy + Let's Encrypt + **rate limit** (10 req/10s และ 60 req/1 min per IP)

แนะนำให้เสริมด้วย **Cloudflare** หน้า Caddy อีกชั้น (DNS proxy + rate limit rules + DDoS protection — free tier)

👉 ดูรายละเอียดที่: **[DEPLOYMENT.md](./DEPLOYMENT.md)**

## 🔧 เชื่อมต่อกับ Claude Desktop

เพิ่มใน `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tripitaka": {
      "command": "python",
      "args": ["/path/to/tripitaka-mcp/main.py"],
      "env": {
        "DATABASE_URL": "postgresql://admin:password123@localhost:5432/tripitaka_db"
      }
    }
  }
}
```

## 📦 MCP Tools

| Tool | คำอธิบาย |
|---|---|
| `search_hybrid` | **(แนะนำ)** ค้นหาผสมผสาน (Hybrid Search) ด้วยเทคนิค RRF เพื่อความแม่นยำสูงสุด |
| `search_by_keyword` | ค้นหาด้วย keyword (trigram fuzzy match) |
| `search_semantic` | ค้นหาแบบ semantic (vector similarity) |
| `get_sutta` | ดึงเนื้อหาสูตรตาม ID พร้อมดึงคำแปลทั้งหมดที่เกี่ยวข้อง |
| `compare_translations`| เปรียบเทียบสำนวนการแปลข้ามฉบับ (Edition) ในแต่ละ Segment |
| `get_word_definition` | ค้นหาพจนานุกรมข้ามภาษา (PTS, DPPN, และพจนานุกรม ป.อ. ปยุตฺโต) |
| `list_structure` | แสดงโครงสร้างคัมภีร์พระไตรปิฎก |
| `get_reference` | สร้างข้อมูลอ้างอิงที่ถูกต้องตามรูปแบบวิชาการ |

## 📁 โครงสร้างโปรเจค

```text
tripitaka-mcp/
├── main.py                 # MCP Server หลัก (Tools ทั้งหมด)
├── db/
│   ├── connection.py       # Database connection pool
│   └── schema.py           # Database schema (รองรับ translation table)
├── embedding/
│   └── model.py            # SentenceTransformer wrapper
├── scripts/
│   ├── seed_metadata.py    # Seed pitaka/nikaya metadata
│   ├── data_loader.py      # Load Pali/English จาก SuttaCentral
│   ├── load_thai_cc0.py    # สคริปต์โหลดคำแปลภาษาไทยประโยคต่อประโยค
│   ├── load_dictionary.py  # โหลดฐานข้อมูลพจนานุกรมเข้าสู่ระบบ
│   ├── scrape_payutto.py   # Web Scraper พจนานุกรม ป.อ. ปยุตฺโต
│   └── generate_embeddings.py  # สร้าง vector embeddings
├── data/
│   └── payutto_dict.json   # ฐานข้อมูลศัพท์ภาษาไทยที่ขูดมาจากเว็บ
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 📜 แหล่งข้อมูลและ License

โครงการนี้รวมข้อมูลจากหลายแหล่งที่อยู่ภายใต้ license ต่างกัน
**โปรดอ่าน [NOTICE.md](./NOTICE.md) ให้ครบถ้วนก่อนนำไปใช้**

| แหล่งข้อมูล | License | หมายเหตุ |
| --- | --- | --- |
| Source code | **MIT** | ใช้ / fork / แก้ไขได้เสรี |
| [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) | **CC0** | Public domain |
| คำแปลไทย (ธีรนันโท, ชยสาโร) | **CC0** | ผ่าน SuttaCentral |
| [พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์](https://www.watnyanaves.net) โดย สมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต) | **ธรรมทาน** | ⚠️ ห้ามใช้เชิงพาณิชย์ |
| PTS / DPPN / Dhammika Dictionaries | Public Domain / CC | — |

### ⚠️ หากคุณจะ fork หรือนำไปใช้ต่อ

- ✅ ใช้ในโปรเจกต์ **ฟรี / ธรรมทาน / การศึกษา** ได้
- ✅ รันในเครื่องตัวเอง / ใช้ส่วนตัว ได้
- ❌ **ห้ามใช้ในสินค้า/บริการที่เรียกเก็บเงิน** (เพราะพจนานุกรม ป.อ. ปยุตฺโต)
- ❌ **ห้ามดัดแปลงเนื้อหาพจนานุกรม**

ถ้าต้องการใช้เชิงพาณิชย์: เอาส่วนพจนานุกรมออก หรือติดต่อวัดญาณเวศกวันขออนุญาต

### 🙏 Credits & Attribution

ดู [CREDITS.md](./CREDITS.md) สำหรับรายละเอียดผู้มีส่วนร่วม
และ [NOTICE.md](./NOTICE.md) สำหรับเงื่อนไข license

**ขออนุโมทนาบุญต่อ:**

- สมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต) + วัดญาณเวศกวัน
- SuttaCentral + ผู้แปลภาษาไทยและภาษาอังกฤษ
- 84000.org

---

**สาธุ 🙏** ขอให้การเผยแผ่ธรรมนี้ เป็นไปเพื่อประโยชน์และความสุขของสรรพสัตว์
