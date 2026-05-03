# The Pāli Canon (Tipiṭaka) — Structure & Coverage

The Pāli Canon is the scriptural foundation of Theravāda Buddhism, composed in the Pāli language and traditionally divided into three "baskets" (*piṭaka*). This page summarises the structure of the canon, lists the books in each basket, and shows what content is currently loaded in this MCP server.

> Server data source: SuttaCentral [bilara-data](https://github.com/suttacentral/bilara-data) (CC0). Counts below are live as of the last data refresh — call the MCP tool `list_structure` for current numbers.

## The three piṭakas

All three piṭakas are at parity with SuttaCentral bilara-data as of v1.1.0 — ~444,673 segments total.

| Piṭaka | Pāli | Thai | English | Coverage in this server |
| --- | --- | --- | --- | --- |
| Sutta | Suttantapiṭaka | สุตตันตปิฎก | Basket of Discourses | full (Pāli + Sujato EN) |
| Vinaya | Vinayapiṭaka | วินัยปิฎก | Basket of Discipline | full (Pāli + Brahmali EN) |
| Abhidhamma | Abhidhammapiṭaka | อภิธรรมปิฎก | Basket of Higher Teaching | full Pāli (no English in bilara-data for any translator) |

## Sutta Piṭaka — fully indexed (~284K segments)

The Sutta Piṭaka contains the discourses of the Buddha, organised into five collections (*nikāya*). All five are loaded with full Pāli text and Bhikkhu Sujato's English translation.

| Code | Pāli | Thai | English | Suttas | Segments |
| --- | --- | --- | --- | --- | ---: |
| `dn` | Dīghanikāya | ทีฆนิกาย | Long Discourses | 37 | 16,401 |
| `mn` | Majjhimanikāya | มัชฌิมนิกาย | Middle Discourses | 155 | 27,195 |
| `sn` | Saṁyuttanikāya | สังยุตตนิกาย | Connected Discourses | 1,829 | 43,466 |
| `an` | Aṅguttaranikāya | อังคุตตรนิกาย | Numerical Discourses | 1,419 | 41,839 |
| `kn` | Khuddakanikāya | ขุททกนิกาย | Minor Collection | 2,351 | 155,801 |
| **total** | | | | **5,791** | **284,702** |

### Khuddakanikāya — 20 sub-books

The KN includes Dhammapada, Udāna, Itivuttaka, Suttanipāta, Theragāthā, Therīgāthā, Jātaka, Niddesa, Paṭisambhidāmagga, Buddhavaṁsa, Cariyāpiṭaka, and the paracanonical Milindapañha. All sub-books are accessible via their SuttaCentral IDs (`dhp1-20`, `snp1.8`, `thag1.1`, `ja1`, `mil3.1.1`, etc.).

## Vinaya Piṭaka — fully indexed (~71K segments)

All four canonical sub-collections are loaded with Pāli + Bhikkhu Brahmali's English translation, plus both Pātimokkhas. Use the SuttaCentral codes for lookups (`pli-tv-bu-vb-pj1` for Pārājika 1, `pli-tv-kd1` for Mahāvagga ch. 1, etc.).

| Code | Pāli | Thai | English | Sections | Segments |
| --- | --- | --- | --- | --- | ---: |
| `pli-tv-bu-vb` | Bhikkhuvibhaṅga | ภิกขุวิภังค์ | Bhikkhu Vibhaṅga (227 rules) | 222 | 21,890 |
| `pli-tv-bi-vb` | Bhikkhunīvibhaṅga | ภิกขุนีวิภังค์ | Bhikkhunī Vibhaṅga (311 rules) | 127 | 7,652 |
| `pli-tv-kd` | Khandhaka | ขันธกะ | Mahāvagga + Cullavagga | 22 | 29,212 |
| `pli-tv-pvr` | Parivāra | ปริวาร | The Compendium | 51 | 12,803 |
| **total** | | | | **422** | **71,557** |

> Legacy codes `vin-v`, `vin-m`, `vin-c`, `vin-p` from the older schema co-exist with `segment_count = 0`. Always pick the `pli-tv-*` code with non-zero segments.

## Abhidhamma Piṭaka — fully indexed in Pāli (~88K segments)

All seven canonical books are loaded with Pāli text. SuttaCentral's bilara-data has no English translation for any Abhidhamma book across any translator (Sujato, Brahmali, etc. all empty under `abhidhamma/`), so this server is Pāli-only here — matching the upstream, not a coverage gap.

| Code | Pāli | Thai | English | Sections | Segments |
| --- | --- | --- | --- | --- | ---: |
| `ds` | Dhammasaṅgaṇī | ธัมมสังคณี | Enumeration of Phenomena | 21 | 7,777 |
| `vb` | Vibhaṅga | วิภังค์ | Book of Analysis | 18 | 12,625 |
| `dt` | Dhātukathā | ธาตุกถา | Discussion of Elements | 19 | 3,001 |
| `pp` | Puggalapaññatti | ปุคคลบัญญัติ | Designation of Persons | 20 | 1,841 |
| `kv` | Kathāvatthu | กถาวัตถุ | Points of Controversy | 225 | 19,619 |
| `ya` | Yamaka | ยมก | Book of Pairs | 77 | 14,382 |
| `patthana` | Paṭṭhāna | ปัฏฐาน | Book of Conditional Relations | 728 | 29,169 |
| **total** | | | | **1,108** | **88,414** |

> Legacy codes `ym`, `pt` co-exist with `segment_count = 0`. Use `ya` and `patthana`.

## How to fetch content

- Full sutta: `get_sutta(sutta_id="mn1", language="all")`
- Survey by topic: `search_hybrid(query="mindfulness of breathing", limit=20)`
- Exact term: `search_by_keyword(keyword="ānāpānassati", language="pali", limit=20)`
- Citation: `get_reference(sutta_id="dn22")`
- Live structure (this page's source data): `list_structure()`

For details on which tool to pick, see the [tipitaka-research](../skills/tipitaka-research.md) skill that ships with this server.

## External references

For canonical content beyond what this server exposes:

- **SuttaCentral** ([suttacentral.net](https://suttacentral.net)) — full Pāli + multilingual translations, primary source for this server's data
- **84000.org** — ฉบับมหาจุฬาฯ (45-volume Thai canonical edition)
- **DPPN** ([Dictionary of Pāli Proper Names](https://www.palikanon.com/english/pali_names/dic_idx.html)) — Malalasekera's reference for places, people, and concepts mentioned across the canon
- **PTS** ([palitext.com](https://palitext.com)) — Pāli Text Society, Roman-script editions and dictionaries
