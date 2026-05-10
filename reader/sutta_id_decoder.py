"""Best-effort decoder of SuttaCentral-style sutta_ids into human-readable text.

Used for hover tooltips on every `code.sid` element in the reader, and for
the "How IDs work" help block on /read/. The point is pedagogical — newcomers
who never learned the canonical ID system gradually internalise it through
repeated exposure to decoded forms in tooltips.

Coverage targets the active IDs in our DB:
    Sutta:      dn{N}, mn{N}, sn{X}.{Y}, an{X}.{Y}, dhp{N}-{M}, snp{X}.{Y}, …
    Vinaya:     pli-tv-bu-pm, pli-tv-bu-vb-pj{N}, pli-tv-kd{N}, pli-tv-pvr{N}, …
    Abhidhamma: ds{X}.{Y}, vb{N}, dt{X}.{Y}, kv{X}.{Y}, ya{X}.{Y}.{Z}, …
    Paracanonical: mil{X}.{Y}.{Z}

Decoder is best-effort. Unknown patterns return the input unchanged so the
tooltip is harmless on data we don't recognise. Add new mappings as the
canon coverage grows.
"""

from __future__ import annotations

import re

# --- Top-level nikāya / book prefixes ---------------------------------------
# Order matters for prefix matching: longer keys are tried first via len-sort.

NIKAYA_NAMES: dict[str, str] = {
    # Sutta Piṭaka
    "dn": "Dīgha Nikāya",
    "mn": "Majjhima Nikāya",
    "sn": "Saṁyutta Nikāya",
    "an": "Aṅguttara Nikāya",
    # Khuddaka Nikāya (sub-books)
    "kp": "Khuddakapāṭha",
    "dhp": "Dhammapada",
    "ud": "Udāna",
    "iti": "Itivuttaka",
    "snp": "Sutta Nipāta",
    "vv": "Vimānavatthu",
    "pv": "Petavatthu",
    "thag": "Theragāthā",
    "thig": "Therīgāthā",
    "tha-ap": "Therāpadāna",
    "thi-ap": "Therīapādāna",
    "bv": "Buddhavaṁsa",
    "cp": "Cariyāpiṭaka",
    "ja": "Jātaka",
    "ne": "Nettippakaraṇa",
    "pe": "Peṭakopadesa",
    "mil": "Milindapañha",
    # Abhidhamma Piṭaka
    "ds": "Dhammasaṅgaṇī",
    "vb": "Vibhaṅga",
    "dt": "Dhātukathā",
    "pp": "Puggalapaññatti",
    "kv": "Kathāvatthu",
    "ya": "Yamaka",
    "patthana": "Paṭṭhāna",
}

# How to label a single trailing number per top-level prefix:
#   "verse" — KN poetic books where each number is a stanza
#   "story" — Jātaka tales
#   "ch."   — Abhidhamma books, organised by chapter
#   default → "sutta" (DN/MN/Vibhaṅga-of-an-pre-2-level/etc.)
SINGLE_NUMBER_LABEL: dict[str, str] = {
    "dhp": "verse", "thag": "verse", "thig": "verse",
    "ud": "verse", "iti": "verse", "snp": "sutta",
    "kp": "passage", "vv": "verse", "pv": "verse",
    "bv": "section", "cp": "section",
    "ja": "story",
    "ds": "ch.", "vb": "ch.", "dt": "ch.", "pp": "ch.",
    "kv": "ch.", "ya": "ch.", "patthana": "ch.",
}

# Two-part numbering label per top nikāya.
# e.g. sn56.11 = Saṁyutta 56, sutta 11
DOT_LABELS: dict[str, tuple[str, str]] = {
    "sn": ("saṁyutta", "sutta"),
    "an": ("nipāta", "sutta"),
    "snp": ("vagga", "sutta"),
    "ud": ("vagga", "sutta"),
    "iti": ("vagga", "sutta"),
    "thag": ("nipāta", "verse"),
    "thig": ("nipāta", "verse"),
    "ja": ("nipāta", "story"),
    "mil": ("vagga", "section"),
    "ds": ("section", "subsection"),
    "dt": ("section", "subsection"),
    "kv": ("kathā", "subsection"),
    "ya": ("section", "subsection"),
    "patthana": ("section", "subsection"),
    "pp": ("section", "subsection"),
}

# --- Vinaya component glossary (pli-tv-…) -----------------------------------

VINAYA_COMPONENTS: dict[str, str] = {
    "pli": "Pāli",
    "tv": "Theravāda",
    "bu": "Bhikkhu",
    "bi": "Bhikkhunī",
    "vb": "Vibhaṅga",
    "kd": "Khandhaka",
    "pvr": "Parivāra",
    "pm": "Pātimokkha",
    "pj": "Pārājika",
    "ss": "Saṅghādisesa",
    "ay": "Aniyata",
    "np": "Nissaggiya Pācittiya",
    "pc": "Pācittiya",
    "pd": "Pāṭidesanīya",
    "sk": "Sekhiya",
    "as": "Adhikaraṇasamatha",
}

# --- Public API -------------------------------------------------------------


def decode_sutta_id(sid: str | None) -> str:
    """Decode a sutta_id into a single-line human-readable expansion.

    Examples:
        sn56.11             → "Saṁyutta Nikāya · saṁyutta 56, sutta 11"
        dn22                → "Dīgha Nikāya · sutta 22"
        dhp1-20             → "Dhammapada · verses 1–20"
        pli-tv-bu-pm        → "Vinaya · Pāli · Theravāda · Bhikkhu · Pātimokkha"
        pli-tv-bu-vb-pj1    → "Vinaya · Pāli · Theravāda · Bhikkhu · Vibhaṅga · Pārājika 1"
        mil3.1.1            → "Milindapañha · 3.1.1"
        patthana1.1         → "Paṭṭhāna · section 1, subsection 1"

    Falls back to the raw sid if the pattern is unrecognised, so the tooltip
    never shows misleading text.
    """
    if not sid:
        return ""
    s = sid.strip().lower()

    if s.startswith("pli-tv-"):
        return _decode_vinaya(s)

    # Try matching a known nikāya prefix; longest match wins so e.g. "tha-ap"
    # is preferred over "th" or "thag".
    for prefix in sorted(NIKAYA_NAMES.keys(), key=len, reverse=True):
        if s == prefix:
            return NIKAYA_NAMES[prefix]
        if s.startswith(prefix):
            rest = s[len(prefix):]
            # Accept only if `rest` is digits/dots/hyphens (a number suffix).
            if re.fullmatch(r"[\d.\-]+", rest):
                return _format_with_numbers(NIKAYA_NAMES[prefix], prefix, rest)

    return sid  # unrecognised — leave alone


# --- Internals --------------------------------------------------------------


def _format_with_numbers(nikaya: str, prefix: str, nums: str) -> str:
    # Range form: "1-20" → verses 1–20
    rng = re.fullmatch(r"(\d+)-(\d+)", nums)
    if rng:
        return f"{nikaya} · verses {rng.group(1)}–{rng.group(2)}"

    parts = nums.split(".")

    if len(parts) == 1 and parts[0].isdigit():
        kind = SINGLE_NUMBER_LABEL.get(prefix, "sutta")
        return f"{nikaya} · {kind} {parts[0]}"

    if len(parts) == 2 and all(p.isdigit() for p in parts):
        a, b = parts
        labels = DOT_LABELS.get(prefix)
        if labels:
            return f"{nikaya} · {labels[0]} {a}, {labels[1]} {b}"
        return f"{nikaya} · {a}.{b}"

    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{nikaya} · {'.'.join(parts)}"

    return f"{nikaya} · {nums}"


def _decode_vinaya(sid: str) -> str:
    """pli-tv-bu-pm → 'Vinaya · Pāli · Theravāda · Bhikkhu · Pātimokkha'.

    Strategy: walk the dash-separated parts left to right, replacing each
    component with its glossary name. A trailing component with a digit
    suffix (e.g. 'pj1', 'kd10', 'pvr10') is split: the alpha part is named,
    the number kept as-is.
    """
    parts = sid.split("-")
    out = ["Vinaya"]
    for p in parts:
        if not p:
            continue
        m = re.fullmatch(r"([a-z]+)(\d+)", p)
        if m:
            alpha, num = m.group(1), m.group(2)
            name = VINAYA_COMPONENTS.get(alpha)
            out.append(f"{name} {num}" if name else f"{alpha} {num}")
        else:
            out.append(VINAYA_COMPONENTS.get(p, p))
    return " · ".join(out)
