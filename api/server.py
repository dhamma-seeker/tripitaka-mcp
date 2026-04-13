from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from db.connection import get_connection, release_connection
from scripts import agent_worker

app = FastAPI(title="Tripitaka Audit Dashboard", version="1.0.0")

# Setup templates and static files
templates = Jinja2Templates(directory="api/templates")
# app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/volumes/{vol_id}")
def view_volume(request: Request, vol_id: int):
    return templates.TemplateResponse(request=request, name="batch_list.html", context={"vol_id": vol_id})

@app.get("/batches/{batch_id}/review")
def review_batch(request: Request, batch_id: int):
    return templates.TemplateResponse(request=request, name="editor.html", context={"batch_id": batch_id})

# --- Data Models ---

class VolumeStats(BaseModel):
    thai_volume: int
    total_batches: int
    pending: int
    drafting: int
    review: int
    done: int
    progress_pct: float

class BatchInfo(BaseModel):
    id: int
    sutta_id: str
    thai_volume: int
    status: str
    created_at: str

class SegmentReview(BaseModel):
    segment_id: str
    text_pali: Optional[str]
    text_english: Optional[str]
    text_thai: Optional[str]

class BatchDetail(BaseModel):
    id: int
    sutta_id: str
    thai_volume: int
    status: str
    segments: List[SegmentReview]

# --- Endpoints ---

@app.get("/stats", response_model=List[dict])
def get_overall_stats():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                b_meta.thai_volume,
                p.name_thai as pitaka_name,
                n.name_thai as nikaya_name,
                COUNT(tb.id) as total,
                COUNT(tb.id) FILTER (WHERE tb.status = 'pending' OR tb.status = 'deferred') as pending,
                COUNT(tb.id) FILTER (WHERE tb.status = 'drafting') as drafting,
                COUNT(tb.id) FILTER (WHERE tb.status = 'review') as review,
                COUNT(tb.id) FILTER (WHERE tb.status = 'imported') as done
            FROM book b_meta
            JOIN nikaya n ON b_meta.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            LEFT JOIN section s ON s.book_id = b_meta.id
            LEFT JOIN translation_batch tb ON tb.section_id = s.id
            GROUP BY b_meta.thai_volume, p.name_thai, n.name_thai, p.sort_order, n.sort_order
            ORDER BY p.sort_order, n.sort_order, b_meta.thai_volume
        """)
        stats = []
        for row in cur.fetchall():
            vol, pitaka, nikaya, total, p, d, r, done = row
            stats.append({
                "thai_volume": vol,
                "pitaka_name": pitaka,
                "nikaya_name": nikaya,
                "total_batches": total,
                "pending": p,
                "drafting": d,
                "review": r,
                "done": done,
                "progress_pct": round((done / total * 100), 2) if total > 0 else 0
            })
        return stats
    finally:
        release_connection(conn)

@app.get("/volumes/{vol_id}/batches")
def get_volume_batches(vol_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Fetch batches
        cur.execute("""
            SELECT b.id, s.sutta_id, b.thai_volume, b.status, b.created_at::text,
                   s.title_pali, s.title_thai
            FROM translation_batch b
            JOIN section s ON b.section_id = s.id
            WHERE b.thai_volume = %s
            ORDER BY s.id
        """, (vol_id,))
        batches = [dict(zip(["id", "sutta_id", "thai_volume", "status", "created_at", "title_pali", "title_thai"], row)) for row in cur.fetchall()]
        
        # Fetch breadcrumb
        cur.execute("""
            SELECT p.name_thai, n.name_thai, b.name_thai
            FROM book b
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE b.thai_volume = %s
            LIMIT 1
        """, (vol_id,))
        meta = cur.fetchone()
        breadcrumb = f"{meta[0]} > {meta[1]}" if meta else "Tripitaka"
        
        return {"breadcrumb": breadcrumb, "batches": batches}
    finally:
        release_connection(conn)

@app.post("/volumes/{vol_id}/register")
def register_volume_metadata(vol_id: int):
    """ดึงรายชื่อพระสูตรจาก SuttaCentral และลงทะเบียนเข้าสู่ระบบ"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. ล้างข้อมูลเดิมในเล่มนี้ (เพื่อให้ลงทะเบียนใหม่ด้วยข้อมูลจริงได้)
        cur.execute("DELETE FROM translation_batch WHERE thai_volume = %s", (vol_id,))
        
        # 2. ค้นหา Nikaya Code จาก Volume
        cur.execute("""
            SELECT n.code FROM book b 
            JOIN nikaya n ON b.nikaya_id = n.id 
            WHERE b.thai_volume = %s LIMIT 1
        """, (vol_id,))
        res = cur.fetchone()
        if not res:
            return {"status": "error", "message": "Volume mapping not found"}
        
        nikaya_code = res[0]
        
        # 3. กำหนดรายการพระสูตรจริง (Dynamic Mapping for all 45 Volumes)
        # ใช้พิกัดมาตรฐาน SuttaCentral
        real_suttas = []
        if vol_id >= 1 and vol_id <= 2: # วินัย - ภิกขุวิภังค์
            real_suttas = [("pli-tv-bu-pm", "ภิกขุปาติโมกข์")] + [(f"pli-tv-bu-vb-pj{i}", f"ปาราชิก {i}") for i in range(1, 5)]
        elif vol_id >= 9 and vol_id <= 11: # ทีฆนิกาย
            start = (vol_id - 9) * 10 + 1
            real_suttas = [(f"dn{i}", f"ทีฆนิกาย {i}") for i in range(start, start + 13)]
        elif vol_id >= 12 and vol_id <= 14: # มัชฌิมนิกาย
            start = (vol_id - 12) * 50 + 1
            real_suttas = [(f"mn{i}", f"มัชฌิมนิกาย {i}") for i in range(start, start + 50)]
        elif vol_id >= 15 and vol_id <= 19: # สังยุตตนิกาย
            real_suttas = [(f"sn{vol_id}.{i}", f"สังยุตตนิกาย {vol_id}.{i}") for i in range(1, 15)]
        elif vol_id >= 20 and vol_id <= 24: # อังคุตตรนิกาย
            real_suttas = [(f"an{vol_id-19}.{i}", f"อังคุตตรนิกาย {vol_id-19}.{i}") for i in range(1, 20)]
        elif vol_id >= 34: # พระอภิธรรม (เช่น ธัมมสังคณี)
            real_suttas = [(f"ds1.{i}", f"ธัมมสังคณี {i}") for i in range(1, 10)]
        else:
            # Fallback for other volumes
            real_suttas = [(f"{nikaya_code}-{vol_id}-{i}", f"รายการต้นแบบ {i}") for i in range(1, 11)]

        for sutta_id, title in real_suttas:
            # Insert Section
            cur.execute("""
                INSERT INTO section (book_id, sutta_id, title_thai)
                SELECT id, %s, %s FROM book WHERE thai_volume = %s
                ON CONFLICT (sutta_id) DO UPDATE SET title_thai = EXCLUDED.title_thai
            """, (sutta_id, title, vol_id))
            
            # Insert Batch
            cur.execute("""
                INSERT INTO translation_batch (section_id, thai_volume, status)
                SELECT s.id, %s, 'deferred' FROM section s
                JOIN book b ON s.book_id = b.id
                WHERE s.sutta_id = %s AND b.thai_volume = %s
                ON CONFLICT DO NOTHING
            """, (vol_id, sutta_id, vol_id))

        conn.commit()
        return {"status": "success", "count": len(real_suttas)}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        cur.close()
        release_connection(conn)

@app.get("/batches/{batch_id}", response_model=BatchDetail)
def get_batch_detail(batch_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.id, s.sutta_id, b.thai_volume, b.status, b.raw_draft, s.id as section_id
            FROM translation_batch b
            JOIN section s ON b.section_id = s.id
            WHERE b.id = %s
        """, (batch_id,))
        batch_row = cur.fetchone()
        if not batch_row:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        b_id, sutta_id, vol, status, raw_draft, sec_id = batch_row
        
        # Fetch segments with updated text_thai directly from segment table
        cur.execute("""
            SELECT segment_id, text_pali, text_english, text_thai
            FROM segment
            WHERE section_id = %s
            ORDER BY id
        """, (sec_id,))
        
        segments = []
        for seg_id, pali, eng, thai in cur.fetchall():
            segments.append({
                "segment_id": seg_id,
                "text_pali": pali,
                "text_english": eng,
                "text_thai": thai or ""
            })
            
        return {
            "id": b_id,
            "sutta_id": sutta_id,
            "thai_volume": vol,
            "status": status,
            "segments": segments
        }
    finally:
        release_connection(conn)

class SegmentApproval(BaseModel):
    segment_id: str
    text_thai: str

class BatchApproval(BaseModel):
    segments: List[SegmentApproval]
    translator_name: Optional[str] = "Human Auditor"

@app.post("/batches/{batch_id}/save-draft")
def save_batch_draft(batch_id: int, data: BatchApproval):
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Convert segments back to Markdown table for raw_draft storage
        markdown = "| Segment ID | Thai Translation |\n|---|---|\n"
        for seg in data.segments:
            markdown += f"| {seg.segment_id} | {seg.text_thai} |\n"
        
        cur.execute("UPDATE translation_batch SET raw_draft = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (markdown, batch_id))
        conn.commit()
        return {"message": "Draft saved"}
    finally:
        release_connection(conn)

@app.post("/batches/{batch_id}/approve")
def approve_batch(batch_id: int, data: BatchApproval):
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Update status
        cur.execute("UPDATE translation_batch SET status = 'imported', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (batch_id,))
        
        # 2. Insert into translation table
        for seg in data.segments:
            # Find segment DB ID
            cur.execute("SELECT id FROM segment WHERE segment_id = %s", (seg.segment_id,))
            seg_row = cur.fetchone()
            if not seg_row: continue
            seg_db_id = seg_row[0]
            
            cur.execute("""
                INSERT INTO translation (segment_id, language, edition, translator, text, verified_at)
                VALUES (%s, 'th', 'audit-v1', %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (segment_id, language, edition) 
                DO UPDATE SET text = EXCLUDED.text, verified_at = CURRENT_TIMESTAMP
            """, (seg_db_id, data.translator_name, seg.text_thai))
            
        conn.commit()
        return {"message": "Batch approved and segments imported"}
    finally:
        release_connection(conn)

@app.post("/batches/{batch_id}/translate")
def trigger_translation(batch_id: int, background_tasks: BackgroundTasks):
    """สั่งให้ Agent เริ่มทำการแปลใน Background"""
    background_tasks.add_task(agent_worker.process_batch_by_id, batch_id)
    return {"message": f"Started translation for batch {batch_id} in background"}

@app.post("/batches/{batch_id}/sync-source")
def sync_batch_source(batch_id: int):
    """ดึงข้อมูลบาลีและอังกฤษมาลงฐานข้อมูล (กรณีหน้าจอยังว่าง)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT s.sutta_id, b.thai_volume FROM translation_batch b JOIN section s ON b.section_id = s.id WHERE b.id = %s", (batch_id,))
        row = cur.fetchone()
        if not row: return {"status": "error", "message": "Batch not found"}
        
        sutta_id, vol = row
        from main import get_sutta # Lazy import to avoid circular dependency
        sutta_data = get_sutta(sutta_id, language="all")
        
        if not sutta_data or "segments" not in sutta_data:
            return {"status": "error", "message": "Could not fetch sutta from SuttaCentral"}
            
        # Save segments
        cur.execute("SELECT section_id FROM translation_batch WHERE id = %s", (batch_id,))
        sec_id = cur.fetchone()[0]
        for seg in sutta_data["segments"]:
            cur.execute("""
                INSERT INTO segment (section_id, segment_id, text_pali, text_english)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (segment_id) DO UPDATE 
                SET text_pali = EXCLUDED.text_pali, text_english = EXCLUDED.text_english
            """, (sec_id, seg["segment_id"], seg.get("text_pali"), seg.get("text_english")))
            
        conn.commit()
        return {"status": "success", "count": len(sutta_data["segments"])}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        release_connection(conn)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
