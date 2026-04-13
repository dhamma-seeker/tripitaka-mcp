from db.connection import get_connection
conn = get_connection()
cur = conn.cursor()
keyword = 'กามคุณ'
query = """
    SELECT
        seg.segment_id,
        sec.sutta_id,
        seg.text_pali,
        t.text AS text_thai,
        seg.text_english,
        t.edition,
        similarity(t.text, %s) AS sim,
        word_similarity(%s, t.text) AS w_sim
    FROM translation t
    JOIN segment seg ON t.segment_id = seg.id
    JOIN section sec ON seg.section_id = sec.id
    JOIN book b ON sec.book_id = b.id
    JOIN nikaya n ON b.nikaya_id = n.id
    JOIN pitaka p ON n.pitaka_id = p.id
    WHERE t.language = 'th'
      AND (t.text % %s OR %s <% t.text)
    LIMIT 1
"""
params = [keyword, keyword, keyword, keyword]
cur.execute(query, params)
row = cur.fetchone()
print(f"Row length: {len(row) if row else 'None'}")
print(f"Row: {row}")
