# 🛕 Tripitaka MCP Server

MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก (Tipiṭaka)  
ให้ AI Agent (เช่น Claude, Cursor) สามารถค้นหาพระสูตร อ้างอิงคำสอน และเปรียบเทียบคำแปลข้ามภาษาได้

## ✨ Features

- 🔍 **Keyword Search** — ค้นหาด้วยคำสำคัญ รองรับ 3 ภาษา (บาลี, ไทย, อังกฤษ)
- 🧠 **Semantic Search** — ค้นหาตามความหมาย ด้วย vector similarity (pgvector)
- 📖 **Get Sutta** — ดึงเนื้อหาสูตรตาม ID (เช่น mn1, dn22, sn56.11)
- 📚 **Structure** — แสดงโครงสร้างพระไตรปิฎกทั้ง 3 ปิฎก
- 📝 **Reference** — สร้างข้อมูลอ้างอิงที่ถูกต้องตามหลักวิชาการ

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
# Seed metadata (pitaka, nikaya)
python scripts/seed_metadata.py

# Download & load Sutta Pitaka data from SuttaCentral
python scripts/data_loader.py

# Generate embeddings สำหรับ semantic search (optional)
python scripts/generate_embeddings.py
```

### 5. Run MCP Server

```bash
python main.py
```

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
| `search_by_keyword` | ค้นหาด้วย keyword (trigram fuzzy match) |
| `get_sutta` | ดึงเนื้อหาสูตรตาม ID |
| `search_semantic` | ค้นหาแบบ semantic (vector similarity) |
| `list_structure` | แสดงโครงสร้างพระไตรปิฎก |
| `get_reference` | สร้างข้อมูลอ้างอิงที่ถูกต้อง |

## 📁 โครงสร้างโปรเจค

```
tripitaka-mcp/
├── main.py                 # MCP Server หลัก
├── db/
│   ├── connection.py       # Database connection pool
│   └── schema.py           # Database schema (tables, indexes)
├── embedding/
│   └── model.py            # Embedding model wrapper
├── scripts/
│   ├── seed_metadata.py    # Seed pitaka/nikaya metadata
│   ├── data_loader.py      # Load data จาก SuttaCentral
│   └── generate_embeddings.py  # สร้าง vector embeddings
├── data/                   # ข้อมูลพระไตรปิฎก (bilara-data)
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 📜 แหล่งข้อมูล

- [SuttaCentral bilara-data](https://github.com/suttacentral/bilara-data) — ข้อมูลพระไตรปิฎก (CC0 License)
- [SuttaCentral](https://suttacentral.net) — เว็บไซต์พระไตรปิฎกดิจิทัล

## 📄 License

MIT
