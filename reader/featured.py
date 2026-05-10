"""Curated list of suttas surfaced on the /read/ landing page.

Edit this file to add/remove featured entries. Each item must have a
sutta_id that exists in the DB (segment_count > 0); the template doesn't
verify on render, so a typo here surfaces as a 404 only when a user clicks.

Categories are rendered in declaration order. Keep the total under ~12
items to avoid burying the existing browse tree below.
"""

FEATURED_SUTTAS: list[dict] = [
    {
        "category": "Start here",
        "emoji": "🌱",
        "items": [
            {
                "sutta_id": "sn56.11",
                "title_pali": "Dhammacakkappavattana",
                "title_en": "Setting the Wheel of Dhamma in Motion",
                "blurb": "The Buddha's first sermon — the Four Noble Truths and the Noble Eightfold Path.",
            },
            {
                "sutta_id": "dhp1-20",
                "title_pali": "Yamakavagga",
                "title_en": "Pairs",
                "blurb": "Opening verses of the Dhammapada — paired and contrasting teachings on mind, anger, and mindfulness.",
            },
            {
                "sutta_id": "mn10",
                "title_pali": "Satipaṭṭhānasutta",
                "title_en": "Mindfulness Meditation",
                "blurb": "The foundation text on the four establishments of mindfulness — more concise than DN 22.",
            },
            {
                "sutta_id": "sn22.59",
                "title_pali": "Anattalakkhaṇa",
                "title_en": "The Characteristic of Not-Self",
                "blurb": "The second sermon — the five aggregates as not-self, the awakening of the first five disciples.",
            },
        ],
    },
    {
        "category": "Pivotal moments",
        "emoji": "📜",
        "items": [
            {
                "sutta_id": "dn16",
                "title_pali": "Mahāparinibbānasutta",
                "title_en": "The Buddha's Last Days",
                "blurb": "The longest sutta in the canon — final journey, final discourses, parinibbāna.",
            },
            {
                "sutta_id": "mn26",
                "title_pali": "Ariyapariyesanāsutta",
                "title_en": "The Noble Search",
                "blurb": "Autobiographical — the Buddha's quest for awakening, from his renunciation to his first teaching.",
            },
            {
                "sutta_id": "mn128",
                "title_pali": "Upakkilesasutta",
                "title_en": "Corruptions",
                "blurb": "After the Kosambī dispute the Buddha leaves alone, then explains eleven corruptions of meditation to Anuruddha.",
            },
        ],
    },
    {
        "category": "Practice",
        "emoji": "🧘",
        "items": [
            {
                "sutta_id": "dn22",
                "title_pali": "Mahāsatipaṭṭhānasutta",
                "title_en": "The Longer Discourse on Mindfulness",
                "blurb": "Extended satipaṭṭhāna with a full exposition of the Four Noble Truths in the dhammānupassanā section.",
            },
            {
                "sutta_id": "mn118",
                "title_pali": "Ānāpānassatisutta",
                "title_en": "Mindfulness of Breathing",
                "blurb": "Sixteen-step breath meditation framework — how the four foundations of mindfulness are fulfilled.",
            },
            {
                "sutta_id": "snp1.8",
                "title_pali": "Karaṇīyamettasutta",
                "title_en": "The Hymn of Universal Love",
                "blurb": "The classic mettā chant — qualities of one skilled in good and the boundless radiation of love.",
            },
        ],
    },
    {
        "category": "Foundations",
        "emoji": "💎",
        "items": [
            {
                "sutta_id": "an3.65",
                "title_pali": "Kālāmasutta",
                "title_en": "To the Kālāmas",
                "blurb": "On rational belief — do not accept teachings merely from tradition, scripture, or the authority of a teacher.",
            },
            {
                "sutta_id": "sn12.2",
                "title_pali": "Paṭiccasamuppāda-vibhaṅga",
                "title_en": "Analysis of Dependent Origination",
                "blurb": "Each link of the twelvefold chain of dependent origination defined in detail.",
            },
        ],
    },
]
