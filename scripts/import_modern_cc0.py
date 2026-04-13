import re
import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def import_draft():
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    draft_path = "drafts/SN56.11_MODERN_TH.md"
    if not os.path.exists(draft_path):
        print(f"Error: {draft_path} not found")
        return
        
    with open(draft_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extract table rows: | segment_id | pali | english | thai |
    # Regex for markdown table row
    pattern = re.compile(r"\|\s*([a-z0-9.:-]+)\s*\|\s*.*?\s*\|\s*.*?\s*\|\s*(.*?)\s*\|")
    
    matches = pattern.findall(content)
    
    imported_count = 0
    now = datetime.now()
    verifier = "User (Human-in-the-loop)"
    edition = "modern-cc0"
    
    print(f"Importing {len(matches)} segments for edition '{edition}'...")
    
    for segment_id_str, text_thai in matches:
        if segment_id_str in ["Segment", "---", ":---"]:
            continue
            
        # Ensure it has the sutta prefix
        full_segment_id = segment_id_str
        if not segment_id_str.startswith("sn56.11:"):
            full_segment_id = f"sn56.11:{segment_id_str}"
            
        # Get internal segment ID
        cur.execute("SELECT id FROM segment WHERE segment_id = %s", (full_segment_id,))
        row = cur.fetchone()
        if not row:
            # Try without prefix just in case (e.g. 0.1)
            cur.execute("SELECT id FROM segment WHERE segment_id = %s", (segment_id_str,))
            row = cur.fetchone()
            
        if not row:
            print(f"Warning: Segment {full_segment_id} (or {segment_id_str}) not found in database")
            continue
            
        seg_internal_id = row[0]
        
        # Insert or Update translation
        cur.execute("""
            INSERT INTO translation (segment_id, language, edition, text, verified_by, verified_at)
            VALUES (%s, 'th', %s, %s, %s, %s)
            ON CONFLICT (segment_id, language, edition) 
            DO UPDATE SET 
                text = EXCLUDED.text,
                verified_by = EXCLUDED.verified_by,
                verified_at = EXCLUDED.verified_at
        """, (seg_internal_id, edition, text_thai, verifier, now))
        
        imported_count += 1
        
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully imported {imported_count} segments.")

if __name__ == "__main__":
    import_draft()
