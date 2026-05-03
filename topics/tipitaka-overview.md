# The Pāli Canon (Tipiṭaka) — Structure & Coverage

The Pāli Canon is the scriptural foundation of Theravāda Buddhism, composed in the Pāli language and traditionally divided into three "baskets" (*piṭaka*). This page summarises the structure of the canon, lists the books in each basket, and shows what content is currently loaded in this MCP server.

> Server data source: SuttaCentral [bilara-data](https://github.com/suttacentral/bilara-data) (CC0). Counts below are live as of the last data refresh — call the MCP tool `list_structure` for current numbers.

## The three piṭakas

| Piṭaka | Pāli | Thai | English | Coverage in this server |
| --- | --- | --- | --- | --- |
| Vinaya | Vinayapiṭaka | วินัยปิฎก | Basket of Discipline | partial |
| Sutta | Suttantapiṭaka | สุตตันตปิฎก | Basket of Discourses | full |
| Abhidhamma | Abhidhammapiṭaka | อภิธรรมปิฎก | Basket of Higher Teaching | partial |

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

## Vinaya Piṭaka — partial (754 segments)

| Code | Pāli | Thai | English | Suttas | Segments |
| --- | --- | --- | --- | --- | ---: |
| `vin-v` | Vibhaṅga | ภิกขุวิภังค์/ภิกขุนีวิภังค์ | Vibhanga | 16 | 754 |
| `vin-m` | Mahāvagga | มหาวรรค | Mahāvagga | 5 | (metadata only) |
| `vin-c` | Cullavagga | จุลวรรค | Cullavagga | 20 | (metadata only) |
| (Bhikkhu / Bhikkhunī Vibhaṅga, Khandhaka, Parivāra) | | | | | (planned) |

The Vibhaṅga contains the analysis of the prātimokṣa rules. The remaining sub-collections — Mahāvagga, Cullavagga, Khandhaka, Parivāra — have metadata seeded but no segment text yet. Loading these is tracked as Phase B.

## Abhidhamma Piṭaka — partial (421 segments)

| Code | Pāli | Thai | English | Suttas | Segments |
| --- | --- | --- | --- | --- | ---: |
| `kv` | Kathāvatthu | กถาวัตถุ | Points of Controversy | 9 | 421 |
| (Dhammasaṅgaṇī, Vibhaṅga, Dhātukathā, Puggalapaññatti, Yamaka, Paṭṭhāna) | | | | | (planned) |

The Abhidhamma's seven canonical books are scholastic in style and require specialised parsing. Only Kathāvatthu is currently loaded; the others are tracked as Phase C.

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
