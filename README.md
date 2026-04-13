# 🛕 Tripitaka MCP Server

MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก (Tipiṭaka)  
ให้ AI Agent (เช่น Claude, Cursor) สามารถค้นหาพระสูตร อ้างอิงคำสอน และเปรียบเทียบคำแปลข้ามภาษาได้

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

### 1. Clone & Setup

```bash
git clone https://github.com/Ipurak/tripitaka-mcp.git
cd tripitaka-mcp
cp .env.example .env
```

### 2. Start Database

```bash
docker compose up db -d
```

### 3. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Initialize Database & Load Data

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

### 5. Run MCP Server

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

## 📜 แหล่งข้อมูล

- [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) — ข้อมูลพระไตรปิฎก (CC0 License)
- [พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์ (ป.อ. ปยุตฺโต)](https://tripitaka-online.blogspot.com/) — สำหรับข้อมูลศัพท์ภาษาไทย
- [SuttaCentral](https://suttacentral.net) — เว็บไซต์อ้างอิงพระไตรปิฎกดิจิทัลหลัก

## 📄 License

MIT
