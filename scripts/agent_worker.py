import os
import anthropic
from dotenv import load_dotenv
from scripts import budget_manager
from main import get_sutta, get_word_definition
from db.connection import get_connection

load_dotenv()

# Constants
MODEL_NAME = "claude-3-5-sonnet-20240620"
STRATEGIC_TERMS = ["dukkha", "taṇhā", "magga", "nirodha", "ariyasacca", "bhikkhave", "tathāgata"]
MAX_BUDGET_USD = float(os.getenv("MAX_BUDGET_USD", "5.0"))

def get_conventions():
    conv_path = "CONVENTIONS_TH.md"
    if os.path.exists(conv_path):
        with open(conv_path, "r", encoding="utf-8") as f:
            return f.read()
    return "No style guide found."

def call_claude(prompt):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "Error: ANTHROPIC_API_KEY not found in .env"
        
    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=4000,
            temperature=0,
            system="You are a professional Pali-to-Thai Tripitaka translator. Follow the provided Style Guide and Terminology strictly.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Track usage
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        text_response = message.content[0].text
        
        return text_response, (input_tokens, output_tokens)
    except Exception as e:
        return None, str(e)

def draft_translation(sutta_id, volume_number, batch_id):
    """
    Calls Claude 3.5 to draft the translation in small chunks.
    """
    # 1. Check Budget
    if not budget_manager.can_afford(MAX_BUDGET_USD):
        return None, f"Budget limit reached (${MAX_BUDGET_USD}). Please top up."

    # 2. Fetch Source Content
    sutta_data = get_sutta(sutta_id, language="all")
    if not sutta_data or not isinstance(sutta_data, dict) or "segments" not in sutta_data:
        return None, "Sutta data invalid"
        
    all_segments = sutta_data["segments"]
    
    # 3. Terminology & Conventions
    terminology_context = []
    for term in STRATEGIC_TERMS:
        defn = get_word_definition(term)
        if defn:
            terminology_context.append(f"- {term}: {defn}")
    conventions = get_conventions()
    
    # 4. CHUNKING LOGIC: Process 25 segments at a time (Claude can handle more, but 25 is safe)
    chunk_size = 25
    full_thai_draft = "| Segment ID | Thai Translation |\n|---|---|\n"
    
    for i in range(0, len(all_segments), chunk_size):
        chunk = all_segments[i:i+chunk_size]
        print(f"  - [Claude] Translating chunk {i//chunk_size + 1}/{len(all_segments)//chunk_size + 1}...")
        
        source_text = ""
        for seg in chunk:
            source_text += f"{seg['segment_id']} | {seg.get('text_pali', '')} | {seg.get('text_english', '')}\n"

        prompt = f"""
[STYLE GUIDE]
{conventions}

[TERMINOLOGY]
{chr(10).join(terminology_context)}

[SOURCE DATA (ID | PALI | ENGLISH)]
{source_text}

[INSTRUCTIONS]
1. Translate to Thai (Modern CC0 Style).
2. Maintain Segment ID.
3. OUTPUT ONLY MARKDOWN TABLE ROWS.
4. Format: | Segment ID | Thai Translation |
"""
        response_text, usage_or_err = call_claude(prompt)
        if isinstance(usage_or_err, str):
            return None, f"API Error: {usage_or_err}"
            
        # Record budget
        in_t, out_t = usage_or_err
        budget_manager.record_usage(f"{batch_id}_chk_{i}", in_t, out_t)
        
        full_thai_draft += response_text + "\n"

    return full_thai_draft, None

def process_next_batch():
    conn = get_connection()
    cur = conn.cursor()
    
    # Find next pending batch
    cur.execute("""
        SELECT b.id, s.sutta_id, b.thai_volume 
        FROM translation_batch b
        JOIN section s ON b.section_id = s.id
        WHERE b.status = 'pending'
        ORDER BY b.thai_volume, b.id
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        print("No pending batches found.")
        return
        
    batch_id, sutta_id, vol = row
    print(f"Processing Batch {batch_id}: {sutta_id} (Volume {vol})...")
    
    # Update status to drafting
    cur.execute("UPDATE translation_batch SET status = 'drafting', agent_id = 'Antigravity' WHERE id = %s", (batch_id,))
    conn.commit()
    
    try:
        draft_content, error = draft_translation(sutta_id, vol, batch_id)
        if error:
            cur.execute("UPDATE translation_batch SET status = 'error', error_log = %s WHERE id = %s", (error, batch_id))
        else:
            # We preserve the draft for review (Option 2)
            cur.execute("UPDATE translation_batch SET status = 'review', raw_draft = %s WHERE id = %s", (draft_content, batch_id))
            
            # Also save to a physical file for user to Audit
            out_dir = f"drafts/vol_{vol}"
            os.makedirs(out_dir, exist_ok=True)
            with open(f"{out_dir}/{sutta_id}.md", "w", encoding="utf-8") as f:
                f.write(draft_content)
                
            print(f"Batch {batch_id} ready for review at {out_dir}/{sutta_id}.md")
            
    except Exception as e:
        cur.execute("UPDATE translation_batch SET status = 'error', error_log = %s WHERE id = %s", (str(e), batch_id))
        print(f"Error processing batch: {e}")
        
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    process_next_batch()
