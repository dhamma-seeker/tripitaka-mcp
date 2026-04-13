import urllib.request
import bs4
import time
import json
import os
import ssl

def parse_payutto():
    base_url = "https://tripitaka-online.blogspot.com/2016/08/bd{:03d}.html"
    results = []
    
    # Disable SSL context verification just in case
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("🚀 เริ่มลุยเก็บข้อมูลพจนานุกรม...")
    
    # 44 consonants + maybe some extras, let's loop up to 60 and stop on 404
    for i in range(1, 60):
        url = base_url.format(i)
        print(f"กำลังดึงข้อมูลจากหน้า: {url}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, context=ctx)
            html = response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if "404" in str(e):
                print(f"✅ ดึงข้อมูลเสร็จสิ้นแล้วที่หน้า {i-1}")
            else:
                print(f"❌ เจอข้อผิดพลาดที่หน้า {url}: {e}")
            break
            
        soup = bs4.BeautifulSoup(html, 'html.parser')
        container = soup.find('div', {'class': 'post-body'})
        if not container:
            print("ไม่พบตระกร้าข้อมูล (post-body) ข้ามหน้านี้")
            continue
            
        # Extract entries. Entries start with <b><span class="vcb">
        page_word_count = 0
        for b_tag in container.find_all('b'):
            span = b_tag.find('span', {'class': 'vcb'})
            if span:
                headword = span.text.strip()
                
                # Fetch sibling nodes until the next <b><span class="vcb">
                definitionParts = []
                curr = b_tag.next_sibling
                while curr:
                    if curr.name == 'b' and curr.find('span', {'class': 'vcb'}):
                        break
                        
                    if isinstance(curr, bs4.element.NavigableString):
                        text = curr.get_text().strip()
                        if text:
                            definitionParts.append(text)
                    elif curr.name == 'br':
                        definitionParts.append("\n")
                    elif curr.name in ['i', 'span', 'a']:
                        text = curr.get_text().strip()
                        if text:
                            definitionParts.append(text)
                    else:
                        text = curr.get_text().strip()
                        if text:
                            definitionParts.append(text)
                    curr = curr.next_sibling
                
                # Process definition
                raw_def = " ".join(definitionParts).replace(" \n ", "\n").replace("\n ", "\n").replace(" \n", "\n").strip()
                # Clean up multiple newlines
                import re
                clean_def = re.sub(r'\n{2,}', '\n', raw_def)
                
                if headword and clean_def:
                    results.append({
                        "word": headword,
                        "definition": clean_def,
                        "source": "payutto"
                    })
                    page_word_count += 1
                    
        print(f"  👉 ได้คำศัพท์มา {page_word_count} คำ")
        time.sleep(1) # Polite crawler policy
        
    print(f"🎉 เสร็จสมบูรณ์! ได้คำศัพท์ทั้งหมด {len(results)} คำ")
    
    # Save the output
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'payutto_dict.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"💾 บันทึกไฟล์เรียบร้อยที่: {out_path}")

if __name__ == '__main__':
    parse_payutto()
