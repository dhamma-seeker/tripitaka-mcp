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
from typing import Any, Literal

from dotenv import load_dotenv
from fastmcp import FastMCP

from db.backend import get_backend
from db.normalize import fold_pali
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
        f"🌐 Search index languages: {enabled_list}\n"
        if not disabled
        else (
            f"🌐 Search index languages: {enabled_list} "
            f"(temporarily disabled: {', '.join(sorted(disabled))} — "
            f"data not yet indexed)\n"
            "If the user's query is in a disabled language, translate it to "
            "**Pāli (Romanised, preferred) or English** before calling the "
            "search tools, then translate the result back into the user's "
            "language when you reply.\n"
        )
    )
    return (
        # NOTE: This instructions block is read by the MCP client (Claude
        # Desktop, Claude.ai, Cursor, etc.) on `initialize` and used as
        # session-level context. Keep it ENGLISH-PRIMARY — Thai-heavy
        # instructions caused Claude.ai to default to Thai replies even
        # when users typed in English (bug report 2026-05-12).
        "MCP server for searching and citing content from the Pāli Tipiṭaka "
        "(the Buddhist Canon). Use these tools to look up suttas, quote the "
        "Buddha's teachings verbatim, and compare translations across "
        "editions and languages.\n\n"
        "📣 **LANGUAGE GUIDELINE — IMPORTANT**\n"
        "Reply to the user in **the language they wrote in**. The user's "
        "input language is the only signal for response language — do NOT "
        "default to Thai or any other language just because this server "
        "documents Thai-source data. The corpus is bilingual (Pāli "
        "canonical + Bhikkhu Sujato English; Thai for select translations); "
        "translate Pāli quotes and explanations into the user's language as "
        "needed. If unsure, mirror the language of the user's most recent "
        "message.\n\n"
        + coverage_note
        + "\n🧭 **Which search tool?**\n"
        "- **Coverage / counting / \"don't miss any\"** — e.g. \"how many "
        "times does Kusinārā appear\", \"every place ānāpānassati is "
        "mentioned\", \"which pitakas mention X\": use **`survey_corpus`**. It "
        "returns an EXACT total, a per-pitaka breakdown, the distinct word "
        "forms matched, and an exhaustive (`complete:true`) enumeration — "
        "things `search_by_keyword` cannot give (it is ranked + capped at 50). "
        "Use `match_scope='stem'` to include inflections/compounds, and "
        "`mode='thorough'` to add concept-level (different-vocabulary) recall "
        "(hosted only; the `semantic` block is explicitly NON-exhaustive).\n"
        "- **Best few passages for a word** — `search_by_keyword`.\n"
        "- **\"Discourses about X\" / concept** — `search_hybrid`.\n"
        + "\n🔗 **Cross-reference URLs (IMPORTANT — always surface in your "
        "reply as clickable markdown links):**\n"
        "Every tool response includes a `cross_reference` field with URLs "
        "to the source material:\n"
        "• `tripitaka_mcp_reader` — bilingual reader (Pāli + English) on "
        "the same domain as this MCP server. `url` = full-sutta page; "
        "`segment_url` = deep-link that highlights and scroll-centres the "
        "cited segment.\n"
        "• `suttacentral` — Pāli canonical (Mahāsaṅgīti) + Sujato English "
        "(`url`, `pali_url`, `english_url`, `segment_url`).\n"
        "• `tipitaka_84000` — Thai Mahāchula edition "
        "(homepage + search hint).\n\n"
        "💡 **URL selection guide:**\n"
        "- **Primary verification**: `tripitaka_mcp_reader.url` for full "
        "suttas; use `segment_url` when quoting a specific sentence — the "
        "page renders the full sutta with highlight + scroll-centre on "
        "that segment.\n"
        "- **Canonical secondary** (for scholarship): "
        "`suttacentral.segment_url`, in case the user wants to verify "
        "against the Pāli edition.\n"
        "- **For Thai-speaking users only**: also include "
        "`tipitaka_84000.url` as a tertiary link — the Mahāchula edition "
        "has Thai translations but deep-links are volume-level only.\n"
        "- Always render links as **clickable markdown** so the user can "
        "verify the source in one click (lowers hallucination risk).\n"
        "\n📚 Data sources:\n"
        "• Pāli canon + English translations: SuttaCentral `bilara-data` "
        "(CC0).\n"
        "• Thai translations: Bhikkhu Thiranando, Ajahn Jayasaro (CC0); "
        "Mahāchula edition; Royal edition.\n"
        "• Buddhist dictionary "
        "(พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์): "
        "Somdet Phra Buddhaghosacariya (P. A. Payutto) — offered as "
        "Dhamma Dāna.\n"
        "• Upstream sources: https://www.watnyanaves.net, "
        "https://84000.org, https://suttacentral.net\n\n"
        "⚠️ Data is provided for study and Dhamma-Dāna purposes only. "
        "For authoritative citation, please verify against the latest "
        "printed editions.\n\n"
        "🙏 This project is offered as Dhamma Dāna — non-commercial use only."
    )


mcp = FastMCP("Tripitaka", instructions=_build_instructions())


def hosted_only_tool(**kwargs):
    """`@mcp.tool` variant ที่ลงทะเบียน tool **เฉพาะ backend ที่ไม่ใช่ sqlite**.

    semantic/hybrid search ต้องใช้ pgvector + embedding model — local (SQLite)
    mode ไม่มี. ถ้ายัง register ไว้ LLM client จะเห็นแล้วเรียก แล้วเจอ error
    แล้วสับสน/hallucinate (พบจาก POC offline stack 2026-05-16). local mode จึง
    ไม่ลงทะเบียน 2 tool นี้เลย — client เห็นแค่ 8 tool ที่ใช้ได้จริง.

    backend อื่น (postgres/hosted): ทำงานเหมือน `@mcp.tool(**kwargs)` ทุกประการ.
    """
    def decorator(fn):
        if get_backend().name == "sqlite":
            return fn  # ไม่ register เป็น MCP tool ใน local mode
        return mcp.tool(**kwargs)(fn)

    return decorator


# สร้างตารางตอน startup (ถ้ายังไม่มี)
# Prod ที่ใช้ readonly user ให้ข้ามด้วย TRIPITAKA_SKIP_MIGRATIONS=true
# เพราะ readonly role ไม่มีสิทธิ์ CREATE TABLE
# SQLite mode ก็ข้าม — DB ถูก build มาแล้ว (scripts/build_sqlite_db.py)
if (
    os.getenv("TRIPITAKA_SKIP_MIGRATIONS", "").lower() not in ("1", "true", "yes")
    and get_backend().name != "sqlite"
):
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
        "title": "พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์ (Buddhist Dictionary, Concept-Glossary edition)",
        "author": "Somdet Phra Buddhaghosacariya (P. A. Payutto)",
        "license": "Dhamma Dāna — non-commercial use only",
        "source_url": "https://www.watnyanaves.net",
        "note": "Verify against the latest printed edition for authoritative citation",
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
    "This project is offered as Dhamma Dāna — "
    "please use for study purposes only, not for commercial use."
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
#   Abhidhamma:    ds1.1, vb1.1, kv1.1, ya1.1, patthana1.1 (yes, "patthana" is one prefix, 8 chars)
# multiple `-[a-z]+` segments allowed (for SC's pli-tv-* convention).
# `\d*` (not `\d+`) so the digit-less "pli-tv-bu-pm" passes too.
# {2,10} on the leading prefix to fit "patthana" (8 chars) with headroom.
SUTTA_ID_PATTERN = re.compile(r"^[a-z]{2,10}(-[a-z]+)*\d*(-\d+)?(\.\d+(-\d+)?){0,4}[a-z]?$")


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

# Tripitaka MCP own bilingual reader (Pāli + English) — same domain as MCP
# server, so users can verify quotes without leaving our trust boundary.
# Override per environment via TRIPITAKA_READER_BASE (e.g. http://127.0.0.1:8090
# for local dev). Defaults to canonical apex.
TRIPITAKA_READER_BASE = os.getenv(
    "TRIPITAKA_READER_BASE", "https://tripitaka-mcp.com"
).rstrip("/")

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
    # Abhidhamma — มี active code (segment_count > 0) คู่กับ legacy code (segment_count = 0)
    # ทั้งสอง map เป็นเล่มเดียวกัน เผื่อ user ส่ง id แบบไหนมาก็ตอบถูก
    "ds": 34,
    "vb": 35,
    "dt": 36,
    "pp": 36,
    "kv": 37,
    "ya": 38,        # active id format (e.g. ya1.1.1)
    "ym": 38,        # legacy schema alias
    "patthana": 40,  # active id format (e.g. patthana1.1)
    "pt": 40,        # legacy schema alias
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
            f"Opens at the start of volume {volume} of the 45-volume "
            f"Mahāchula edition — scroll or search for the sutta within "
            f"the volume. Use search_url to query 84000.org directly."
        )
        return {
            "url": volume_url,
            "search_url": google_search,
            "note": note,
        }
    # Fallback: paracanonical (Mil, Ne, Pe) or IDs outside the volume mapping
    return {
        "url": TIPITAKA_84000_BASE,
        "search_url": google_search,
        "note": (
            "This sutta is outside the 45-volume main canon "
            "(paracanonical) — use search_url to find it on the site."
        ),
    }


def _tripitaka_reader_urls(
    sutta_id: str, segment_id: str | None = None
) -> dict[str, str]:
    """สร้าง URL set ของ Tripitaka MCP bilingual reader (Pāli + English)
    บนโดเมนเดียวกับ MCP server — user verify ได้โดยไม่ออก trust boundary.

    Returns:
        - url: หน้าสูตรเต็ม (แสดง Pāli + Sujato EN ทุก segment)
        - segment_url: deep-link พร้อม fragment ที่ highlight + scroll-center
          segment ที่อ้างถึง (auto-applied โดย CSS `:target` + JS)
    """
    base = f"{TRIPITAKA_READER_BASE}/read/{sutta_id}"
    urls = {"url": base}
    if segment_id:
        urls["segment_url"] = f"{base}#{segment_id}"
    return urls


def _cross_reference_urls(sutta_id: str, segment_id: str | None = None) -> dict[str, Any]:
    """รวม URL จากทุกแหล่งสำหรับ AI client surface ใน response.

    Returns dict with:
        - tripitaka_mcp_reader: bilingual reader บนโดเมนเดียวกับ MCP server
          (preferred verification target — same trust boundary, ไม่พา user
          ออกไป external)
        - suttacentral: deep-link set (canonical reference, segment URL)
        - tipitaka_84000: ฉบับมหาจุฬาฯ ไทย — volume page + Google search
          fallback (deep-link mapping เป็น heuristic, ใช้ search_url ถ้าไม่ตรง)
    """
    return {
        "tripitaka_mcp_reader": _tripitaka_reader_urls(sutta_id, segment_id),
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


def _keyword_search_sqlite(
    cur,
    keyword: str,
    language: str,
    edition: str | None,
    pitaka: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    """FTS5-backed keyword search สำหรับ SQLite mode.

    คืน list[dict] รูปแบบเดียวกับ Postgres path ของ search_by_keyword
    (segment_id, sutta_id, text_*, [edition], similarity, word_similarity).
    ใช้แทน pg_trgm similarity()/word_similarity() ที่ SQLite ไม่มี — ดู
    Dual-Backend Discipline ใน CLAUDE.md.
    """
    # escape keyword เป็น FTS5 phrase literal — กัน special char (* " : ฯลฯ)
    phrase = '"' + (keyword or "").replace('"', '""') + '"'

    if language == "thai":
        sql = """
            SELECT
                seg.segment_id,
                sec.sutta_id,
                seg.text_pali,
                t.text AS text_thai,
                seg.text_english,
                t.edition,
                bm25(translation_fts) AS rank
            FROM translation_fts
            JOIN translation t ON t.id = translation_fts.rowid
            JOIN segment seg ON t.segment_id = seg.id
            JOIN section sec ON seg.section_id = sec.id
            JOIN book b ON sec.book_id = b.id
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE translation_fts MATCH ?
              AND t.language = 'th'
        """
        sql_params: list[Any] = [phrase]
        if edition:
            sql += " AND t.edition = ?"
            sql_params.append(edition)
        if pitaka:
            sql += " AND p.code = ?"
            sql_params.append(pitaka)
    else:
        text_col = LANGUAGE_COLUMNS[language]
        sql = """
            SELECT
                seg.segment_id,
                sec.sutta_id,
                seg.text_pali,
                seg.text_thai,
                seg.text_english,
                bm25(segment_fts) AS rank
            FROM segment_fts
            JOIN segment seg ON seg.id = segment_fts.rowid
            JOIN section sec ON seg.section_id = sec.id
            JOIN book b ON sec.book_id = b.id
            JOIN nikaya n ON b.nikaya_id = n.id
            JOIN pitaka p ON n.pitaka_id = p.id
            WHERE segment_fts MATCH ?
        """
        # column filter — ค้นเฉพาะคอลัมน์ภาษาที่เลือก (เทียบเท่า seg.{text_col})
        sql_params = [f"{text_col} : {phrase}"]
        if pitaka:
            sql += " AND p.code = ?"
            sql_params.append(pitaka)

    sql += " ORDER BY rank LIMIT ?"
    sql_params.append(limit)

    cur.execute(sql, sql_params)
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # bm25 → similarity-like score (ค่ามาก = ตรงกว่า) ให้ schema ตรงกับ Postgres
    out: list[dict[str, Any]] = []
    for r in rows:
        score = round(-(r.pop("rank", 0.0) or 0.0), 4)
        r["similarity"] = score
        r["word_similarity"] = score
        out.append(r)
    return out


@mcp.tool(
    annotations={
        "title": "Keyword Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def search_by_keyword(
    keyword: str,
    language: Literal["pali", "english", "thai"] = "pali",
    edition: Literal["dhiranandi", "jayasaro", "mbu", "royal"] | None = None,
    pitaka: Literal["vinaya", "sutta", "abhidhamma"] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Keyword search across the Pāli Tipiṭaka (trigram word-similarity).

    Searches the configured enabled language(s) on the server. Filterable
    by pitaka and translation edition.

    💡 **Hints for the AI client:**
    The system's canonical reference is Romanised Pāli (from SuttaCentral).
    If the user asks in a disabled or unsupported language, translate the
    keyword to **Romanised Pāli (preferred) or English** before calling this
    tool — e.g. "suffering" → "dukkha", "mindfulness of breathing" →
    "ānāpānassati". See the server instructions for the enabled language set.

    🔍 **Pick the right search tool for the question shape:**
    - **Term lookup (exact word appearances)** — e.g. "occurrences of
      `ānāpānassati`": this tool is best (trigram nails the exact word).
    - **Concept search ("discourses about X")** — e.g. "discourses about
      mindfulness of breathing": **use `search_hybrid` instead.** Canonical
      Pāli has two quirks that hurt keyword search for concepts:
        • Section headings (`Ānāpānapabba`) often use a different word than
          the teaching body, which uses verb forms (`assasati`, `passasati`,
          `dīghaṁ`, `rassaṁ`). E.g. DN22's Ānāpānapabba has 16 segments but
          the word `ānāpāna` appears in only 2 (header + footer) — the
          actual teaching segments won't match.
        • Stock phrases (e.g. `So satova assasati, satova passasati`)
          recur in 10+ suttas, so a keyword query ranks broadly and won't
          pinpoint the canonical reference.
    - **General keyword survey** — set `limit≥30` and filter client-side,
      or call multiple related forms (root verb + noun + compound).

    Args:
        keyword: The word/phrase to search for.
        language: Search language — must be in the server's ENABLED_LANGUAGES
                  (default: "pali"). Disabled languages return an error.
        edition: Thai translation edition — "dhiranandi", "jayasaro", "mbu",
                  "royal" or None. Only used when language="thai" and Thai is
                  enabled on the server.
        pitaka: Filter by pitaka — "vinaya", "sutta", "abhidhamma" or None
                (all). ✅ v1.1+: all three pitakas at parity with SuttaCentral
                bilara — see list_structure for live counts.
        limit: Maximum results (default: 10, max: 50).
    """
    try:
        language = _validate_choice(language, VALID_LANGUAGES_SEARCH, "language")
        edition = _validate_choice(edition, VALID_EDITIONS, "edition")
        pitaka = _validate_choice(pitaka, VALID_PITAKAS, "pitaka")
    except ValidationError as e:
        return [{"error": str(e)}]

    limit = min(max(1, limit), 50)
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        params = {"kw": keyword, "limit": limit}

        if backend.name == "sqlite":
            results = _keyword_search_sqlite(
                cur, keyword, language, edition, pitaka, limit
            )
        elif language == "thai":
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
            return [{"message": f"No results for '{keyword}' in {language}{hint}"}]

        return [
            _strip_disabled_text_fields({
                **r,
                "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
            })
            for r in results
        ]

    except Exception as e:
        return [{"error": f"Search error: {str(e)}"}]
    finally:
        cur.close()
        backend.release(conn)


# =============================================================================
# Corpus survey — exhaustive lexical coverage with a completeness contract
# =============================================================================
# search_by_keyword answers "show me the best matches" — ranked, hard-capped at
# 50, no total. survey_corpus answers a different question: "find EVERY
# occurrence across the whole canon and tell me you didn't miss any."
#
# The lexical layer is deterministic, so it carries a hard guarantee
# (`complete: true`) + an exact count + the distinct surface forms it matched,
# so the caller can audit exactly what was (and wasn't) counted. Concept-level
# semantic recall is a separate layer added later and is explicitly NOT
# exhaustive — we never let it claim completeness. See PROGRESS.md.

# token = a run of (Unicode) word characters — Romanised Pāli words incl.
# diacritics (ā, ṁ, ñ …) all match \w in Python 3 str patterns.
# folding lives in db/normalize.fold_pali — used only to extract matched_forms
# and build the folded needle; the actual match is f_unaccent (PG) / FTS5 (SQLite).
_PALI_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _matched_surface_forms(texts, folded_kw: str, scope: str) -> list[str]:
    """Distinct surface forms (verbatim, with diacritics) that matched.

    `word` scope → a token whose fold == folded_kw.
    `stem` scope → a token whose fold starts with folded_kw.

    This is the audit half of the completeness contract: the caller sees every
    inflection/compound that was counted (e.g. kusinārā, kusinārāyaṁ,
    kusināravagga) and can discard over-matches itself.

    NOTE: audit is token-level, so a multi-token PHRASE query (folded_kw with a
    space) yields [] here even when total_segments > 0 — no single surface form
    represents a phrase. Counts/results stay correct; only this form list is
    empty for phrases.
    """
    forms: dict[str, None] = {}
    for t in texts:
        for tok in _PALI_TOKEN_RE.findall(t or ""):
            folded = fold_pali(tok)
            hit = folded == folded_kw if scope == "word" else folded.startswith(folded_kw)
            if hit:
                forms.setdefault(tok, None)
    return sorted(forms)


# cap on how many matching segments we scan to extract matched_forms — keeps a
# very common term (e.g. "dukkha") cheap. Counts/aggregation are always exact
# (COUNT in SQL); only the matched_forms LIST may be partial past this, and we
# flag it via forms_truncated so we never silently under-report.
_FORMS_SCAN_CAP = 20000


def _fts_match_expr(text_col: str, folded_kw: str, scope: str) -> str:
    """Build an FTS5 MATCH expression for one text column.

    word → quoted phrase of the folded tokens (exact word match).
    stem → each folded token as a prefix token (kusinara* …) for inflection +
           compound recall.
    """
    tokens = [t for t in folded_kw.split() if t]
    if not tokens:
        return f'{text_col} : ""'
    if scope == "stem":
        return f"{text_col} : " + " ".join(f"{t}*" for t in tokens)
    return f'{text_col} : "{folded_kw}"'


def _survey_sqlite(cur, keyword, language, pitaka, scope, page_size, cursor):
    """Lexical-exhaustive survey for SQLite/local mode (FTS5-backed).

    Returns the `lexical` block of the completeness contract. Counts and
    aggregation are exact (SQL COUNT); the FTS tokenizer already folds
    diacritics so matching is diacritic-insensitive.
    """
    text_col = LANGUAGE_COLUMNS[language]  # text_pali / text_english
    folded_kw = fold_pali(keyword)
    match_expr = _fts_match_expr(text_col, folded_kw, scope)

    # shared FROM + WHERE — joined up to pitaka so we can filter/aggregate
    base = (
        " FROM segment_fts"
        " JOIN segment seg ON seg.id = segment_fts.rowid"
        " JOIN section sec ON seg.section_id = sec.id"
        " JOIN book b ON sec.book_id = b.id"
        " JOIN nikaya n ON b.nikaya_id = n.id"
        " JOIN pitaka p ON n.pitaka_id = p.id"
        " WHERE segment_fts MATCH ?"
    )
    where_params: list[Any] = [match_expr]
    if pitaka:
        base += " AND p.code = ?"
        where_params.append(pitaka)

    # exact totals
    cur.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT sec.sutta_id){base}", where_params
    )
    total_segments, total_suttas = cur.fetchone()

    # per-pitaka breakdown
    cur.execute(f"SELECT p.code, COUNT(*){base} GROUP BY p.code", where_params)
    by_pitaka = {code: cnt for code, cnt in cur.fetchall()}

    # matched surface forms (audit) — scan matching texts up to the cap
    cur.execute(
        f"SELECT seg.{text_col}{base} LIMIT ?", where_params + [_FORMS_SCAN_CAP]
    )
    scanned = [row[0] for row in cur.fetchall()]
    matched_forms = _matched_surface_forms(scanned, folded_kw, scope)
    forms_truncated = total_segments > _FORMS_SCAN_CAP

    # one page of results, canonical order (insertion order ≈ canonical)
    cur.execute(
        "SELECT seg.segment_id, sec.sutta_id, seg.text_pali, seg.text_english"
        f"{base} ORDER BY seg.id LIMIT ? OFFSET ?",
        where_params + [page_size, cursor],
    )
    cols = ["segment_id", "sutta_id", "text_pali", "text_english"]
    results = [dict(zip(cols, row)) for row in cur.fetchall()]

    return {
        "total_segments": total_segments,
        "total_suttas": total_suttas,
        "by_pitaka": by_pitaka,
        "matched_forms": matched_forms,
        "forms_truncated": forms_truncated,
        "results": results,
    }


def _survey_postgres(cur, keyword, language, pitaka, scope, page_size, cursor):
    """Lexical-exhaustive survey for Postgres/hosted mode.

    Diacritic-insensitive matching reuses the functional GIN index
    `gin(f_unaccent(text_pali) gin_trgm_ops)` (f_unaccent = unaccent + lower),
    so `kusinara` finds `kusinārā` and the match is fully index-driven (~ms over
    the whole canon) — no extra column, no backfill. f_unaccent folds the same
    as db.normalize.fold_pali for the canon (verified: kusinārā → 11 word / 67
    stem on both). The extension/function/indexes are set up by
    scripts/setup_unaccent.sql (run post-data-load; deploy.sh does this).

      word → whole-word match: ILIKE substring (drives the index) + word-
             boundary regex (\\m..\\M) refine.
      stem → word-prefix match: ILIKE substring + leading-boundary regex (\\m..).
    """
    text_col = LANGUAGE_COLUMNS[language]  # text_pali / text_english
    folded_kw = fold_pali(keyword)
    # MUST mirror the indexed expression `f_unaccent(text_<lang>)` exactly so the
    # planner uses idx_segment_<lang>_unaccent_trgm.
    fexpr = f"f_unaccent(seg.{text_col})"

    # ILIKE substring (folded, lowercased — f_unaccent lowercases too) drives the
    # trigram index; the regex then refines to whole-word / word-prefix. A multi-
    # token phrase skips the regex (substring only — boundary regex across tokens
    # is brittle).
    conds = [f"{fexpr} LIKE %(like)s"]
    params: dict[str, Any] = {"like": f"%{folded_kw}%"}
    if folded_kw.strip() and " " not in folded_kw.strip():
        params["re"] = r"\m" + re.escape(folded_kw) + (r"\M" if scope == "word" else "")
        conds.append(f"{fexpr} ~ %(re)s")
    cond = " AND ".join(conds)

    base = (
        " FROM segment seg"
        " JOIN section sec ON seg.section_id = sec.id"
        " JOIN book b ON sec.book_id = b.id"
        " JOIN nikaya n ON b.nikaya_id = n.id"
        " JOIN pitaka p ON n.pitaka_id = p.id"
        f" WHERE {cond}"
    )
    if pitaka:
        base += " AND p.code = %(pitaka)s"
        params["pitaka"] = pitaka

    cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT sec.sutta_id){base}", params)
    total_segments, total_suttas = cur.fetchone()

    cur.execute(f"SELECT p.code, COUNT(*){base} GROUP BY p.code", params)
    by_pitaka = {code: cnt for code, cnt in cur.fetchall()}

    cur.execute(
        f"SELECT seg.{text_col}{base} LIMIT %(cap)s", {**params, "cap": _FORMS_SCAN_CAP}
    )
    scanned = [row[0] for row in cur.fetchall()]
    matched_forms = _matched_surface_forms(scanned, folded_kw, scope)
    forms_truncated = total_segments > _FORMS_SCAN_CAP

    cur.execute(
        "SELECT seg.segment_id, sec.sutta_id, seg.text_pali, seg.text_english"
        f"{base} ORDER BY seg.id LIMIT %(limit)s OFFSET %(offset)s",
        {**params, "limit": page_size, "offset": cursor},
    )
    cols = ["segment_id", "sutta_id", "text_pali", "text_english"]
    results = [dict(zip(cols, row)) for row in cur.fetchall()]

    return {
        "total_segments": total_segments,
        "total_suttas": total_suttas,
        "by_pitaka": by_pitaka,
        "matched_forms": matched_forms,
        "forms_truncated": forms_truncated,
        "results": results,
    }


# --- semantic recall layer (thorough mode, hosted-only) ----------------------
# Concept-level recall — surfaces passages that teach the same idea with
# DIFFERENT vocabulary (e.g. ānāpānassati taught via assasati/passasati). This
# is approximate by nature, so it is ALWAYS labelled non-exhaustive and never
# carries a completeness guarantee. It augments — never replaces — the lexical
# layer.

_SEM_DEFAULT_THRESHOLD = 0.7
_SEM_DEFAULT_K = 50
_SEM_MAX_K = 200


def _text_matches_lexically(text: str, folded_kw: str, scope: str) -> bool:
    """True if `text` would be caught by the lexical layer for this term.

    Lets the semantic layer flag which of its hits are *new* (concept-only)
    vs. already covered lexically — same fold/word/stem rule as the survey.
    """
    for tok in _PALI_TOKEN_RE.findall(text or ""):
        folded = fold_pali(tok)
        if (folded == folded_kw) if scope == "word" else folded.startswith(folded_kw):
            return True
    return False


def _semantic_layer_postgres(cur, query, k, threshold, folded_kw, scope, language, pitaka):
    """Bounded semantic recall over Pāli embeddings (pgvector).

    Returns the `semantic` contract block: top-k segments within `threshold`
    cosine distance, each flagged `in_lexical` so the caller sees which are
    concept-only finds. `capped` is True when we hit k (more may exist) — we
    never silently truncate.

    Respects the same `pitaka` filter as the lexical layer (so a pitaka-scoped
    survey stays scoped end-to-end). `in_lexical` is judged against the SAME
    text column the lexical layer matched (`language`), not always Pāli.
    """
    try:
        from embedding.model import generate_embedding

        q_emb = generate_embedding(query)
    except ImportError:
        return {"available": False, "note": "Embedding model not installed on this server."}
    except Exception as e:
        return {"available": False, "note": f"Could not embed query: {e}"}

    # join only as deep as needed: pitaka filter pulls in book→nikaya→pitaka
    sql = (
        "SELECT seg.segment_id, sec.sutta_id, seg.text_pali, seg.text_english,"
        " seg.embedding <=> %(emb)s::vector AS distance"
        " FROM segment seg JOIN section sec ON seg.section_id = sec.id"
    )
    params: dict[str, Any] = {"emb": q_emb, "threshold": threshold, "k": k}
    if pitaka:
        sql += (
            " JOIN book b ON sec.book_id = b.id"
            " JOIN nikaya n ON b.nikaya_id = n.id"
            " JOIN pitaka p ON n.pitaka_id = p.id"
        )
    sql += " WHERE seg.embedding IS NOT NULL AND (seg.embedding <=> %(emb)s::vector) <= %(threshold)s"
    if pitaka:
        sql += " AND p.code = %(pitaka)s"
        params["pitaka"] = pitaka
    sql += " ORDER BY distance LIMIT %(k)s"

    cur.execute(sql, params)
    cols = ["segment_id", "sutta_id", "text_pali", "text_english", "distance"]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    # judge in_lexical against the column the lexical layer actually matched
    lex_col = LANGUAGE_COLUMNS[language]
    new_finds = 0
    items = []
    for r in rows:
        in_lex = _text_matches_lexically(r.get(lex_col, ""), folded_kw, scope)
        if not in_lex:
            new_finds += 1
        items.append({
            **r,
            "distance": round(float(r["distance"]), 4),
            "in_lexical": in_lex,
            "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
        })
    items = [_strip_disabled_text_fields(it) for it in items]

    return {
        "available": True,
        "exhaustive": False,
        "note": "Related by MEANING — approximate, NOT exhaustive. `in_lexical` "
        "flags hits already in the lexical layer; the rest are concept-only "
        "finds (different vocabulary).",
        "threshold": threshold,
        "returned": len(items),
        "new_concept_finds": new_finds,
        "capped": len(items) >= k,
        "results": items,
    }


_SEMANTIC_FAST = {
    "available": False,
    "note": "Lexical-only (mode='fast'). Pass mode='thorough' for concept-level "
    "semantic recall (different-vocabulary passages).",
}

_SEMANTIC_LOCAL = {
    "available": False,
    "note": "Semantic recall needs the hosted server (pgvector + embeddings). "
    "Local mode is lexical-only — the lexical coverage above is still exhaustive.",
}


@mcp.tool(
    annotations={
        "title": "Survey Corpus (exhaustive)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def survey_corpus(
    keyword: str,
    language: Literal["pali", "english"] = "pali",
    pitaka: Literal["vinaya", "sutta", "abhidhamma"] | None = None,
    match_scope: Literal["word", "stem"] = "word",
    mode: Literal["fast", "thorough"] = "fast",
    page_size: int = 20,
    cursor: int = 0,
    sem_threshold: float = _SEM_DEFAULT_THRESHOLD,
    sem_limit: int = _SEM_DEFAULT_K,
) -> dict[str, Any]:
    """Exhaustively survey the WHOLE Tipiṭaka for a term — guaranteed complete.

    Use this (not `search_by_keyword`) when the question is about **coverage or
    counting** rather than "show me the best passages":
    - "How many times does Kusinārā appear in the canon?"
    - "Every place ānāpānassati is mentioned — don't miss any"
    - "Which pitakas/how many suttas mention this term?"

    Unlike `search_by_keyword` (ranked, capped at 50, no total), this returns an
    **exact count**, a **per-pitaka breakdown**, the **distinct surface forms**
    that matched (so you can audit and discard over-matches), and a paginated
    enumeration. The `lexical` result carries `complete: true` — a hard
    guarantee that nothing was dropped for the chosen `match_scope`.

    Two layers, two different promises:
    - **lexical** — the word and its forms. Deterministic + EXHAUSTIVE.
    - **semantic** (`mode="thorough"`, hosted only) — passages teaching the same
      concept with DIFFERENT vocabulary (e.g. ānāpānassati via
      `assasati`/`passasati`). Approximate, **NOT exhaustive** — it never claims
      completeness, it only boosts recall.

    Args:
        keyword: Term to survey (Romanised Pāli preferred; diacritics optional —
                 matching folds `ā→a`, `ṁ→m`, etc.).
        language: "pali" (default) or "english". Thai is not indexed yet.
        pitaka: Restrict to "vinaya" / "sutta" / "abhidhamma", or None for all.
        match_scope: "word" (default) matches the exact word/phrase only.
                     "stem" also matches inflections + compounds via prefix
                     (kusinārā → kusinārāyaṁ, kusināravagga …) — higher recall,
                     may over-match (audit via `matched_forms`).
        mode: "fast" (default) = lexical only — quick, no server-side ML, works
              offline. "thorough" = also run the semantic layer (hosted only;
              this is the heavier part). The lexical guarantee holds in BOTH.
        page_size: Lexical results per page (default 20, max 100). Counts/forms
                   cover the WHOLE corpus regardless of this.
        cursor: Offset into the full lexical result set for pagination.
        sem_threshold: Max cosine distance for semantic hits (default 0.7;
                       lower = stricter). Only used when mode="thorough".
        sem_limit: Max semantic hits (default 50, max 200). `capped` flags when
                   reached. Only used when mode="thorough".

    Returns:
        A completeness contract: { query, language, match_scope, mode,
        lexical: { complete, total_segments, total_suttas, by_pitaka,
        matched_forms, forms_truncated, page, results },
        semantic: { available, exhaustive:false, new_concept_finds, capped,
        results, … } }.
    """
    try:
        language = _validate_choice(language, VALID_LANGUAGES_SEARCH, "language")
        pitaka = _validate_choice(pitaka, VALID_PITAKAS, "pitaka")
    except ValidationError as e:
        return {"error": str(e)}

    if match_scope not in ("word", "stem"):
        return {"error": f"invalid match_scope {match_scope!r} (allowed: 'word', 'stem')"}
    if mode not in ("fast", "thorough"):
        return {"error": f"invalid mode {mode!r} (allowed: 'fast', 'thorough')"}
    if language not in LANGUAGE_COLUMNS:
        # thai lives in the translation table and isn't indexed for survey yet
        return {
            "error": f"survey_corpus supports 'pali'/'english' only — "
            f"{language!r} is not indexed for exhaustive survey yet."
        }
    if not (keyword or "").strip():
        return {"error": "keyword must not be empty"}

    page_size = min(max(1, page_size), 100)
    cursor = max(0, cursor)
    sem_limit = min(max(1, sem_limit), _SEM_MAX_K)
    folded_kw = fold_pali(keyword)

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        if backend.name == "sqlite":
            lex = _survey_sqlite(cur, keyword, language, pitaka, match_scope, page_size, cursor)
        else:
            lex = _survey_postgres(cur, keyword, language, pitaka, match_scope, page_size, cursor)

        # semantic layer: thorough mode only, hosted only
        if mode == "fast":
            semantic = _SEMANTIC_FAST
        elif backend.name == "sqlite":
            semantic = _SEMANTIC_LOCAL
        else:
            semantic = _semantic_layer_postgres(
                cur, keyword, sem_limit, sem_threshold, folded_kw, match_scope,
                language, pitaka,
            )
    except Exception as e:
        return {"error": f"Survey error: {str(e)}"}
    finally:
        try:
            cur.close()
        except Exception:
            pass
        backend.release(conn)

    total = lex["total_segments"]
    if total == 0:
        return {
            "query": keyword,
            "language": language,
            "match_scope": match_scope,
            "mode": mode,
            "lexical": {
                "complete": True,
                "total_segments": 0,
                "total_suttas": 0,
                "by_pitaka": {},
                "matched_forms": [],
                "results": [],
                "message": f"No lexical occurrences of '{keyword}' ({match_scope}) in the canon.",
            },
            "semantic": semantic,
        }

    returned = len(lex["results"])
    next_cursor = cursor + returned if cursor + returned < total else None
    results = [
        _strip_disabled_text_fields({
            **r,
            "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
        })
        for r in lex["results"]
    ]

    return {
        "query": keyword,
        "language": language,
        "match_scope": match_scope,
        "mode": mode,
        "lexical": {
            "complete": True,
            "total_segments": total,
            "total_suttas": lex["total_suttas"],
            "by_pitaka": lex["by_pitaka"],
            "matched_forms": lex["matched_forms"],
            "forms_truncated": lex["forms_truncated"],
            "page": {
                "cursor": cursor,
                "page_size": page_size,
                "returned": returned,
                "next_cursor": next_cursor,
            },
            "results": results,
        },
        "semantic": semantic,
    }


@mcp.tool(
    annotations={
        "title": "Get Sutta",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def get_sutta(
    sutta_id: str,
    language: Literal["pali", "thai", "english", "all"] = "pali",
    edition: Literal["dhiranandi", "jayasaro", "mbu", "royal"] | None = None,
) -> dict[str, Any]:
    """Fetch the full content of a sutta/section by ID — returns every segment.

    Uses standard SuttaCentral IDs, e.g.:
    - `mn1` = Majjhima Nikāya sutta 1 (Mūlapariyāyasutta, 334 segments)
    - `dn22` = Dīgha Nikāya sutta 22 (Mahāsatipaṭṭhānasutta, 454 segments)
    - `dn16` = Dīgha Nikāya sutta 16 (Mahāparinibbānasutta — the longest
      sutta in the canon, 1,664 segments)
    - `sn56.11` = Saṃyutta 56.11 (Dhammacakkappavattana)
    - `mn62` = Majjhima Nikāya 62 (Mahārāhulovāda — advice to Rāhula)
    - `dhp1-20` = Dhammapada verses 1-20 (KN uses range format)
    - `mil3.1.1` = Milindapañha 3.1.1 (paracanonical, 3–4 level id)

    💡 **Hints for the AI client:**
    - **Quote `text_pali` / `text_english` directly from the returned
      segments** — do not rely on training memory. The system is
      verifiable; AI recall is often wrong.
    - Short segments ending in `:0.1` or `:0.2` are usually **headers**
      (nikāya/sutta names), not the teaching itself — actual content
      starts around `:1.1`.
    - Segments ending in "...niṭṭhitaṁ" (e.g. `mn1:194.10` =
      "Mūlapariyāyasuttaṁ niṭṭhitaṁ paṭhamaṁ") are **colophons**
      marking the close of the sutta.
    - Segments containing `…pe…` (peyyāla) are **abbreviated repetitions**
      — not missing data. Pāli texts use this convention for repeated
      stock phrases.
    - The response includes a `cross_reference` field — render the URLs
      as clickable markdown in your reply so users can verify the source.

    ✅ **Coverage (v1.1+):** all three pitakas at parity with SuttaCentral
    `bilara-data`:
    - Sutta Piṭaka (DN/MN/SN/AN/KN): Pāli + Sujato EN (5,791 sections)
    - Vinaya Piṭaka: Pāli + Brahmali EN — SC codes e.g.
      `pli-tv-bu-vb-pj1` (Bhikkhu Pārājika 1), `pli-tv-bi-vb-pj1`
      (Bhikkhunī), `pli-tv-kd1` (Mahāvagga), `pli-tv-pvr10` (Parivāra),
      `pli-tv-bu-pm` (Bhikkhu Pātimokkha)
    - Abhidhamma Piṭaka: 7 books (ds, vb, dt, pp, kv, ya, patthana) —
      Pāli only (bilara has no English translator for any Abhidhamma book)

    Args:
        sutta_id: Sutta ID, e.g. "mn1", "dn22", "sn56.11", "dhp1-20".
        language: Which language to return — "pali", "thai", "english",
                  or "all" (default: "pali"). Thai is currently disabled
                  on the server, so Thai fields return null.
        edition: Thai translation edition — "dhiranandi", "jayasaro",
                 "mbu", "royal", or None. If None, uses `text_thai` from
                 bilara-data. ⚠️ The DB has no Thai editions loaded yet,
                 so most values return null.

    Returns:
        Sutta data including:
        - sutta_id, title{pali,thai,english}, nikaya, pitaka, edition
        - segment_count, segments[] (id-sorted, every segment included)
        - cross_reference: SuttaCentral URLs (sutta + Pāli + English) plus
          84000.org link for Thai-user routing.
    """
    try:
        sutta_id = _validate_sutta_id(sutta_id)
        language = _validate_choice(language, VALID_LANGUAGES_DISPLAY, "language")
        edition = _validate_choice(edition, VALID_EDITIONS, "edition")
    except ValidationError as e:
        return {"error": str(e)}

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)

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
            return {"error": f"Sutta not found: {sutta_id}"}

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
        return {"error": f"Error: {str(e)}"}
    finally:
        cur.close()
        backend.release(conn)


@hosted_only_tool(
    annotations={
        "title": "Semantic Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def search_semantic(
    query: str,
    language: str = "pali",
    limit: int = 5,
    threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Semantic search — match by meaning, not exact words.

    Uses vector similarity (cosine distance) over `text_pali` embedded with
    a multilingual MiniLM model.

    🤔 **In most cases you should use `search_hybrid` instead** — it
    combines this semantic search with keyword search and ranks better.
    Use this tool only when you need:
    - Pure semantic results (no keyword influence)
    - Fine-grained `threshold` tuning (hybrid uses RRF which is harder
      to tune)
    - To debug what semantic alone picks up vs keyword

    ⚠️ Known limitations:
    - The index is **Pāli only** (English/Thai queries pass through the
      multilingual embedding but the model isn't tuned on Pāli)
    - English queries usually embed better than Thai (model is EN-primary)
    - For specific Pāli terms (`appamāda`, `dukkha`), exact match is
      better — use `search_by_keyword` instead
    - Pāli stock phrases recur in many suttas → similarity scores
      cluster; read the top 10, don't trust rank 1 alone

    Args:
        query: Query text (English works best, then Pāli, Thai is weakest).
        language: Output language — "pali", "thai", "english", or "all"
                  (Thai disabled → null).
        limit: Maximum results (default: 5, max: 20).
        threshold: Maximum cosine distance (smaller = stricter match).
                   Default 0.7; lower to 0.5 for tighter matches, raise
                   to 0.9 for broader.

    Returns:
        Results sorted by ascending distance. Each item:
        - segment_id, sutta_id, text_pali/text_english (per language flag),
          distance, cross_reference URLs.
    """
    limit = min(max(1, limit), 20)

    if get_backend().name == "sqlite":
        return [
            {
                "error": "semantic search is not available in local (SQLite) "
                "mode — it requires the hosted server (pgvector + an embedding "
                "model). Use search_by_keyword instead."
            }
        ]

    try:
        # สร้าง embedding จาก query
        from embedding.model import generate_embedding

        query_embedding = generate_embedding(query)
    except ImportError:
        return [{"error": "Embedding module not installed — please use search_by_keyword instead"}]
    except Exception as e:
        return [{"error": f"Could not create embedding: {str(e)}"}]

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)

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
            return [{"message": f"No semantic matches found (distance < {threshold}). Try a higher threshold for a broader search."}]

        return [
            _strip_disabled_text_fields({
                **r,
                "cross_reference": _cross_reference_urls(r["sutta_id"], r["segment_id"]),
            })
            for r in results
        ]

    except Exception as e:
        return [{"error": f"Search error: {str(e)}"}]
    finally:
        cur.close()
        backend.release(conn)


@hosted_only_tool(
    annotations={
        "title": "Hybrid Search",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def search_hybrid(
    query: str,
    language: str = "pali",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Hybrid search — combines keyword + semantic search via RRF.

    Uses Reciprocal Rank Fusion (RRF) to merge exact-word results with
    meaning-based results. **This is the recommended tool for "discourses
    about X" / concept queries**, because the semantic side catches suttas
    that discuss a concept using different vocabulary (e.g. some
    mindfulness-of-breathing suttas use `assasati/passasati/dīghaṁ`
    instead of `ānāpānassati`).

    💡 **Hints for the AI client:**
    - English queries usually work best (e.g. `mindfulness of breathing`)
      because the embedding model is multilingual but EN-primary.
    - Thai stop-word handling is weak. If a Thai query underperforms, the
      AI client should translate to Pāli/English first (see server
      instructions).
    - The default `limit=5` is often too small for a topic survey — use
      `limit=15-20` (max 20) for good coverage.
    - Ranking is by similarity, NOT canonical importance — locus
      classicus suttas (e.g. MN118, DN22) may rank below smaller suttas
      that happen to use the exact vocabulary. Treat results as a
      starting point, then call `get_sutta` for the canonical references.

    Args:
        query: Query text (Thai, Pāli, or English — English works best).
        language: Output language — "pali", "thai", "english", or "all".
        limit: Maximum results (default: 5, max: 20).

    Returns:
        Sutta segments ranked by descending rrf_score.
    """
    limit = min(max(1, limit), 20)
    
    if get_backend().name == "sqlite":
        return [
            {
                "error": "hybrid search is not available in local (SQLite) "
                "mode — it requires the hosted server (pgvector + an embedding "
                "model). Use search_by_keyword instead."
            }
        ]

    try:
        from embedding.model import generate_embedding
        query_embedding = generate_embedding(query)
    except Exception as e:
        return [{"error": f"Could not create embedding: {str(e)}"}]
        
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        
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
            return [{"message": "No results from hybrid search"}]
            
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
        return [{"error": f"Hybrid search error: {str(e)}"}]
    finally:
        cur.close()
        backend.release(conn)


@mcp.tool(
    annotations={
        "title": "List Tipiṭaka Structure",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def list_structure() -> dict[str, Any]:
    """Show the structure of all three pitakas with coverage statistics.

    💡 **Use this tool when:**
    - The user asks for an overview of the Tipiṭaka (what's in it / which
      collections).
    - You need to check coverage before promising a search will find
      something — `segment_count > 0` is the active-loaded signal.
    - Verifying scope when compiling an artifact.

    📊 **Current state (v1.1+, at parity with SuttaCentral bilara-data):**
    - **Sutta Piṭaka** complete: DN 37, MN 155, SN 1,829, AN 1,419, KN
      2,351 sections (~284,702 segments) — Pāli + Sujato EN
    - **Vinaya Piṭaka** complete: Bhikkhu Vibhaṅga 222, Bhikkhunī Vibhaṅga
      127, Khandhaka 22, Parivāra 51 + Pātimokkha 2 (~71,557 segments) —
      Pāli + Brahmali EN
    - **Abhidhamma Piṭaka** complete: 7 books (ds, vb, dt, pp, kv, ya,
      patthana) ~88,414 segments — Pāli only (bilara has no English for
      any Abhidhamma book)
    - **Total ~444,673 segments** in the DB

    ⚠️ **Known quirks:**
    - The schema carries duplicate legacy + SC-modern codes side by side:
      - Vinaya: `vin-v/vin-m/vin-c/vin-p` (legacy, segment_count = 0)
        alongside `pli-tv-bu-vb/pli-tv-bi-vb/pli-tv-kd/pli-tv-pvr`
        (active, populated).
      - Abhidhamma: `ym/pt` (legacy = 0) alongside `ya/patthana` (active).
    - **Use the `active` flag** — each nikaya carries `active: true/false`
      (true ⇔ `segment_count > 0`). Pick `active` nikayas; the others are
      metadata placeholders from an older migration.

    🌐 **Languages:** Returns Pāli + Thai + English labels regardless of
    enabled set (these are metadata, not segment text). Text content
    follows ENABLED_LANGUAGES. Thai translations aren't loaded yet —
    Thai users can fall back to the cross_reference 84000.org link.

    Returns:
        Hierarchical structure:
        - pitakas{vinaya/sutta/abhidhamma} → nikayas[]
        - Each nikaya: code, name (3 languages), sutta_count, segment_count.
    """
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)

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
                    # `active` = this nikaya has loaded segment text. Legacy
                    # placeholder codes (vin-v/ym/pt …) carry segment_count = 0
                    # and are NOT searchable — filter on this flag instead of
                    # re-deriving `segment_count > 0` client-side.
                    "active": row[9] > 0,
                })

        return {"pitakas": structure}

    except Exception as e:
        return {"error": f"Error: {str(e)}"}
    finally:
        cur.close()
        backend.release(conn)


@mcp.tool(
    annotations={
        "title": "Get Citation",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def get_reference(
    sutta_id: str,
) -> dict[str, Any]:
    """Build a proper citation string for a sutta.

    💡 **Use this tool when:**
    - The user wants a citation for academic work, an article, or a reference.
    - You need to know the canonical location of a sutta (pitaka / nikāya).
    - You want a ready-to-use formatted citation string.

    🔗 vs `get_sutta`: this tool returns metadata + citation only, no
    segments. Pair it with `get_sutta` when you want both the content
    and the citation.

    Args:
        sutta_id: Sutta ID, e.g. "mn1", "dn22", "sn56.11".

    Returns:
        - sutta_id, title{pali,thai,english}
        - location: nikāya + pitaka (3 languages)
        - segment_count: size of the sutta (segments)
        - citation_format: ready-to-use string, e.g. "The Root of All
          Things (Mūlapariyāyasutta, MN1), Middle Discourses"
        - cross_reference: SuttaCentral + 84000 URLs for linking in the
          citation.
    """
    try:
        sutta_id = _validate_sutta_id(sutta_id)
    except ValidationError as e:
        return {"error": str(e)}

    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)

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
            return {"error": f"Sutta not found: {sutta_id}"}

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
        return {"error": f"Error: {str(e)}"}
    finally:
        cur.close()
        backend.release(conn)


# =============================================================================
# MCP Tools — Translation Edition
# =============================================================================


@mcp.tool(
    annotations={
        "title": "List Translation Editions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def list_editions() -> list[dict[str, Any]]:
    """List the translation editions available, with coverage stats.

    💡 **Use this tool when:**
    - Before calling `compare_translations` or `get_sutta(edition=...)`,
      so you know which edition values are valid and worth comparing.
    - The user asks which editions are loaded in the DB.

    🔍 **Filtering:** Filtered by the server's `TRIPITAKA_ENABLED_LANGUAGES`
    — when Thai is disabled the list is empty. Only enabled languages
    are returned.

    ⚠️ **Current state:** the DB mostly holds Pāli (default from
    SuttaCentral bilara) and English (Sujato). Thai editions
    (`dhiranandi`, `jayasaro`, `mbu`, `royal`) aren't indexed yet — the
    list returns empty until they're loaded.

    Returns:
        List of edition objects, each containing:
        - edition: edition code, e.g. "sujato", "dhiranandi", "mbu"
        - translator: translator's name
        - language: ISO code ("pi", "en", "th")
        - segment_count: how many segments have a translation in this edition
        - sutta_count: how many suttas have a translation.
    """
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        if backend.name == "sqlite":
            # SQLite ไม่มี ANY(array) → IN (?, ?, ...) แทน
            _codes = list(ENABLED_TRANSLATION_CODES)
            _ph = ", ".join(["?"] * len(_codes))
            cur.execute(
                f"""
                SELECT
                    t.edition,
                    t.translator,
                    t.language,
                    COUNT(t.id) AS segment_count,
                    COUNT(DISTINCT sec.sutta_id) AS sutta_count
                FROM translation t
                JOIN segment seg ON t.segment_id = seg.id
                JOIN section sec ON seg.section_id = sec.id
                WHERE t.language IN ({_ph})
                GROUP BY t.edition, t.translator, t.language
                ORDER BY t.language, t.edition
                """,
                _codes,
            )
        else:
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
            return [{"message": "No additional translation editions loaded"}]

        return results

    except Exception as e:
        return [{"error": f"Error: {str(e)}"}]
    finally:
        cur.close()
        backend.release(conn)


@mcp.tool(
    annotations={
        "title": "Compare Translations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def compare_translations(
    segment_id: str,
) -> dict[str, Any]:
    """Compare every available translation for a single segment.

    💡 **Use this tool when:**
    - The user asks about the meaning/translation of a single Pāli line
      and wants to see multiple translators side-by-side.
    - Checking how different translators interpret the same line —
      technical terms like `dukkha`, `anattā`, `nibbāna` carry nuance
      that varies across translations.
    - Academic work that needs to quote multiple translations.

    🔍 **vs `get_sutta`:** this tool targets a **single segment** (line
    level); `get_sutta` returns the **whole sutta**. To compare a whole
    sutta you'd call `compare_translations` for each segment.

    📋 **segment_id format:** `<sutta_id>:<paragraph>.<line>`, e.g.
    `mn1:171.4` (Mūlapariyāyasutta paragraph 171 line 4 — "Nandī
    dukkhassa mūlaṁ"). Find segment_ids via `get_sutta` or search results.

    ⚠️ **Current state:** the `translation` table is mostly empty (the DB
    only loads default Pāli + English from bilara). `total_editions` is
    usually 0; `text_pali` and `text_english` are always populated. Thai
    editions will be added later.

    Args:
        segment_id: Segment ID, e.g. "mn26:8.2", "dn22:17.1", "mn62:5.3".

    Returns:
        - segment_id, sutta_id
        - text_pali: Pāli source (Mahāsaṅgīti)
        - text_english: Sujato translation (from bilara-data)
        - text_thai_default: bilara Thai translation (currently null —
          Thai disabled)
        - translations[]: filtered by ENABLED_LANGUAGES — list of
          {edition, translator, language, text}
        - total_editions: count of active editions
        - cross_reference: SuttaCentral segment-level deep link
          (important — jumps straight to the segment in the SC viewer).
    """
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)

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
            return {"error": f"Segment not found: {segment_id}"}

        seg_db_id, seg_id, sutta_id, text_pali, text_thai_default, text_english = row

        # ดึงคำแปลจาก translation table — กรองเฉพาะภาษาที่เปิดใช้งาน
        if backend.name == "sqlite":
            # SQLite ไม่มี ANY(array) → IN (?, ?, ...) แทน
            _codes = list(ENABLED_TRANSLATION_CODES)
            _ph = ", ".join(["?"] * len(_codes))
            cur.execute(
                f"""
                SELECT edition, translator, language, text
                FROM translation
                WHERE segment_id = ? AND language IN ({_ph})
                ORDER BY language, edition
                """,
                [seg_db_id, *_codes],
            )
        else:
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
        return {"error": f"Error: {str(e)}"}
    finally:
        cur.close()
        backend.release(conn)


@mcp.tool(
    annotations={
        "title": "Get Word Definition",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def get_word_definition(word: str, language: Literal["en", "thai", "th", "all"] = "all", limit_context: int = 3) -> dict[str, Any]:
    """Look up the dictionary meaning of a Pāli word, with sutta context.

    Serves as a Pāli Dictionary Bridge — pairs the "definition" with the
    "context where the Buddha actually used the word".

    📖 **About the dictionary sources:**
    This tool draws from multiple primary dictionaries, including
    "พจนานุกรมพุทธศาสน์ ฉบับประมวลศัพท์" (Buddhist Dictionary —
    Concept-Glossary edition) by Somdet Phra Buddhaghosacariya (P. A.
    Payutto). The Thai-language entries are **original scholarly works**
    (not translations), so they are **always available** even when
    ENABLED_LANGUAGES has Thai disabled. The AI client should translate
    Thai entries into the user's language if needed.

    Args:
        word: Word to look up (e.g. "dukkha", "กฐิน").
        language: Dictionary language (e.g. "en", "thai", or "all" as
                  default).
        limit_context: Number of sutta-context examples to include (1-5).

    Returns:
        Dictionary entries from SuttaCentral/Payutto plus context
        examples showing how the word is used in segments.
    """
    word_search = word.lower().strip()
    limit_context = min(max(1, limit_context), 5)
    
    backend = get_backend()
    conn = backend.connect()
    try:
        cur = backend.cursor(conn)
        
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
                    "note": f"No exact match for '{word}'; here are similar words:",
                    "suggestions": definitions
                }
            return {"error": f"Word '{word}' not found in dictionary"}
            
        # 2. Fetch context from segment where text_pali contains the word
        # ใช้ ROW_NUMBER() + PARTITION BY เพื่อให้ดึงแค่ 1 ตัวอย่างต่อพระสูตร 
        # และ ORDER BY random() เพื่อสุ่มความหลากหลายของนิกาย
        if backend.name == "sqlite":
            # SQLite: ~* word-boundary regex → FTS5 MATCH (token-level = word match)
            _match = 'text_pali : "' + word_search.replace('"', '""') + '"'
            cur.execute(
                """
                WITH matched AS (
                    SELECT sec.sutta_id, seg.segment_id, seg.text_pali, seg.text_english, seg.text_thai,
                           ROW_NUMBER() OVER (PARTITION BY sec.sutta_id ORDER BY random()) as rn
                    FROM segment_fts
                    JOIN segment seg ON seg.id = segment_fts.rowid
                    JOIN section sec ON seg.section_id = sec.id
                    WHERE segment_fts MATCH ?
                )
                SELECT sutta_id, segment_id, text_pali, text_english, text_thai
                FROM matched
                WHERE rn = 1
                ORDER BY random()
                LIMIT ?
                """,
                (_match, limit_context),
            )
        else:
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
        return {"error": f"Error: {str(e)}"}
    finally:
        cur.close()
        backend.release(conn)


@mcp.tool(
    annotations={
        "title": "Parse Pāli Word",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def parse_pali_word(word: str) -> dict[str, Any]:
    """Strip Pāli inflectional suffixes to find the root form (basic stem).

    💡 **Use this tool when:**
    - You find an inflected Pāli word (e.g. `dukkhassa`, `bhikkhūnaṁ`) and
      `get_word_definition` doesn't find it directly — Pāli inflects nouns
      across 7 cases × 2 numbers, ~16 forms per root.
    - You want to split a compound (`sammāsambuddhassa` → `sammā` +
      `sambuddha` + `-ssa` genitive).
    - You want to see possible stems before another `get_word_definition`
      lookup.

    🔄 **Recommended workflow:**
    `parse_pali_word(inflected_form)` → get `possible_stems[]` →
    call `get_word_definition(stem)` per stem until you find a definition.

    ⚠️ **Limitations:**
    - Rule-based first-pass — strips common suffixes (case endings, vowel
      shortening). Not a full morphological analyzer.
    - Compound words (samāsa) are NOT split — `dukkhanirodha` won't be
      broken into `dukkha` + `nirodha`.
    - Sandhi (sound junctions) like `tena ahaṁ → tenāhaṁ` aren't reversed.
    - Returns **possible** stems — verify each via `get_word_definition`.

    Args:
        word: An inflected Pāli word (e.g. "dukkhassa", "bhikkhūnaṁ",
              "sīlavā").

    Returns:
        - original_word: normalised input
        - matched_suffixes_removed: list of stripped suffixes
        - possible_stems: candidate root forms
        - guidance: next-step workflow hint.
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
