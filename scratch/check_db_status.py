import os
from dotenv import load_dotenv
from db.connection import get_connection, release_connection

load_dotenv()

def check_status():
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        tables = ['pitaka', 'nikaya', 'book', 'section', 'segment', 'translation', 'dictionary']
        status = {}
        
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                status[table] = cur.fetchone()[0]
            except Exception as e:
                status[table] = f"Error: {str(e)}"
                conn.rollback()
        
        # Check embeddings
        try:
            cur.execute("SELECT COUNT(*) FROM segment WHERE embedding IS NOT NULL")
            status['segments_with_embeddings'] = cur.fetchone()[0]
        except Exception:
            status['segments_with_embeddings'] = "Column not found or error"
            conn.rollback()
            
        # Check editions
        try:
            cur.execute("SELECT edition, COUNT(*) FROM translation GROUP BY edition")
            status['editions'] = {row[0]: row[1] for row in cur.fetchall()}
        except Exception:
            status['editions'] = "Error"
            conn.rollback()
            
        return status
    finally:
        release_connection(conn)

if __name__ == "__main__":
    res = check_status()
    print("--- Project Database Status ---")
    for k, v in res.items():
        print(f"{k}: {v}")
