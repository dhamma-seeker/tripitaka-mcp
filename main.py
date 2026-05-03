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
import re
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP

from db.connection import get_connection, release_connection
from db.schema import create_tables

load_dotenv()


# =============================================================================
# Language Coverage (feature flag)
# =============================================================================
# canonical = SuttaCentral bilara-data (Pāli + Sujato English).
# Thai/อื่น ๆ จะเปิดได้เมื่อ index ฉบับแปลพร้อม — ไม่งั้นปิดไว้ใน prod เพื่อ
# ป้องกัน user ได้ผลลัพธ์ครึ่ง ๆ กลาง ๆ. AI client ฝั่งผู้ใช้ควรแปล query
# เป็นบาลีโรมัน/อังกฤษก่อนเรียก search tools.
SUPPORTED_LANGUAGES = frozenset({"pali", "thai", "english"})


def _parse_enabled_languages() -> frozenset[str]:
    raw = os.getenv("TRIPITAKA_ENABLED_LANGUAGES", "pali,english")
    langs = {x.strip().lower() for x in raw.split(",") if x.strip()}
    if not langs:
        raise ValueError(
            "TRIPITAKA_ENABLED_LANGUAGES must enable at least one language"
        )
    invalid = langs - SUPPORTED_LANGUAGES
    if invalid:
        raise ValueError(
            f"TRIPITAKA_ENABLED_LANGUAGES has unknown values: {sorted(invalid)} "
            f"(supported: {sorted(SUPPORTED_LANGUAGES)})"
        )
    if "pali" not in langs:
        # Pāli เป็น canonical reference — ปิดไม่ได้
        raise ValueError(
            "TRIPITAKA_ENABLED_LANGUAGES must include 'pali' (canonical reference)"
        )
    return frozenset(langs)


ENABLED_LANGUAGES = _parse_enabled_languages()


# =============================================================================
# Initialize MCP Server
# =============================================================================
def _build_instructions() -> str:
    enabled_list = ", ".join(sorted(ENABLED_LANGUAGES))
    disabled = SUPPORTED_LANGUAGES - ENABLED_LANGUAGES
    coverage_note = (
        f"🌐 ภาษาที่เปิดใช้ในเซิร์ฟเวอร์นี้: {enabled_list}\n"
        if not disabled
        else (
            f"🌐 ภาษาที่เปิดใช้: {enabled_list} "
            f"(ปิดชั่วคราว: {', '.join(sorted(disabled))} — "
            f"ข้อมูลยังไม่พร้อมใช้งาน)\n"
            "💡 ถ้า user ถาม query ในภาษาที่ปิดอยู่ ให้ AI client "
            "**แปล query เป็นบาลีโรมัน (preferred) หรืออังกฤษ** "
            "ก่อนเรียก search tools — แล้วแปลผลลัพธ์กลับเป็นภาษาผู้ใช้.\n"
        )
    )
    return (
        "MCP Server สำหรับค้นหาและอ้างอิงเนื้อหาจากพระไตรปิฎก (Tipiṭaka). "
        "ใช้สำหรับค้นหาพระสูตร, อ้างอิงคำสอนพระพุทธเจ้า, "
        "และเปรียบเทียบคำแปลข้ามภาษา.\n\n"
        + coverage_note
        + "\n🔗 **Cross-reference URLs (สำคัญ — surface ในคำตอบเสมอ):**\n"
        "ทุก response มี field `cross_reference` ที่มี URL ไปยังต้นฉบับ:\n"
        "• `suttacentral` — Pāli canonical, deep-link ระดับ segment ได้\n"
        "  (`url`, `pali_url`, `english_url`, `segment_url`)\n"
        "• `tipitaka_84000` — ฉบับมหาจุฬาฯ ภาษาไทย (homepage + search hint)\n\n"
        "💡 **AI client เลือก URL ตามภาษาของ user:**\n"
        "- User คุยภาษาไทย → surface `tipitaka_84000.url` เป็นลิงก์หลัก "
        "(แนะนำให้ค้นด้วย Pāli title) + suttacentral เป็น secondary\n"
        "- User คุยภาษาอังกฤษ/อื่น → surface `suttacentral.english_url` "
        "เป็นลิงก์หลัก + segment_url เมื่ออ้างประโยคเฉพาะ\n"
        "- รวมลิงก์ใน response เป็น markdown clickable เสมอ — เพื่อ user "
        "verify ต้นฉบับได้ทันที (ลด hallucination)\n"
        "\n📚 แหล่งข้อมูล (Data Sources):\n"
        "• พระไตรปิฎกบาลี + คำแปลอังกฤษ: SuttaCentral bilara-data (CC0)\n"
        "• คำแปลไทย: พระธีรนันโท, พระอาจารย์ชยสาโร (CC0) / ฉบับ มจร., ฉบับหลวง\n"
        "• พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์: "
        "สมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต) — เผยแผ่เป็นธรรมทาน\n"
        "• ต้นฉบับ: https://www.watnyanaves.net, https://84000.org, "
        "https://suttacentral.net\n\n"
        "⚠️ ข้อมูลจัดทำเพื่อการศึกษาและเผยแผ่ธรรมเท่านั้น "
        "หากพบข้อผิดพลาดหรือต้องการอ้างอิงอย่างเป็นทางการ "
        "โปรดตรวจสอบกับตัวเล่มหนังสือฉบับพิมพ์ล่าสุด.\n\n"
        "🙏 โครงการนี้เผยแผ่เป็นธรรมทาน ห้ามใช้ในเชิงพาณิชย์."
    )


mcp = FastMCP("Tripitaka", instructions=_build_instructions())

# สร้างตารางตอน startup (ถ้ายังไม่มี)
# Prod ที่ใช้ readonly user ให้ข้ามด้วย TRIPITAKA_SKIP_MIGRATIONS=true
# เพราะ readonly role ไม่มีสิทธิ์ CREATE TABLE
if os.getenv("TRIPITAKA_SKIP_MIGRATIONS", "").lower() not in ("1", "true", "yes"):
    try:
        create_tables()
    except Exception as e:
        print(f"⚠️  create_tables skipped: {e}")


# =============================================================================
# Helper Functions
# =============================================================================

LANGUAGE_COLUMNS = {
    "pali": "text_pali",
    "thai": "text_thai",
    "english": "text_english",
}

# Attribution metadata สำหรับแต่ละ source ของพจนานุกรม
# แสดงในทุก response เพื่อให้เป็นไปตามเงื่อนไขของผู้เรียบเรียง
DICTIONARY_ATTRIBUTIONS = {
    "payutto": {
        "title": "พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์",
        "author": "สมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต)",
        "license": "ธรรมทาน (Dhamma Dāna) — ห้ามใช้เชิงพาณิชย์",
        "source_url": "https://www.watnyanaves.net",
        "note": "ควรตรวจสอบกับหนังสือฉบับพิมพ์ล่าสุดสำหรับการอ้างอิงทางการ",
    },
    "pts": {
        "title": "The Pali Text Society's Pali-English Dictionary",
        "author": "T. W. Rhys Davids & William Stede",
        "license": "Public Domain",
        "source_url": "https://www.palitextsociety.org",
    },
    "dppn": {
        "title": "Dictionary of Pali Proper Names",
        "author": "G. P. Malalasekera",
        "license": "Public Domain",
        "source_url": "https://www.palikanon.com/english/pali_names/dic_idx.html",
    },
    "dhammika": {
        "title": "A Buddhist Dictionary",
        "author": "Bhikkhu Dhammika",
        "license": "Creative Commons",
        "source_url": "https://www.bhantedhammika.net",
    },
}

PROJECT_NOTICE = (
    "โครงการนี้เผยแผ่เป็นธรรมทาน — "
    "โปรดใช้เพื่อการศึกษาเท่านั้น และไม่ใช้ในเชิงพาณิชย์"
)

# Whitelists สำหรับ validate input ที่จะถูกใช้ใน SQL / filter
# Search/display restricted to ENABLED_LANGUAGES — language ที่ปิดจะถูก reject
VALID_LANGUAGES_SEARCH = ENABLED_LANGUAGES
VALID_LANGUAGES_DISPLAY = ENABLED_LANGUAGES | {"all"}
VALID_PITAKAS = frozenset({"vinaya", "sutta", "abhidhamma"})
VALID_EDITIONS = frozenset({"dhiranandi", "jayasaro", "mbu", "royal"})
VALID_DICT_LANGUAGES = frozenset({"en", "thai", "th", "all"})

# language code mapping — translation table ใช้ ISO 2-letter code
TRANSLATION_LANG_CODES = {
    "pali": "pi",
    "thai": "th",
    "english": "en",
}
ENABLED_TRANSLATION_CODES = frozenset(
    TRANSLATION_LANG_CODES[lang] for lang in ENABLED_LANGUAGES
)

# sutta_id format เช่น "mn1", "dn22", "sn56.11", "an4.5.6", "dhp1-20", "tha-ap411", "mil3.1.1"
# sutta_id formats supported:
#   simple:        mn1, dn22, sn56.11, an4.5.6
#   range:         dhp1-20  (KN range groupings)
#   1 hyphen alpha: tha-ap1, thi-ap1
#   compound:      mil3.1.1
#   Vinaya:        pli-tv-bu-vb-pj1, pli-tv-bu-vb-as1-7, pli-tv-kd1, pli-tv-pvr1, pli-tv-bu-pm
# multiple `-[a-z]+` segments allowed (for SC's pli-tv-* convention).
# `\d*` (not `\d+`) so the digit-less "pli-tv-bu-pm" passes too.
SUTTA_ID_PATTERN = re.compile(r"^[a-z]{2,6}(-[a-z]+)*\d*(-\d+)?(\.\d+(-\d+)?){0,4}[a-z]?$")


class ValidationError(ValueError):
    """ข้อผิดพลาดจาก input validation — ใช้แยกจาก internal error"""


def _validate_choice(value: str | None, allowed: frozenset[str], field: str) -> str | None:
    """ตรวจว่า value อยู่ใน whitelist หรือไม่ — รับ None ได้ (optional filter)"""
    if value is None:
        return None
    if value not in allowed:
        raise ValidationError(
            f"invalid {field!r}: {value!r} (allowed: {sorted(allowed)})"
        )
    return value


def _validate_sutta_id(sutta_id: str) -> str:
    """ตรวจรูปแบบ sutta_id ป้องกัน injection — lowercase, alphanumeric + dots"""
    if not isinstance(sutta_id, str) or not SUTTA_ID_PATTERN.match(sutta_id):
        raise ValidationError(
            f"invalid sutta_id format: {sutta_id!r} "
            "(expected e.g. 'mn1', 'dn22', 'sn56.11')"
        )
    return sutta_id


def _build_context(row: tuple, columns: list[str]) -> dict[str, Any]:
    """แปลง database row เป็น dict ตาม columns ที่กำหนด"""
    return dict(zip(columns, row))


# Mapping ระหว่างชื่อ column ใน result กับ ENABLED_LANGUAGES check
_TEXT_COLUMN_TO_LANG = {
    "text_pali": "pali",
    "text_thai": "thai",
    "text_english": "english",
}


# =============================================================================
# Cross-reference URL builders
# =============================================================================
# AI client ใช้ URL เหล่านี้แสดงเป็น clickable link ในคำตอบ user — เพื่อให้
# verify ต้นฉบับได้ทันที (groundability + reduce hallucination).
# Default = SuttaCentral (Pāli canonical, deep-link ระดับ segment ได้)
# 84000.org = ฉบับมหาจุฬาฯ ภาษาไทย — ใช้ homepage เพราะ deep-link
# mapping (SC ID ↔ B/A) ยังไม่มี (ดู PROGRESS.md TODO)

SUTTACENTRAL_BASE = "https://suttacentral.net"
TIPITAKA_84000_BASE = "https://84000.org/tipitaka/"

# Heuristic: nikāya prefix → 84000 volume number (มหาจุฬาฯ 45-volume edition)
# - Vinaya = vols 1-8
# - Sutta:  DN = 9-11, MN = 12-14, SN = 15-19, AN = 20-24, KN = 25-33
# - Abhidhamma = vols 34-45
# ค่านี้คือ "starting volume" ของแต่ละนิกาย; deep-link sutta-level ต้องการ
# A= (paragraph offset) ที่เรายังไม่มี mapping → ให้ user landing ที่หน้าเล่มแรก
# แล้วใช้ search_hint หา sutta เอง
_NIKAYA_TO_84000_VOL = {
    "dn": 9,
    "mn": 12,
    "sn": 15,
    "an": 20,
    # KN sub-books — เริ่มที่ vol 25
    "kn-kp": 25,
    "kn-dhp": 25,
    "kn-ud": 25,
    "kn-iti": 25,
    "kn-snp": 25,
    "kn-vv": 26,
    "kn-pv": 26,
    "kn-thag": 26,
    "kn-thig": 26,
    "kn-ja": 27,
    "kn-mnd": 29,
    "kn-cnd": 30,
    "kn-ps": 31,
    "kn-bv": 33,
    "kn-cp": 33,
    # KN sub-books แบบ short prefix (sutta_id ใช้ short เช่น "dhp1-20", "snp1.8")
    "dhp": 25,
    "ud": 25,
    "iti": 25,
    "snp": 25,
    "vv": 26,
    "pv": 26,
    "thag": 26,
    "thig": 26,
    "ja": 27,
    "mnd": 29,
    "cnd": 30,
    "ps": 31,
    "bv": 33,
    "cp": 33,
    # Vinaya
    "vin": 1,
    "pli-tv": 1,
    # Abhidhamma
    "ds": 34,
    "vb": 35,
    "dt": 36,
    "pp": 36,
    "kv": 37,
    "ym": 38,
    "pt": 40,
    # Apadāna / Buddhavaṃsa subset (ไม่ map ตรงๆ ใน Thai canon — fallback to 33)
    "tha-ap": 32,
    "thi-ap": 32,
}


def _parse_nikaya_prefix(sutta_id: str) -> str | None:
    """ดึง nikāya prefix จาก sutta_id เพื่อหา 84000 volume.

    ตัวอย่าง: mn1 → "mn", dhp1-20 → "dhp", sn56.11 → "sn", tha-ap1 → "tha-ap",
    mil3.1.1 → "mil" (ไม่อยู่ใน mapping → return None → fallback)
    """
    sid = sutta_id.lower()
    # ลอง match prefix ยาวก่อน (kn-thag ก่อน thag, pli-tv ก่อน pli)
    for prefix in sorted(_NIKAYA_TO_84000_VOL.keys(), key=len, reverse=True):
        if sid.startswith(prefix):
            # ตรวจว่าตัวถัดไปเป็น digit หรือ '-' (กัน match บางส่วนเช่น "dn" match "dn..." แต่ไม่ match "dnnn")
            rest = sid[len(prefix):]
            if rest and (rest[0].isdigit() or rest[0] == "-" or rest[0] == "."):
                return prefix
    return None


def _suttacentral_urls(sutta_id: str, segment_id: str | None = None) -> dict[str, str]:
    """สร้าง URL set ของ SuttaCentral สำหรับ cross-reference.

    Returns:
        - url: หน้าหลักของสูตร (SC default — มี language switcher)
        - pali_url: ฉบับบาลี Mahāsaṅgīti
        - english_url: คำแปลอังกฤษโดย Bhikkhu Sujato
        - segment_url: deep-link ไปยัง segment เฉพาะ (ถ้าส่ง segment_id)
    """
    base = f"{SUTTACENTRAL_BASE}/{sutta_id}"
    urls = {
        "url": base,
        "pali_url": f"{base}/pli/ms",
        "english_url": f"{base}/en/sujato",
    }
    if segment_id:
        urls["segment_url"] = f"{base}/pli/ms#{segment_id}"
    return urls


def _tipitaka_84000_urls(sutta_id: str) -> dict[str, str]:
    """สร้าง URL set ของ 84000.org (ฉบับมหาจุฬาฯ ภาษาไทย).

    Strategy: heuristic mapping จาก nikāya prefix → starting volume number.
    user landing ที่หน้าแรกของเล่ม (ไม่ใช่ sutta-level) แล้วใช้ search_hint
    หา sutta ในเล่ม. เพิ่ม Google site-search URL เป็น fallback ที่แม่นกว่า

    Returns:
        - url: 84000 volume URL ที่ใกล้สูตรนี้สุด (best-effort)
        - search_url: Google site-search ของ 84000 ด้วย sutta_id (precise)
        - note: hint สำหรับ AI client
    """
    nikaya_prefix = _parse_nikaya_prefix(sutta_id)
    volume = _NIKAYA_TO_84000_VOL.get(nikaya_prefix or "")

    google_search = (
        f"https://www.google.com/search?q=site%3A84000.org+%22{sutta_id}%22"
    )

    if volume:
        volume_url = f"https://84000.org/tipitaka/read/r.php?B={volume}&A=1"
        note = (
            f"เปิดที่หน้าแรกของเล่ม {volume} (ฉบับ มจร 45 เล่ม) — "
            "เลื่อน/ค้นชื่อสูตรในเล่มเอง. ใช้ search_url เพื่อค้นใน 84000 ตรง"
        )
        return {
            "url": volume_url,
            "search_url": google_search,
            "note": note,
        }
    # Fallback: paracanonical (Mil, Ne, Pe) หรือ id ที่ไม่อยู่ใน mapping
    return {
        "url": TIPITAKA_84000_BASE,
        "search_url": google_search,
        "note": (
            "Sutta นี้อยู่นอก 45 เล่มหลัก (paracanonical) — "
            "ใช้ search_url เพื่อหาในไซต์"
        ),
    }


def _cross_reference_urls(sutta_id: str, segment_id: str | None = None) -> dict[str, Any]:
    """รวม URL จากทุกแหล่งสำหรับ AI client surface ใน response.

    Returns dict with:
        - suttacentral: deep-link set (canonical, default)
        - tipitaka_84000: ฉบับมหาจุฬาฯ ไทย — volume page + Google search
          fallback (deep-link mapping เป็น heuristic, ใช้ search_url ถ้าไม่ตรง)
    """
    return {
        "suttacentral": _suttacentral_urls(sutta_id, segment_id),
        "tipitaka_84000": _tipitaka_84000_urls(sutta_id),
    }


def _strip_disabled_text_fields(result: dict[str, Any]) -> dict[str, Any]:
    """ลบ field text_<lang> ที่ภาษาถูกปิดอยู่ ออกจาก result dict.

    ใช้กับผลลัพธ์ search/lookup ที่อาจมี text_thai/text_english/text_pali —
    เพื่อให้ output สอดคล้องกับ ENABLED_LANGUAGES.
    """
    return {
        k: v
        for k, v in result.items()
        if k not in _TEXT_COLUMN_TO_LANG
        or _TEXT_COLUMN_TO_LANG[k] in ENABLED_LANGUAGES
    }


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

    ค้นหาแบบ trigram (word similarity) บนภาษาที่เปิดใช้งานในเซิร์ฟเวอร์.
    สามารถกรองผลลัพธ์ตามปิฎกและฉบับแปลได้.

    💡 **คำแนะนำสำหรับ AI client:**
    Canonical reference ของระบบคือบาลีโรมัน (จาก SuttaCentral). ถ้า user
    ถามเป็นภาษาที่ปิด (หรือไม่อยู่ใน supported set) ให้แปล keyword เป็น
    บาลีโรมัน (preferred) หรืออังกฤษก่อนเรียก tool นี้ — เช่น
    "ทุกข์" → "dukkha", "อานาปานสติ" → "ānāpānassati".
    ดูภาษาที่ใช้ได้ใน server instructions ด้านบน.

    🔍 **เลือก tool ค้นหาให้เหมาะกับงาน:**
    - **หาคำเป๊ะ (term lookup)** — เช่น "appearances of `ānāpānassati`":
      ใช้ tool นี้ ดี เพราะ trigram match ตรงคำสุด
    - **หา "เนื้อหาเรื่อง X" (concept search)** — เช่น "discourses about
      mindfulness of breathing": **ใช้ `search_hybrid` แทน** เพราะ
      canonical Pāli มีลักษณะที่ keyword search หา concept ได้ไม่ครบ:
        • คำสำคัญในชื่อหมวด (`Ānāpānapabba`) ไม่ได้อยู่ในเนื้อหาคำสอน
          ที่ใช้ verb อื่น (`assasati`, `passasati`, `dīghaṁ`, `rassaṁ`) —
          เช่น DN22 Ānāpānapabba มี 16 segments แต่คำว่า `ānāpāna`
          ปรากฏแค่ 2 ที่ (header + footer) — เนื้อหาจริงจะหาไม่เจอ
        • Stock phrases (เช่น `So satova assasati, satova passasati`)
          ปรากฏซ้ำใน 10+ สูตร — keyword จะ rank ผลกว้าง ไม่ชี้สูตรเฉพาะ
    - **ค้นทั่วไปจาก keyword เดียว** — ใช้ `limit≥30` แล้วกรองเอง
      หรือเรียกหลายคำที่เกี่ยวข้อง (root verb + noun + compound)

    Args:
        keyword: คำที่ต้องการค้นหา
        language: ภาษาที่ค้นหา — ต้องอยู่ใน ENABLED_LANGUAGES ของเซิร์ฟเวอร์
                  (default: "pali"). ภาษาที่ปิดอยู่จะ return error.
        edition: ฉบับแปลภาษาไทย — "dhiranandi", "jayasaro", "mbu", "royal" หรือ None
                  (ใช้เฉพาะเมื่อ language="thai" และ Thai เปิดอยู่)
        pitaka: กรองตามปิฎก — "vinaya", "sutta", "abhidhamma" หรือ None (ค้นทั้งหมด)
                ✅ v1.1+: ทั้ง 3 ปิฎกครบ (Sutta + Vinaya + Abhidhamma) เทียบเท่า
                SuttaCentral bilara — ดู list_structure ตัวเลขสด
        limit: จำนวนผลลัพธ์สูงสุด (default: 10, max: 50)
    """
    try:
        language = _validate_choice(language, VALID_LANGUAGES_SEARCH, "language")
        edition = _validate_choice(edition, VALID_EDITIONS, "edition")
        pitaka = _validate_choice(pitaka, VALID_PITAKAS, "pitaka")
    except ValidationError as e:
        return [{"error": str(e)}]

    limit = min(max(1, limit), 50)
    conn = get_connection()
    try:
        cur = conn.cursor()
        params = {"kw": keyword, "limit": limit}

        if language == "thai":
            # ค้นหาภาษาไทยจากตาราง translation
            query = """
                SELECT
                    seg.segment_id,
                    sec.sutta_id,
                    seg.text_pali,
                    t.text AS text_thai,
                    seg.text_english,
                    t.edition,
                    similarity(t.text, %(kw)s) AS similarity,
                    word_similarity(%(kw)s, t.text) AS word_similarity
                FROM translation t
                JOIN segment seg ON t.segment_id = seg.id
                JOIN section sec ON seg.section_id = sec.id
                JOIN book b ON sec.book_id = b.id
                JOIN nikaya n ON b.nikaya_id = n.id
                JOIN pitaka p ON n.pitaka_id = p.id
                WHERE t.language = 'th'
                  AND %(kw)s <%% t.text
            """
            if edition:
                query += " AND t.edition = %(edition)s"
                params["edition"] = edition
            if pitaka:
                query += " AND p.code = %(pitaka)s"
                params["pitaka"] = pitaka

            query += " ORDER BY word_similarity DESC, similarity DESC LIMIT %(limit)s"
            cur.execute(query, params)
            cols = [desc[0] for desc in cur.description]
            results = [dict(zip(cols, row)) for row in cur.fetchall()]

        else:
            # ค้นหาภาษาอื่นจากตาราง segment — language ผ่าน whitelist validation แล้ว
            text_col = LANGUAGE_COLUMNS[language]
            query = f"""
                SELECT
                    seg.segment_id,
                    sec.sutta_id,
                    seg.text_pali,
                    seg.text_thai,
                    seg.text_english,
                    similarity(seg.{text_col}, %(kw)s) AS similarity,
                    word_similarity(%(kw)s, seg.{text_col}) AS word_similarity
                FROM segment seg
                JOIN section sec ON seg.section_id = sec.id
                JOIN book b ON sec.book_id = b.id
                JOIN nikaya n ON b.nikaya_id = n.id
                JOIN pitaka p ON n.pitaka_id = p.id
                WHERE %(kw)s <%% seg.{text_col}
            """
            if pitaka:
                query += " AND p.code = %(pitaka)s"
                params["pitaka"] = pitaka

            query += " ORDER BY word_similarity DESC, similarity DESC LIMIT %(limit)s"
            cur.execute(query, params)
            cols = [desc[0] for desc in cur.description]
            results = [dict(zip(cols, row)) for row in cur.fetchall()]

        if not results:
            hint = f" (edition: {edition})" if edition else ""
            return [{"message": f"ไม่พบผลลัพธ์สำหรับ '{keyword}' ในภาษา {language}{hint}"}]

        return [
            _strip_disabled_text_fields({
                **r,
                "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
            })
            for r in results
        ]

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
    """ดึงเนื้อหาสูตร/กัณฑ์ตาม ID — return เนื้อหาเต็มทุก segment

    ใช้รหัสมาตรฐาน SuttaCentral เช่น:
    - `mn1` = มัชฌิมนิกาย สูตรที่ 1 (Mūlapariyāyasutta — มูลปริยายสูตร, 334 segments)
    - `dn22` = ทีฆนิกาย สูตรที่ 22 (Mahāsatipaṭṭhānasutta — มหาสติปัฏฐาน, 454 segments)
    - `dn16` = ทีฆนิกาย สูตรที่ 16 (Mahāparinibbānasutta — สูตรยาวที่สุด 1,664 segments)
    - `sn56.11` = สังยุตต์ 56.11 (Dhammacakkappavattana — ธัมมจักกัปปวัตตนะ)
    - `mn62` = มัชฌิมนิกาย 62 (Mahārāhulovāda — สอนพระราหุล)
    - `dhp1-20` = Dhammapada verses 1-20 (KN ใช้ range format)
    - `mil3.1.1` = Milindapañha 3.1.1 (paracanonical, 3-4 level id)

    💡 **คำแนะนำสำหรับ AI client:**
    - **Quote text_pali / text_english โดยตรงจาก segment** — อย่าดึงจาก
      training memory. ระบบ verify ได้, AI หลายครั้งจำผิดได้
    - Segment สั้นๆ ลงท้ายด้วย `:0.1` หรือ `:0.2` มักเป็น **header** (ชื่อ
      นิกาย/สูตร) ไม่ใช่เนื้อหา teaching จริง — เริ่ม content จาก `:1.1`
    - Segment ที่ลงท้ายด้วย "...niṭṭhitaṁ" (เช่น `mn1:194.10` =
      "Mūlapariyāyasuttaṁ niṭṐhitaṁ paṭhamaṁ") เป็น **colophon** ปิดสูตร
    - Segments ที่มี `…pe…` (peyyāla = เปยยาล) คือ **abbreviated repetition**
      ไม่ใช่ข้อมูลขาดหาย — ตำราบาลีย่อด้วยวิธีนี้
    - response มี `cross_reference` field — render เป็น markdown clickable
      ใน reply เพื่อให้ user verify ต้นฉบับได้

    ✅ **Coverage (v1.1+):** ครบ 3 ปิฎก เทียบเท่า SuttaCentral bilara-data
    - Sutta Piṭaka (DN/MN/SN/AN/KN): ✅ ครบ Pāli + Sujato EN (5,791 sections)
    - Vinaya Piṭaka: ✅ ครบ Pāli + Brahmali EN — ใช้ SC codes เช่น
      `pli-tv-bu-vb-pj1` (ปาราชิก ๑), `pli-tv-bi-vb-pj1` (ภิกขุนี),
      `pli-tv-kd1` (มหาวรรค), `pli-tv-pvr10` (ปริวาร), `pli-tv-bu-pm`
      (ภิกขุปาฏิโมกข์)
    - Abhidhamma Piṭaka: ✅ ครบ 7 books (ds, vb, dt, pp, kv, ya, patthana)
      — Pāli only (bilara ไม่มี EN ทุก translator)

    Args:
        sutta_id: รหัสสูตร เช่น "mn1", "dn22", "sn56.11", "dhp1-20"
        language: ภาษาที่ต้องการ — "pali", "thai", "english", หรือ "all"
                  (default: "pali"). Thai ปิดอยู่ใน server ปัจจุบัน → return null
        edition: ฉบับแปลภาษาไทย — "dhiranandi", "jayasaro", "mbu", "royal"
                 หรือ None. ถ้าไม่ระบุ จะใช้ text_thai จาก bilara-data
                 ⚠️ ปัจจุบัน DB ไม่มีฉบับแปลไทย → ทุกค่ามักเป็น null

    Returns:
        ข้อมูลสูตรประกอบด้วย:
        - sutta_id, title{pali,thai,english}, nikaya, pitaka, edition
        - segment_count, segments[] (เรียงตาม id, ครบทุก segment)
        - cross_reference: SuttaCentral URLs (sutta + Pāli + English) +
          84000 link สำหรับ Thai user routing
    """
    try:
        sutta_id = _validate_sutta_id(sutta_id)
        language = _validate_choice(language, VALID_LANGUAGES_DISPLAY, "language")
        edition = _validate_choice(edition, VALID_EDITIONS, "edition")
    except ValidationError as e:
        return {"error": str(e)}

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
            # ถ้าไม่ระบุ edition ให้พยายามดึงจาก segment.text_thai
            # และ fallback ไปยัง translation table ฉบับใดก็ได้ที่มีบทแปลไทย
            cur.execute(
                """
                SELECT 
                    seg.segment_id, 
                    seg.text_pali, 
                    COALESCE(
                        seg.text_thai, 
                        (SELECT text FROM translation WHERE segment_id = seg.id AND language = 'th' LIMIT 1)
                    ) AS text_thai, 
                    seg.text_english
                FROM segment seg
                WHERE seg.section_id = %s
                ORDER BY seg.id
                """,
                (section_id,),
            )
        segment_rows = cur.fetchall()

        # สร้าง segments ตามภาษาที่ต้องการ
        # ภาษาที่ปิดใน ENABLED_LANGUAGES จะไม่ถูก include แม้ language="all"
        # ขณะเดียวกัน เก็บ title fallback จาก segment :0.2 (SC convention —
        # section.title_* ใน DB หลายแถวเป็น null, แต่ segment :0.2 มักมี
        # ชื่อสูตรครบทุกภาษา เช่น "Mūlapariyāyasutta" / "The Root of All Things")
        segments = []
        title_from_segment: dict[str, str | None] = {
            "pali": None, "thai": None, "english": None,
        }
        for seg_row in segment_rows:
            seg = {"segment_id": seg_row[0]}
            if "pali" in ENABLED_LANGUAGES and language in ("pali", "all"):
                seg["text_pali"] = seg_row[1]
            if "thai" in ENABLED_LANGUAGES and language in ("thai", "all"):
                seg["text_thai"] = seg_row[2]
            if "english" in ENABLED_LANGUAGES and language in ("english", "all"):
                seg["text_english"] = seg_row[3]
            segments.append(seg)
            if seg_row[0].endswith(":0.2") and title_from_segment["pali"] is None:
                title_from_segment = {
                    "pali": seg_row[1],
                    "thai": seg_row[2],
                    "english": seg_row[3],
                }

        # title: prefer section.title_* (curated), fallback ไป segment :0.2
        # respect ENABLED_LANGUAGES — ภาษาที่ปิดอยู่ return null
        def _title_for(lang: str, db_title: str | None) -> str | None:
            if lang not in ENABLED_LANGUAGES:
                return None
            return db_title or title_from_segment[lang]

        return {
            "sutta_id": section_row[1],
            "title": {
                "pali": _title_for("pali", section_row[2]),
                "thai": _title_for("thai", section_row[3]),
                "english": _title_for("english", section_row[4]),
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
            "cross_reference": _cross_reference_urls(section_row[1]),
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

    ใช้ vector similarity search (cosine distance) บน `text_pali` ที่ embed
    ด้วย multilingual MiniLM model.

    🤔 **ส่วนใหญ่คุณควรใช้ `search_hybrid` แทน** — มันรวม semantic นี้กับ
    keyword search แล้ว ranking ดีกว่า. ใช้ tool นี้เฉพาะเมื่อ:
    - ต้องการ pure semantic (ไม่ต้องการ keyword influence)
    - อยาก tune `threshold` ละเอียด (hybrid ใช้ RRF ปรับยาก)
    - debug ดูว่า semantic จับอะไรได้บ้างเทียบกับ keyword

    ⚠️ ข้อจำกัดที่ทราบ:
    - Index = บาลีเท่านั้น (English/Thai ใช้ได้แต่ผ่าน multilingual embedding
      ที่ไม่ได้ tune บน Pāli)
    - English query มัก embed ดีกว่าไทย (model tune EN เป็นหลัก)
    - คำเฉพาะตัว (`appamāda`, `dukkha`) ที่ค้นแบบ exact ดีกว่า → ใช้
      `search_by_keyword`
    - Stock phrases บาลีปรากฏในหลายสูตร → similarity score กระจัดกระจาย,
      อ่าน top 10 อย่ายึดแค่ rank 1

    Args:
        query: ข้อความ (อังกฤษให้ผลดีสุด, รองมาเป็นบาลี, ไทยอ่อน)
        language: ภาษา output — "pali", "thai", "english", หรือ "all"
                  (Thai disabled → null)
        limit: จำนวนผลลัพธ์สูงสุด (default: 5, max: 20)
        threshold: cosine distance สูงสุด (น้อย=ตรงเผง). default 0.7;
                   ลดเป็น 0.5 ถ้าอยากเข้มงวด, เพิ่มเป็น 0.9 ถ้าอยากกว้าง

    Returns:
        list ผลลัพธ์เรียงตาม distance (น้อยไปมาก) แต่ละรายการมี:
        - segment_id, sutta_id, text_pali/text_english (ตาม language flag),
          distance, cross_reference URLs
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
                COALESCE(
                    seg.text_thai, 
                    (SELECT text FROM translation WHERE segment_id = seg.id AND language = 'th' LIMIT 1)
                ) AS text_thai,
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

        return [
            _strip_disabled_text_fields({
                **r,
                "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
            })
            for r in results
        ]

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
    การค้นหาคำตรงๆ มารวมกับผลลัพธ์จากการค้นหาความหมาย —
    **เป็น tool ที่แนะนำสำหรับ "หาเนื้อหาเรื่อง X"** เพราะ semantic ช่วย
    จับสูตรที่พูดถึง concept เดียวกันแม้ใช้คำต่างกัน (เช่น คำสอน
    อานาปานสติบางสูตรใช้ `assasati/passasati/dīghaṁ` แทน `ānāpānassati`).

    💡 **คำแนะนำสำหรับ AI client:**
    - Query ภาษาอังกฤษมักได้ผลดี (เช่น `mindfulness of breathing`)
      เพราะ embedding model เป็น multilingual แต่ tuned สำหรับ EN เป็นหลัก
    - Stop word ภาษาไทยอ่อน — ถ้า query ไทยไม่ได้ผลดี ให้ AI client
      แปลเป็นบาลี/อังกฤษก่อน (ดู server instructions)
    - default `limit=5` มักน้อยเกินสำหรับ topic survey — ถ้าต้องการ
      coverage ดี ใช้ `limit=15-20` (max 20)
    - Ranking ตาม similarity ไม่ใช่ canonical importance — สูตรหลัก
      (locus classicus) เช่น MN118, DN22 อาจ rank ต่ำกว่าสูตรเล็ก
      ถ้าสูตรเล็กมีคำเป๊ะกว่า. ใช้ผลลัพธ์เป็น "starting point"
      แล้วต่อด้วย `get_sutta` สำหรับสูตรเฉพาะที่เป็น canonical reference

    Args:
        query: ข้อความ (ภาษาไทย, บาลี หรืออังกฤษ — อังกฤษให้ผลดีสุด)
        language: ภาษาที่ต้องการให้แสดงในผลลัพธ์ ("pali", "thai", "english", "all")
        limit: จำนวนข้อความที่ต้องการค้นพบ (default 5, max 20)

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
        # Tokenize query: multi-word phrases rarely appear verbatim in any column,
        # so split and OR-match each token across text columns + translation table.
        tokens = [t for t in re.split(r"[\s\-]+", query.strip()) if len(t) >= 3]
        if not tokens:
            tokens = [query.strip()] if query.strip() else []

        keyword_ranks: dict[int, int] = {}
        if tokens:
            # สร้าง ILIKE conditions เฉพาะคอลัมน์ภาษาที่เปิดใช้งาน
            enabled_cols = [
                LANGUAGE_COLUMNS[lang]
                for lang in ("pali", "thai", "english")
                if lang in ENABLED_LANGUAGES
            ]
            per_token_seg = " OR ".join(f"{c} ILIKE %s" for c in enabled_cols)
            seg_conds = " OR ".join([f"({per_token_seg})"] * len(tokens))
            seg_params: list[str] = []
            for t in tokens:
                seg_params.extend([f"%{t}%"] * len(enabled_cols))

            sql = f"SELECT id as seg_id FROM segment WHERE {seg_conds}"

            # union กับ translation table เฉพาะเมื่อ Thai เปิดอยู่
            # (translation table มีแค่ภาษาไทย)
            if "thai" in ENABLED_LANGUAGES:
                trans_conds = " OR ".join(["text ILIKE %s"] * len(tokens))
                trans_params = [f"%{t}%" for t in tokens]
                sql = (
                    f"SELECT seg_id FROM ("
                    f"  {sql}"
                    f"  UNION"
                    f"  SELECT segment_id as seg_id FROM translation"
                    f"  WHERE language = 'th' AND ({trans_conds})"
                    f") AS combined_search LIMIT 50"
                )
                params = tuple(seg_params + trans_params)
            else:
                sql = f"SELECT seg_id FROM ({sql}) AS combined_search LIMIT 50"
                params = tuple(seg_params)

            cur.execute(sql, params)
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
                COALESCE(
                    seg.text_thai, 
                    (SELECT text FROM translation WHERE segment_id = seg.id AND language = 'th' LIMIT 1)
                ) AS text_thai,
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
                ctx = _build_context(context_row, columns)
                ctx["cross_reference"] = _cross_reference_urls(ctx["sutta_id"], ctx["segment_id"])
                results.append(_strip_disabled_text_fields(ctx))

        return results

    except Exception as e:
        return [{"error": f"เกิดข้อผิดพลาดในการค้นหา hybrid: {str(e)}"}]
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def list_structure() -> dict[str, Any]:
    """แสดงโครงสร้างพระไตรปิฎกทั้ง 3 ปิฎก พร้อมสถิติ coverage

    💡 **ใช้ tool นี้เมื่อ:**
    - User ถามภาพรวมพระไตรปิฎก (มีอะไรบ้าง / นิกายอะไร)
    - ตรวจ coverage ก่อนสัญญาว่าจะค้นได้ — ดู segment_count > 0 เป็นตัว
      ตัดสินว่า sub-collection นั้นโหลดแล้ว
    - Verify scope สำหรับการ compile artifact

    📊 **State ปัจจุบัน v1.1+ (เทียบเท่า SuttaCentral bilara-data):**
    - **Sutta Piṭaka** ครบ: DN 37, MN 155, SN 1,829, AN 1,419, KN 2,351 sections
      (~284,702 segments รวม) — Pāli + Sujato EN
    - **Vinaya Piṭaka** ครบ: Bhikkhu Vibhaṅga 222, Bhikkhunī Vibhaṅga 127,
      Khandhaka 22, Parivāra 51 + Pātimokkha 2 (~71,557 segs) — Pāli + Brahmali EN
    - **Abhidhamma Piṭaka** ครบ: 7 books (ds, vb, dt, pp, kv, ya, patthana)
      ~88,414 segs — Pāli only (bilara ไม่มี EN ทุก translator)
    - **รวม ~444,673 segments** ใน DB

    ⚠️ **Quirks ที่ยังอยู่:**
    - Schema มี duplicate codes legacy + SC modern ใช้ co-exist:
      - Vinaya: `vin-v/vin-m/vin-c/vin-p` (legacy, segment_count = 0) คู่กับ
        `pli-tv-bu-vb/pli-tv-bi-vb/pli-tv-kd/pli-tv-pvr` (active, มี segments)
      - Abhidhamma: `ym/pt` (legacy = 0) คู่กับ `ya/patthana` (active)
    - **เลือก code ที่ segment_count > 0 ตอนใช้งาน** — ตัวอื่นเป็น metadata
      placeholder จาก migration เก่า

    🌐 **ภาษา:** ส่งกลับ Pāli + Thai + English labels เสมอ (metadata ไม่ใช่
    segment text); text content ตามภาษาที่ ENABLED_LANGUAGES บอก. ตอนนี้
    ฉบับแปลไทยใน DB ยังไม่มี — Thai user ใช้ cross_reference 84000.org เพิ่ม

    Returns:
        โครงสร้างแบบ hierarchical:
        - pitakas{vinaya/sutta/abhidhamma} → nikayas[]
        - แต่ละ nikaya: code, name (3 ภาษา), sutta_count, segment_count
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
    """สร้างข้อมูลอ้างอิง (citation) ที่ถูกต้องสำหรับสูตร

    💡 **ใช้ tool นี้เมื่อ:**
    - User ขอ citation สำหรับงานวิชาการ/บทความ/อ้างอิง
    - ต้องการรู้ตำแหน่งในพระไตรปิฎก (ปิฎก/นิกาย) ของสูตร
    - ต้องการ formatted citation string พร้อมใช้

    🔗 vs `get_sutta`: tool นี้ return เฉพาะ metadata + citation ไม่มี segments;
    ใช้คู่กับ `get_sutta` เมื่ออยากได้ทั้งเนื้อหา + citation

    Args:
        sutta_id: รหัสสูตร เช่น "mn1", "dn22", "sn56.11"

    Returns:
        - sutta_id, title{pali,thai,english}
        - location: nikaya + pitaka (3 ภาษา)
        - segment_count: ขนาดสูตร (segments)
        - citation_format: รูปแบบ ready-to-use เช่น "The Root of All Things
          (Mūlapariyāyasutta, MN1), Middle Discourses"
        - cross_reference: SuttaCentral + 84000 URLs สำหรับลิงก์ใน citation
    """
    try:
        sutta_id = _validate_sutta_id(sutta_id)
    except ValidationError as e:
        return {"error": str(e)}

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

        # title fallback จาก segment :0.2 (เช่นเดียวกับ get_sutta) — เพราะ
        # section.title_* ใน DB หลายแถวเป็น null. หาตัวแรกที่ลงท้าย ":0.2"
        # ใน section นี้
        title_pali_fb = title_thai_fb = title_english_fb = None
        cur.execute(
            """
            SELECT text_pali, text_thai, text_english
            FROM segment
            WHERE section_id = (SELECT id FROM section WHERE sutta_id = %s)
              AND segment_id LIKE %s
            ORDER BY id
            LIMIT 1
            """,
            (sutta_id, "%:0.2"),
        )
        fb_row = cur.fetchone()
        if fb_row:
            title_pali_fb, title_thai_fb, title_english_fb = fb_row

        title_pali = row[1] or title_pali_fb or sutta_id
        title_thai = row[2] or title_thai_fb
        title_english = row[3] or title_english_fb or ""
        nikaya_english = row[6] or ""
        nikaya_code = row[7] or ""

        # สร้างรูปแบบการอ้างอิง
        citation = f"{title_pali} ({sutta_id.upper()}), {nikaya_english}"
        if title_english:
            citation = f"{title_english} ({title_pali}, {sutta_id.upper()}), {nikaya_english}"

        def _title_for(lang: str, db: str | None, fb: str | None) -> str | None:
            if lang not in ENABLED_LANGUAGES:
                return None
            return db or fb

        return {
            "sutta_id": row[0],
            "title": {
                "pali": _title_for("pali", row[1], title_pali_fb),
                "thai": _title_for("thai", row[2], title_thai_fb),
                "english": _title_for("english", row[3], title_english_fb),
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
            "cross_reference": _cross_reference_urls(sutta_id),
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
    """แสดงรายการฉบับแปลที่มีในระบบ พร้อมสถิติ coverage

    💡 **ใช้ tool นี้เมื่อ:**
    - ก่อนเรียก `compare_translations` หรือ `get_sutta(edition=...)` —
      เพื่อรู้ว่าใช้ค่า edition อะไรได้บ้างและฉบับไหนคุ้มเทียบ
    - User ถามว่ามีฉบับแปลใดบ้างใน DB

    🔍 **กรอง:** Tool นี้ filter ตาม `TRIPITAKA_ENABLED_LANGUAGES` ของเซิร์ฟเวอร์
    — Thai disabled → return empty list. ทำงานเฉพาะภาษาที่เปิดอยู่

    ⚠️ **State ปัจจุบัน:** DB ส่วนใหญ่มีแต่ Pāli (default จาก SuttaCentral
    bilara) + English (Sujato). Thai editions (`dhiranandi`, `jayasaro`,
    `mbu`, `royal`) ยังไม่ได้ index — return empty จนกว่าจะ load

    Returns:
        list ของ edition object แต่ละตัวมี:
        - edition: รหัสฉบับ เช่น "sujato", "dhiranandi", "mbu"
        - translator: ชื่อผู้แปล
        - language: รหัสภาษา ISO ("pi", "en", "th")
        - segment_count: จำนวน segments ที่มีคำแปลใน edition นี้
        - sutta_count: จำนวนสูตรที่มีคำแปล
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                t.edition,
                t.translator,
                t.language,
                COUNT(t.id) AS segment_count,
                COUNT(DISTINCT sec.sutta_id) AS sutta_count
            FROM translation t
            JOIN segment seg ON t.segment_id = seg.id
            JOIN section sec ON seg.section_id = sec.id
            WHERE t.language = ANY(%s)
            GROUP BY t.edition, t.translator, t.language
            ORDER BY t.language, t.edition
            """,
            (list(ENABLED_TRANSLATION_CODES),),
        )
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

    💡 **ใช้ tool นี้เมื่อ:**
    - User ถามความหมาย/การแปลของบรรทัดเดียวจากบาลี ที่อยากเทียบหลายผู้แปล
    - ตรวจสอบว่าผู้แปลแต่ละคนตีความต่างกันยังไง (เช่น คำเทคนิค `dukkha`,
      `anattā`, `nibbāna` มี nuance ในการแปลต่างกัน)
    - งานวิชาการที่ต้อง quote multiple translations

    🔍 **vs `get_sutta`:** tool นี้ targets **1 segment** (line-level), ส่วน
    `get_sutta` targets **ทั้งสูตร**. ถ้าอยากเทียบทั้งสูตร ต้องเรียก
    `compare_translations` หลาย segment

    📋 **Format ของ segment_id:** `<sutta_id>:<paragraph>.<line>` เช่น
    `mn1:171.4` (Mūlapariyāyasutta paragraph 171 line 4 — "Nandī dukkhassa
    mūlaṁ"). หา segment_id จาก `get_sutta` หรือ search results

    ⚠️ **State ปัจจุบัน:** Translation table ยังว่าง (DB load เฉพาะ default
    Pāli+English จาก bilara). `total_editions` มักเป็น 0; `text_pali` กับ
    `text_english` ใช้ได้เสมอ. Thai editions เพิ่มทีหลัง

    Args:
        segment_id: รหัส segment เช่น "mn26:8.2", "dn22:17.1", "mn62:5.3"

    Returns:
        - segment_id, sutta_id
        - text_pali: ต้นฉบับบาลี (Mahāsaṅgīti)
        - text_english: Sujato translation (จาก bilara-data)
        - text_thai_default: bilara Thai translation (ปัจจุบัน null เพราะ
          Thai disabled)
        - translations[]: filtered ตาม ENABLED_LANGUAGES — list of
          {edition, translator, language, text}
        - total_editions: นับจำนวน editions ที่ active
        - cross_reference: SuttaCentral segment-level deep link (สำคัญ —
          link ตรงไปยัง segment ใน SC viewer)
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

        # ดึงคำแปลจาก translation table — กรองเฉพาะภาษาที่เปิดใช้งาน
        cur.execute(
            """
            SELECT edition, translator, language, text
            FROM translation
            WHERE segment_id = %s AND language = ANY(%s)
            ORDER BY language, edition
            """,
            (seg_db_id, list(ENABLED_TRANSLATION_CODES)),
        )
        translations = [
            {
                "edition": r[0],
                "translator": r[1],
                "language": r[2],
                "text": r[3],
            }
            for r in cur.fetchall()
        ]

        # field text_thai_default = null เมื่อ Thai ไม่ได้เปิด
        # (schema คงไว้เพื่อ forward-compatible — เปิดกลับมาได้โดยไม่ต้องแก้ client)
        result: dict[str, Any] = {
            "segment_id": seg_id,
            "sutta_id": sutta_id,
            "text_pali": text_pali if "pali" in ENABLED_LANGUAGES else None,
            "text_english": text_english if "english" in ENABLED_LANGUAGES else None,
            "text_thai_default": text_thai_default if "thai" in ENABLED_LANGUAGES else None,
            "translations": translations,
            "total_editions": len(translations),
            "cross_reference": _cross_reference_urls(sutta_id, seg_id),
        }
        return result

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

    📖 **เกี่ยวกับฐานข้อมูลพจนานุกรม:**
    Tool นี้ใช้พจนานุกรมต้นฉบับหลายเล่ม รวมถึง "พจนานุกรมพุทธศาสน์ ฉบับ
    ประมวลศัพท์" ของสมเด็จพระพุทธโฆษาจารย์ (ป. อ. ปยุตฺโต) ที่เป็นภาษาไทย —
    เนื้อหาเหล่านี้เป็น **ผลงานต้นฉบับวิชาการที่สมบูรณ์อยู่แล้ว** (ไม่ใช่
    คำแปล) จึง **เปิดให้ใช้ได้เสมอ** แม้ ENABLED_LANGUAGES จะปิดภาษาไทย.
    AI client ควรแปลเนื้อหาผลลัพธ์ภาษาไทยเป็นภาษาผู้ใช้เองหากจำเป็น.

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
            
        definitions = [
            {
                "source": r[0],
                "text": r[1],
                "attribution": DICTIONARY_ATTRIBUTIONS.get(r[0], {}),
            }
            for r in cur.fetchall()
        ]
        
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
            "appears_in_context": appears_in,
            "notice": PROJECT_NOTICE,
        }
        
    except Exception as e:
        return {"error": f"เกิดข้อผิดพลาด: {str(e)}"}
    finally:
        cur.close()
        release_connection(conn)


@mcp.tool()
def parse_pali_word(word: str) -> dict[str, Any]:
    """วิเคราะห์คำบาลีเพื่อหารากศัพท์ (Stemming / Lemmatization เบื้องต้น)

    💡 **ใช้ tool นี้เมื่อ:**
    - เจอคำบาลีในข้อความ (เช่น `dukkhassa`, `bhikkhūnaṁ`) แล้ว
      `get_word_definition` หาไม่เจอ — Pāli inflect คำตามวิภัตติ ๘ × วจน ๒
      = ๑๖ form ต่อราก
    - ต้องการแยก compound word (`sammāsambuddhassa` → `sammā` + `sambuddha`
      + `-ssa` genitive)
    - ดู possible stems ก่อนค้นต่อใน `get_word_definition`

    🔄 **Workflow แนะนำ:**
    `parse_pali_word(inflected_form)` → ได้ `possible_stems[]` →
    เรียก `get_word_definition(stem)` ทีละ stem จนเจอ definition

    ⚠️ **ข้อจำกัด:**
    - เป็น rule-based เบื้องต้น — ตัด common suffixes (case endings, vowel
      shortening) ไม่ใช่ full morphological analyzer
    - Compound words (samāsa) ไม่ได้แยก — เช่น `dukkhanirodha` ไม่ตัดเป็น
      `dukkha` + `nirodha`
    - ไม่จับ sandhi (เสียงเชื่อม) เช่น `tena ahaṁ → tenāhaṁ`
    - ผลลัพธ์เป็น **possible** stems — ต้อง verify ผ่าน `get_word_definition`

    Args:
        word: คำบาลีที่ inflected (เช่น "dukkhassa", "bhikkhūnaṁ", "sīlavā")

    Returns:
        - original_word: input ที่ normalize แล้ว
        - matched_suffixes_removed: list ของ suffix ที่ตัดได้
        - possible_stems: list ของรากศัพท์ที่อาจเป็นไปได้
        - guidance: คำแนะนำ workflow ต่อ
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


@mcp.resource("tripitaka://sutta/{sutta_id}")
def sutta_resource(sutta_id: str) -> str:
    """ดึงเนื้อหาสูตรเป็น MCP resource (URI: tripitaka://sutta/{sutta_id}).

    เป็น native MCP resource alternative ของ get_sutta tool — client บางตัว
    (เช่น Claude Desktop) แสดง resources เป็น attachable context, AI สามารถ
    pin เนื้อหาสูตรไว้ในการสนทนาได้โดยไม่ต้องเรียก tool ทุกครั้ง.

    Returns: JSON object เหมือน get_sutta(sutta_id, language="all")
    """
    import json

    result = get_sutta(sutta_id, language="all")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.resource("tripitaka://word/{word}")
def word_resource(word: str) -> str:
    """พจนานุกรมศัพท์บาลี (URI: tripitaka://word/{word}).

    เป็น MCP resource สำหรับ pin พจนานุกรมเข้าบทสนทนา — เหมาะเมื่อกำลัง
    ศึกษาคำเฉพาะแล้วอยากให้ AI อ้างนิยามได้ตลอดโดยไม่ต้องเรียก tool ซ้ำ.

    Returns: JSON object เหมือน get_word_definition(word, language="all")
    """
    import json

    result = get_word_definition(word, language="all")
    return json.dumps(result, ensure_ascii=False, indent=2)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    print(f"🛕 Tripitaka MCP Server starting... (transport: {transport})")
    if transport in ("sse", "streamable-http", "http"):
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport=transport, host=host, port=port)
    else:
        mcp.run(transport=transport)
