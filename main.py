"""
Tripitaka MCP Server — Main Entry Point

MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก
รองรับ 3 ภาษา: บาลี (Pali), ไทย (Thai), อังกฤษ (English)
ค้นหาได้ทั้ง keyword search และ semantic search

Usage:
    python main.py                  # รัน stdio transport (Claude Desktop / Cursor)
    MCP_TRANSPORT=sse python main.py  # รัน SSE transport (HTTP)

Tools:
    - search_by_keyword: ค้นหาด้วยคำสำคัญ
    - get_sutta: ดึงเนื้อหาสูตรตาม ID
    - search_semantic: ค้นหาตามความหมาย (vector similarity)
    - list_structure: แสดงโครงสร้างพระไตรปิฎก
    - get_reference: สร้างการอ้างอิงที่ถูกต้อง
"""

import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from db.connection import get_connection, release_connection
from db.schema import create_tables

load_dotenv()

# =============================================================================
# Initialize MCP Server
# =============================================================================
mcp = FastMCP(
    "Tripitaka",
    instructions=(
        "MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก (Tipiṭaka) "
        "รองรับ 3 ภาษา: บาลี (Pali), ไทย (Thai), อังกฤษ (English). "
        "ใช้สำหรับค้นหาพระสูตร, อ้างอิงคำสอนพระพุทธเจ้า, "
        "และเปรียบเทียบคำแปลข้ามภาษา."
    ),
)

# สร้างตารางตอน startup (ถ้ายังไม่มี)
try:
    create_tables()
except Exception:
    pass  # ถ้า DB ยังไม่พร้อม ให้ข้ามไปก่อน


# =============================================================================
# Helper Functions
# =============================================================================

LANGUAGE_COLUMNS = {
    "pali": "text_pali",
    "thai": "text_thai",
    "english": "text_english",
}


def _build_context(row: tuple, columns: list[str]) -> dict[str, Any]:
    """แปลง database row เป็น dict ตาม columns ที่กำหนด"""
    return dict(zip(columns, row))


# =============================================================================
# MCP Tools
# =============================================================================


@mcp.tool()
def search_by_keyword(
    keyword: str,
    language: str = "pali",
    edition: str | None = None,
    pitaka: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """ค้นหาข้อความในพระไตรปิฎกด้วย keyword

    ค้นหาแบบ trigram (fuzzy match) รองรับทั้ง 3 ภาษา
    สามารถกรองผลลัพธ์ตามปิฎกและฉบับแปลได้

    Args:
        keyword: คำที่ต้องการค้นหา
        language: ภาษาที่ค้นหา — "pali", "thai", หรือ "english" (default: "pali")
        edition: ฉบับแปลภาษาไทย — "dhiranandi", "jayasaro", "mbu", "royal" หรือ None
                 ใช้เฉพาะเมื่อ language="thai" เพื่อเลือกฉบับที่ต้องการ
                 ถ้าไม่ระบุ จะค้นจาก text_thai (bilara-data) ก่อน แล้วค้นจาก translation table
        pitaka: กรองตามปิฎก — "vinaya", "sutta", "abhidhamma" หรือ None (ค้นทั้งหมด)
        limit: จำนวนผลลัพธ์สูงสุด (default: 10, max: 50)

    Returns:
        รายการผลลัพธ์ แต่ละรายการมี:
        - segment_id: รหัส segment (เช่น "mn1:1.1")
        - sutta_id: รหัสสูตร (เช่น "mn1")
        - text_pali: เนื้อหาภาษาบาลี
        - text_thai: เนื้อหาภาษาไทย (ถ้ามี)
        - text_english: เนื้อหาภาษาอังกฤษ (ถ้ามี)
        - edition: ฉบับแปลที่ใช้ (ถ้าค้นจาก translation table)
        - similarity: คะแนนความคล้ายคลึง (0-1)
    """
    limit = min(max(1, limit), 50)

    conn = get_connection()
    try:
        cur = conn.cursor()

        # ค้นหาจาก translation table เมื่อภาษาไทยและระบุ edition
        # หรือเมื่อต้องการค้นจากฉบับแปลที่เพิ่มเข้ามา
        if language == "thai" and edition:
            query = """
                SELECT
                    seg.segment_id,
                    sec.sutta_id,
                    seg.text_pali,
                    t.text AS text_thai,
                    seg.text_english,
                    t.edition,
                    similarity(t.text, %s) AS sim
                FROM translation t
                JOIN segment seg ON t.segment_id = seg.id
                JOIN section sec ON seg.section_id = sec.id
                JOIN book b ON sec.book_id = b.id
                JOIN nikaya n ON b.nikaya_id = n.id
                JOIN pitaka p ON n.pitaka_id = p.id
                WHERE t.language = 'th'
                  AND t.edition = %s
                  AND t.text %% %s
            """
            params: list[Any] = [keyword, edition, keyword]

            if pitaka:
                query += " AND p.code = %s"
                params.append(pitaka)

            query += " ORDER BY sim DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            columns = ["segment_id", "sutta_id", "text_pali", "text_thai", "text_english", "edition", "similarity"]
            results = [_build_context(row, columns) for row in cur.fetchall()]

        else:
            # ค้นหาจาก segment table (pali/english/thai จาก bilara-data)
            if language not in LANGUAGE_COLUMNS:
                return [{"error": f"ภาษาไม่ถูกต้อง: {language}. ใช้ได้: pali, thai, english"}]

            text_col = LANGUAGE_COLUMNS[language]
            query = f"""
                SELECT
                    seg.segment_id,
                    sec.sutta_id,
                    seg.text_pali,
                    seg.text_thai,
                    seg.text_english,
                    similarity(seg.{text_col}, %s) AS sim
                FROM segment seg
                JOIN section sec ON seg.section_id = sec.id
                JOIN book b ON sec.book_id = b.id
                JOIN nikaya n ON b.nikaya_id = n.id
                JOIN pitaka p ON n.pitaka_id = p.id
                WHERE seg.{text_col} %% %s
            """
            params = [keyword, keyword]

            if pitaka:
                query += " AND p.code = %s"
                params.append(pitaka)

            query += " ORDER BY sim DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            columns = ["segment_id", "sutta_id", "text_pali", "text_thai", "text_english", "similarity"]
            results = [_build_context(row, columns) for row in cur.fetchall()]

        if not results:
            hint = f" (edition: {edition})" if edition else ""
            return [{"message": f"ไม่พบผลลัพธ์สำหรับ '{keyword}' ในภาษา {language}{hint}"}]

        return results

    except Exception as e:
        return [{"error": f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"}]
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def get_sutta(
    sutta_id: str,
    language: str = "pali",
    edition: str | None = None,
) -> dict[str, Any]:
    """ดึงเนื้อหาสูตร/กัณฑ์ตาม ID

    ใช้รหัสมาตรฐาน SuttaCentral เช่น:
    - mn1 = มัชฌิมนิกาย สูตรที่ 1 (มูลปริยายสูตร)
    - dn22 = ทีฆนิกาย สูตรที่ 22 (มหาสติปัฏฐานสูตร)
    - sn56.11 = สังยุตตนิกาย 56.11 (ธัมมจักกัปปวัตตนสูตร)

    Args:
        sutta_id: รหัสสูตร เช่น "mn1", "dn22", "sn56.11"
        language: ภาษาที่ต้องการ — "pali", "thai", "english", หรือ "all" (default: "pali")
        edition: ฉบับแปลภาษาไทย — "dhiranandi", "jayasaro", "mbu", "royal" หรือ None
                 ถ้าไม่ระบุ จะใช้ text_thai จาก bilara-data (ถ้ามี)

    Returns:
        ข้อมูลสูตรประกอบด้วย:
        - sutta_id: รหัสสูตร
        - title: ชื่อสูตร (ถ้ามี)
        - nikaya: ชื่อนิกาย
        - pitaka: ชื่อปิฎก
        - edition: ฉบับแปลที่ใช้ (ถ้าระบุ)
        - segments: เนื้อหาเรียงตาม segment
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ดึงข้อมูล section + metadata
        cur.execute(
            """
            SELECT
                sec.id,
                sec.sutta_id,
                sec.title_pali,
                sec.title_thai,
                sec.title_english,
                n.name_pali AS nikaya_pali,
                n.name_thai AS nikaya_thai,
                n.name_english AS nikaya_english,
                p.name_pali AS pitaka_pali,
                p.name_thai AS pitaka_thai,
                p.name_english AS pitaka_english
            FROM section sec
            JOIN book b ON sec.book_id = b.id
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE sec.sutta_id = %s
            """,
            (sutta_id,),
        )
        section_row = cur.fetchone()

        if not section_row:
            return {"error": f"ไม่พบสูตร: {sutta_id}"}

        section_id = section_row[0]

        # ดึง segments พร้อม translation จาก edition ที่ระบุ (ถ้ามี)
        if edition and language in ("thai", "all"):
            cur.execute(
                """
                SELECT seg.segment_id, seg.text_pali, t.text AS text_thai, seg.text_english
                FROM segment seg
                LEFT JOIN translation t ON t.segment_id = seg.id
                    AND t.language = 'th'
                    AND t.edition = %s
                WHERE seg.section_id = %s
                ORDER BY seg.id
                """,
                (edition, section_id),
            )
        else:
            cur.execute(
                """
                SELECT segment_id, text_pali, text_thai, text_english
                FROM segment
                WHERE section_id = %s
                ORDER BY id
                """,
                (section_id,),
            )
        segment_rows = cur.fetchall()

        # สร้าง segments ตามภาษาที่ต้องการ
        segments = []
        for seg_row in segment_rows:
            seg = {"segment_id": seg_row[0]}
            if language in ("pali", "all"):
                seg["text_pali"] = seg_row[1]
            if language in ("thai", "all"):
                seg["text_thai"] = seg_row[2]
            if language in ("english", "all"):
                seg["text_english"] = seg_row[3]
            segments.append(seg)

        return {
            "sutta_id": section_row[1],
            "title": {
                "pali": section_row[2],
                "thai": section_row[3],
                "english": section_row[4],
            },
            "nikaya": {
                "pali": section_row[5],
                "thai": section_row[6],
                "english": section_row[7],
            },
            "pitaka": {
                "pali": section_row[8],
                "thai": section_row[9],
                "english": section_row[10],
            },
            "edition": edition,
            "segment_count": len(segments),
            "segments": segments,
        }

    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def search_semantic(
    query: str,
    language: str = "pali",
    limit: int = 5,
    threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """ค้นหาแบบ semantic — ค้นหาตามความหมาย ไม่จำเป็นต้องตรงคำ

    ใช้ vector similarity search (cosine distance) เพื่อหาเนื้อหา
    ที่มีความหมายใกล้เคียงกับ query
    รองรับการค้นหาข้ามภาษา (เช่น ถามเป็นไทย ค้นเจอบาลี)

    Args:
        query: ข้อความที่ต้องการค้นหา (ภาษาอะไรก็ได้)
        language: ภาษาที่ต้องการแสดงผล — "pali", "thai", "english", หรือ "all"
        limit: จำนวนผลลัพธ์สูงสุด (default: 5, max: 20)
        threshold: ระยะห่างความหมาย (ยิ่งน้อยยิ่งตรงเผง, default: 0.7)

    Returns:
        รายการผลลัพธ์เรียงตามความใกล้เคียงทางความหมาย
        แต่ละรายการมี:
        - segment_id, sutta_id, text (ตามภาษา), distance
    """
    limit = min(max(1, limit), 20)

    try:
        # สร้าง embedding จาก query
        from embedding.model import generate_embedding

        query_embedding = generate_embedding(query)
    except ImportError:
        return [{"error": "Embedding module ยังไม่ได้ติดตั้ง — กรุณาใช้ search_by_keyword แทน"}]
    except Exception as e:
        return [{"error": f"ไม่สามารถสร้าง embeddingได้: {str(e)}"}]

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                seg.segment_id,
                sec.sutta_id,
                seg.text_pali,
                seg.text_thai,
                seg.text_english,
                seg.embedding <=> %s::vector AS distance
            FROM segment seg
            JOIN section sec ON seg.section_id = sec.id
            WHERE seg.embedding IS NOT NULL
              AND (seg.embedding <=> %s::vector) <= %s
            ORDER BY distance
            LIMIT %s
            """,
            (query_embedding, query_embedding, threshold, limit),
        )

        columns = ["segment_id", "sutta_id", "text_pali", "text_thai", "text_english", "distance"]
        results = [_build_context(row, columns) for row in cur.fetchall()]

        if not results:
            return [{"message": f"ไม่พบผลลัพธ์ที่ตรงกับความหมาย (ระยะวิเคราะห์ < {threshold}) — ทดลองคลาย threshold เพื่อค้นหาแบบกว้าง"}]

        return results

    except Exception as e:
        return [{"error": f"เกิดข้อผิดพลาดในการค้นหา: {str(e)}"}]
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def search_hybrid(
    query: str,
    language: str = "pali",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """ค้นหาแบบผสมผสาน (Hybrid Search) — รวมพลัง Keyword + Semantic
    
    ใช้เทคนิค RRF (Reciprocal Rank Fusion) เพื่อนำผลลัพธ์จาก
    การค้นหาคำตรงๆ มารวมกับผลลัพธ์จากการค้นหาความหมาย
    ทำให้ระบบค้นหาครอบคลุมที่สุด หาอะไรก็เจอแน่ๆ
    
    Args:
        query: ข้อความ (ภาษาไทย, บาลี หรืออังกฤษ)
        language: ภาษาที่ต้องการให้แสดงในผลลัพธ์ ("pali", "thai", "english", "all")
        limit: จำนวนข้อความที่ต้องการค้นพบ

    Returns:
        รายการประโยคจากพระไตรปิฎกที่มีค่า rrf_score สูงที่สุด 
    """
    limit = min(max(1, limit), 20)
    
    try:
        from embedding.model import generate_embedding
        query_embedding = generate_embedding(query)
    except Exception as e:
        return [{"error": f"ไม่สามารถสร้าง embedding ได้: {str(e)}"}]
        
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Semantic Search (Top 50)
        cur.execute(
            """
            SELECT seg.id, seg.embedding <=> %s::vector AS distance
            FROM segment seg
            WHERE seg.embedding IS NOT NULL
            ORDER BY distance
            LIMIT 50
            """,
            (query_embedding,)
        )
        semantic_results = cur.fetchall()
        semantic_ranks = {row[0]: rank + 1 for rank, row in enumerate(semantic_results)}

        # 2. Keyword Search (Top 50)
        # Using ILIKE to search across all text fields
        cur.execute(
            """
            SELECT seg.id
            FROM segment seg
            WHERE seg.text_pali ILIKE %s OR seg.text_thai ILIKE %s OR seg.text_english ILIKE %s
            LIMIT 50
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%")
        )
        keyword_results = cur.fetchall()
        keyword_ranks = {row[0]: rank + 1 for rank, row in enumerate(keyword_results)}

        # 3. Reciprocal Rank Fusion (RRF) Scoring
        k = 60
        rrf_scores = {}
        all_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())
        
        for seg_id in all_ids:
            score = 0.0
            if seg_id in semantic_ranks:
                score += 1.0 / (k + semantic_ranks[seg_id])
            if seg_id in keyword_ranks:
                score += 1.0 / (k + keyword_ranks[seg_id])
            rrf_scores[seg_id] = score
            
        # Select Top N
        top_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:limit]
        
        if not top_ids:
            return [{"message": "ไม่พบผลลัพธ์จาก Hybrid Search"}]
            
        # Fetch actual segment content
        format_strings = ','.join(['%s'] * len(top_ids))
        cur.execute(
            f"""
            SELECT
                seg.id,
                seg.segment_id,
                sec.sutta_id,
                seg.text_pali,
                seg.text_thai,
                seg.text_english
            FROM segment seg
            JOIN section sec ON seg.section_id = sec.id
            WHERE seg.id IN ({format_strings})
            """,
            tuple(top_ids)
        )
        
        id_to_row = {row[0]: row for row in cur.fetchall()}
        
        columns = ["segment_id", "sutta_id", "text_pali", "text_thai", "text_english", "rrf_score"]
        results = []
        for seg_id in top_ids:
            if seg_id in id_to_row:
                row = id_to_row[seg_id]
                context_row = (row[1], row[2], row[3], row[4], row[5], round(rrf_scores[seg_id], 4))
                results.append(_build_context(context_row, columns))
                
        return results

    except Exception as e:
        return [{"error": f"เกิดข้อผิดพลาดในการค้นหา hybrid: {str(e)}"}]
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def list_structure() -> dict[str, Any]:
    """แสดงโครงสร้างพระไตรปิฎกทั้ง 3 ปิฎก

    Returns:
        โครงสร้างแบบ hierarchical:
        - pitakas → nikayas พร้อมจำนวนสูตรในแต่ละนิกาย
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                p.code AS pitaka_code,
                p.name_pali AS pitaka_pali,
                p.name_thai AS pitaka_thai,
                p.name_english AS pitaka_english,
                n.code AS nikaya_code,
                n.name_pali AS nikaya_pali,
                n.name_thai AS nikaya_thai,
                n.name_english AS nikaya_english,
                COUNT(DISTINCT sec.id) AS sutta_count,
                COUNT(seg.id) AS segment_count
            FROM pitaka p
            LEFT JOIN nikaya n ON n.pitaka_id = p.id
            LEFT JOIN book b ON b.nikaya_id = n.id
            LEFT JOIN section sec ON sec.book_id = b.id
            LEFT JOIN segment seg ON seg.section_id = sec.id
            GROUP BY p.id, p.code, p.name_pali, p.name_thai, p.name_english,
                     n.id, n.code, n.name_pali, n.name_thai, n.name_english
            ORDER BY p.sort_order, n.sort_order
            """
        )

        # จัดกลุ่มเป็น hierarchical structure
        structure: dict[str, Any] = {}
        for row in cur.fetchall():
            pitaka_code = row[0]
            if pitaka_code not in structure:
                structure[pitaka_code] = {
                    "name_pali": row[1],
                    "name_thai": row[2],
                    "name_english": row[3],
                    "nikayas": [],
                }

            if row[4]:  # nikaya_code
                structure[pitaka_code]["nikayas"].append({
                    "code": row[4],
                    "name_pali": row[5],
                    "name_thai": row[6],
                    "name_english": row[7],
                    "sutta_count": row[8],
                    "segment_count": row[9],
                })

        return {"pitakas": structure}

    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def get_reference(
    sutta_id: str,
) -> dict[str, Any]:
    """สร้างข้อมูลอ้างอิง (reference) ที่ถูกต้องสำหรับสูตร

    ใช้เพื่อสร้างการอ้างอิงที่ถูกต้องตามหลักวิชาการ
    เมื่อต้องการอ้างอิงเนื้อหาจากพระไตรปิฎก

    Args:
        sutta_id: รหัสสูตร เช่น "mn1", "dn22", "sn56.11"

    Returns:
        ข้อมูลอ้างอิงประกอบด้วย:
        - sutta_id: รหัสสูตร
        - title: ชื่อสูตร (3 ภาษา)
        - location: ตำแหน่งในพระไตรปิฎก
        - citation_format: รูปแบบการอ้างอิงสำเร็จรูป
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                sec.sutta_id,
                sec.title_pali,
                sec.title_thai,
                sec.title_english,
                n.name_pali AS nikaya_pali,
                n.name_thai AS nikaya_thai,
                n.name_english AS nikaya_english,
                n.code AS nikaya_code,
                p.name_pali AS pitaka_pali,
                p.name_thai AS pitaka_thai,
                p.name_english AS pitaka_english,
                COUNT(seg.id) AS segment_count
            FROM section sec
            JOIN book b ON sec.book_id = b.id
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            LEFT JOIN segment seg ON seg.section_id = sec.id
            WHERE sec.sutta_id = %s
            GROUP BY sec.id, sec.sutta_id, sec.title_pali, sec.title_thai,
                     sec.title_english, n.name_pali, n.name_thai, n.name_english,
                     n.code, p.name_pali, p.name_thai, p.name_english
            """,
            (sutta_id,),
        )
        row = cur.fetchone()

        if not row:
            return {"error": f"ไม่พบสูตร: {sutta_id}"}

        title_pali = row[1] or sutta_id
        title_english = row[3] or ""
        nikaya_english = row[6] or ""
        nikaya_code = row[7] or ""

        # สร้างรูปแบบการอ้างอิง
        citation = f"{title_pali} ({sutta_id.upper()}), {nikaya_english}"
        if title_english:
            citation = f"{title_english} ({title_pali}, {sutta_id.upper()}), {nikaya_english}"

        return {
            "sutta_id": row[0],
            "title": {
                "pali": row[1],
                "thai": row[2],
                "english": row[3],
            },
            "location": {
                "nikaya": {
                    "code": nikaya_code,
                    "pali": row[4],
                    "thai": row[5],
                    "english": row[6],
                },
                "pitaka": {
                    "pali": row[8],
                    "thai": row[9],
                    "english": row[10],
                },
            },
            "segment_count": row[11],
            "citation_format": citation,
            "suttacentral_url": f"https://suttacentral.net/{sutta_id}/pli/ms",
        }

    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


# =============================================================================
# MCP Tools — Translation Edition
# =============================================================================


@mcp.tool()
def list_editions() -> list[dict[str, Any]]:
    """แสดงรายการฉบับแปลภาษาไทยที่มีในระบบ

    แสดงทุก edition ที่ถูก load เข้า translation table พร้อมสถิติ

    Returns:
        รายการ edition แต่ละรายการมี:
        - edition: รหัสฉบับ เช่น "dhiranandi", "mbu"
        - translator: ชื่อผู้แปล
        - language: ภาษา
        - segment_count: จำนวน segments ที่มีคำแปล
        - sutta_count: จำนวนสูตรที่มีคำแปล
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                t.edition,
                t.translator,
                t.language,
                COUNT(t.id) AS segment_count,
                COUNT(DISTINCT sec.sutta_id) AS sutta_count
            FROM translation t
            JOIN segment seg ON t.segment_id = seg.id
            JOIN section sec ON seg.section_id = sec.id
            GROUP BY t.edition, t.translator, t.language
            ORDER BY t.language, t.edition
        """)
        columns = ["edition", "translator", "language", "segment_count", "sutta_count"]
        results = [_build_context(row, columns) for row in cur.fetchall()]

        if not results:
            return [{"message": "ยังไม่มีฉบับแปลเพิ่มเติมในระบบ"}]

        return results

    except Exception as e:
        return [{"error": f"เกิดข้อผิดพลาด: {str(e)}"}]
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def compare_translations(
    segment_id: str,
) -> dict[str, Any]:
    """เปรียบเทียบคำแปลทุกฉบับที่มีสำหรับ segment เดียวกัน

    ใช้เพื่อตรวจสอบความถูกต้องและเปรียบเทียบสำนวนของผู้แปลต่างๆ
    รวมทั้งต้นฉบับบาลีและคำแปลอังกฤษ

    Args:
        segment_id: รหัส segment เช่น "mn26:8.2", "dn22:17.1"

    Returns:
        ข้อมูลเปรียบเทียบประกอบด้วย:
        - segment_id: รหัส segment
        - sutta_id: รหัสสูตร
        - text_pali: ต้นฉบับบาลี
        - text_english: คำแปลอังกฤษ (Sujato/bilara-data)
        - text_thai_default: คำแปลไทยจาก bilara-data (ถ้ามี)
        - translations: คำแปลจากทุก edition ใน translation table
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ดึง segment หลัก
        cur.execute(
            """
            SELECT seg.id, seg.segment_id, sec.sutta_id,
                   seg.text_pali, seg.text_thai, seg.text_english
            FROM segment seg
            JOIN section sec ON seg.section_id = sec.id
            WHERE seg.segment_id = %s
            """,
            (segment_id,),
        )
        row = cur.fetchone()
        if not row:
            return {"error": f"ไม่พบ segment: {segment_id}"}

        seg_db_id, seg_id, sutta_id, text_pali, text_thai_default, text_english = row

        # ดึงคำแปลจาก translation table ทุก edition
        cur.execute(
            """
            SELECT edition, translator, language, text, alignment_confidence, alignment_status
            FROM translation
            WHERE segment_id = %s
            ORDER BY language, edition
            """,
            (seg_db_id,),
        )
        translations = [
            {
                "edition": r[0],
                "translator": r[1],
                "language": r[2],
                "text": r[3],
                "alignment_confidence": r[4],
                "alignment_status": r[5],
            }
            for r in cur.fetchall()
        ]

        return {
            "segment_id": seg_id,
            "sutta_id": sutta_id,
            "text_pali": text_pali,
            "text_english": text_english,
            "text_thai_default": text_thai_default,
            "translations": translations,
            "total_editions": len(translations),
        }

    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def get_word_definition(word: str, language: str = "all", limit_context: int = 3) -> dict[str, Any]:
    """ดึงความหมายพจนานุกรมของคําศัพท์บาลี พร้อมด้วยตัวอย่างประโยคบริบทในพระสูตร
    
    ใช้เป็น Pali Dictionary Bridge เพื่อทำความเข้าใจความหมายแท้จริงของคำ 
    โดยนำเสนอ "นิยาม" ควบคู่กับ "บริบทที่พระพุทธองค์ทรงใช้จริง"

    Args:
        word: คำที่ต้องการค้นหา (เช่น "dukkha", "กฐิน")
        language: ภาษาของพจนานุกรม (เช่น "en", "thai", หรือ "all" เป็นค่าเริ่มต้น)
        limit_context: จำนวนตัวอย่างประโยคในพระสูตรที่จะแสดง (1-5)

    Returns:
        ข้อมูลพจนานุกรมจาก SuttaCentral/Payutto และตัวอย่างบริบทการใช้คำนั้นจาก segment
    """
    word_search = word.lower().strip()
    limit_context = min(max(1, limit_context), 5)
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Fetch definitions from dictionary table
        if language == "all":
            cur.execute(
                """
                SELECT source, text 
                FROM dictionary 
                WHERE word = %s 
                ORDER BY source
                """,
                (word_search,)
            )
        else:
            cur.execute(
                """
                SELECT source, text 
                FROM dictionary 
                WHERE word = %s AND language = %s
                ORDER BY source
                """,
                (word_search, language)
            )
            
        definitions = [{"source": r[0], "text": r[1]} for r in cur.fetchall()]
        
        if not definitions:
            # Fallback fuzzy match just in case
            if language == "all":
                cur.execute(
                    """
                    SELECT word, source, text
                    FROM dictionary
                    WHERE word ILIKE %s
                    ORDER BY length(word)
                    LIMIT 3
                    """,
                    (f"{word_search}%",)
                )
            else:
                cur.execute(
                    """
                    SELECT word, source, text
                    FROM dictionary
                    WHERE word ILIKE %s AND language = %s
                    ORDER BY length(word)
                    LIMIT 3
                    """,
                    (f"{word_search}%", language)
                )
            fallback = cur.fetchall()
            if fallback:
                definitions = [{"word": r[0], "source": r[1], "text": r[2]} for r in fallback]
                return {
                    "note": f"ไม่พบคำตรงตัวสำหรับ '{word}' แต่พบคำที่ใกล้เคียง:",
                    "suggestions": definitions
                }
            return {"error": f"ไม่พบคำว่า '{word}' ในพจนานุกรม"}
            
        # 2. Fetch context from segment where text_pali contains the word
        # ใช้ ROW_NUMBER() + PARTITION BY เพื่อให้ดึงแค่ 1 ตัวอย่างต่อพระสูตร 
        # และ ORDER BY random() เพื่อสุ่มความหลากหลายของนิกาย
        cur.execute(
            """
            WITH matched AS (
                SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english, seg.text_thai,
                       ROW_NUMBER() OVER (PARTITION BY sec.sutta_id ORDER BY random()) as rn
                FROM segment seg
                JOIN section sec ON seg.section_id = sec.id
                WHERE seg.text_pali ~* %s
            )
            SELECT sutta_id, segment_id, text_pali, text_english, text_thai
            FROM matched
            WHERE rn = 1
            ORDER BY random()
            LIMIT %s
            """,
            (f"\\y{word_search}\\y", limit_context)
        )
        appears_in = [
            {
                "sutta_id": r[0],
                "segment_id": r[1],
                "pali": r[2],
                "english": r[3],
                "thai": r[4]
            }
            for r in cur.fetchall()
        ]
        
        # If no strict word boundary match, fall back to simple ILIKE
        if not appears_in:
            cur.execute(
                """
                WITH matched AS (
                    SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english, seg.text_thai,
                           ROW_NUMBER() OVER (PARTITION BY sec.sutta_id ORDER BY random()) as rn
                    FROM segment seg
                    JOIN section sec ON seg.section_id = sec.id
                    WHERE seg.text_pali ILIKE %s
                )
                SELECT sutta_id, segment_id, text_pali, text_english, text_thai
                FROM matched
                WHERE rn = 1
                ORDER BY random()
                LIMIT %s
                """,
                (f"%{word_search}%", limit_context)
            )
            appears_in = [
                {
                    "sutta_id": r[0],
                    "segment_id": r[1],
                    "pali": r[2],
                    "english": r[3],
                    "thai": r[4]
                }
                for r in cur.fetchall()
            ]
        
        # 3. Find related words (Compound words)
        cur.execute(
            """
            SELECT word 
            FROM dictionary 
            WHERE word LIKE %s AND word != %s
            GROUP BY word
            ORDER BY length(word), word
            LIMIT 10
            """,
            (f"%{word_search}%", word_search)
        )
        related_words = [r[0] for r in cur.fetchall()]

        return {
            "word": word,
            "definitions": definitions,
            "related_words": related_words,
            "appears_in_context": appears_in
        }
        
    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def parse_pali_word(word: str) -> dict[str, Any]:
    """วิเคราะห์คำบาลีเพื่อหารากศัพท์ (Stemming/Lemmatization เบื้องต้น)
    
    ใช้เมื่อเจอคำศัพท์บาลีที่ถูกแจกวิภัตติแล้ว (มี suffix) และค้นหาในพจนานุกรมไม่พบ
    Tool นี้จะช่วยตัด Suffix ภาษาบาลีที่พบบ่อย และเดารากศัพท์ให้
    
    Args:
        word: คำบาลีที่ต้องการวิเคราะห์ (เช่น "dukkhassa", "bhikkhūnaṁ")

    Returns:
        รากศัพท์ดั้งเดิมที่น่าจะเป็นไปได้ ซึ่งสามารถนำไปค้นใน get_word_definition ต่อได้
    """
    word = word.lower().strip()
    
    # Common Pali suffixes -> possible stem endings
    suffixes = {
        "ānaṁ": ["a", "ā", "i", "ī", "u", "ū"],
        "naṁ": ["a", "ā", "i", "ī", "u", "ū"],
        "āya": ["a", "ā"],
        "assa": ["a"],
        "ssa": ["a", "i", "u"],
        "smā": ["a"],
        "mhā": ["a"],
        "smiṁ": ["a"],
        "mhi": ["a"],
        "ena": ["a"],
        "ebhi": ["a"],
        "ehi": ["a"],
        "esu": ["a", "i", "u"],
        "su": ["a", "ā", "i", "ī", "u", "ū"],
        "aṁ": ["a", "ā"],
        "ṁ": ["a", "i", "u"],
        "āni": ["a"],
        "ni": ["i", "u"],
        "e": ["a"],
        "ā": ["a"],
        "o": ["a", "u"]
    }
    
    possible_stems = set()
    possible_stems.add(word)
    matched_suffixes = []
    
    for suffix, replacements in suffixes.items():
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            base = word[:-len(suffix)]
            matched_suffixes.append(suffix)
            for r in replacements:
                possible_stems.add(base + r)
                
    # Rule for long vowel shortening before some suffixes
    if word.endswith("ūnaṁ") or word.endswith("īnaṁ"):
        base = word[:-4]
        vowel = "i" if word.endswith("īnaṁ") else "u"
        possible_stems.add(base + vowel)
        matched_suffixes.append(word[-4:])

    return {
        "original_word": word,
        "matched_suffixes_removed": list(set(matched_suffixes)),
        "possible_stems": list(possible_stems),
        "guidance": "ลองนำคำใน possible_stems ไปค้นใน get_word_definition เพื่อหาความหมายที่แท้จริง"
    }


# =============================================================================
# MCP Resources
# =============================================================================


@mcp.resource("tripitaka://structure")
def structure_resource() -> str:
    """โครงสร้างพระไตรปิฎกทั้ง 3 ปิฎก"""
    import json

    result = list_structure()
    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    print(f"🛕 Tripitaka MCP Server starting... (transport: {transport})")
    mcp.run(transport=transport)
