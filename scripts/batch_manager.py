import os
from db.connection import get_connection

def init_batches(volume_number):
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all sections in this volume that don't have a batch yet
    cur.execute("""
        SELECT sec.id, sec.sutta_id 
        FROM section sec
        JOIN book b ON sec.book_id = b.id
        WHERE b.thai_volume = %s
          AND sec.id NOT IN (SELECT section_id FROM translation_batch)
        ORDER BY sec.id
    """, (volume_number,))
    
    sections = cur.fetchall()
    print(f"Initializing {len(sections)} batches for Volume {volume_number}...")
    
    created = 0
    for sec_id, sutta_id in sections:
        cur.execute("""
            INSERT INTO translation_batch (section_id, thai_volume, status)
            VALUES (%s, %s, 'pending')
        """, (sec_id, volume_number))
        created += 1
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"Successfully created {created} batch entries.")

if __name__ == "__main__":
    import sys
    vol = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    init_batches(vol)
