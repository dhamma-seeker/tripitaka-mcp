"""Curated list of suttas surfaced on the /read/ landing page.

Edit this file to add/remove featured entries. Each item must have a
sutta_id that exists in the DB (segment_count > 0); the template doesn't
verify on render, so a typo here surfaces as a 404 only when a user clicks.

Categories are rendered in declaration order. Keep the total under ~12
items to avoid burying the existing browse tree below.

`title_pali` / `title_en` are **the text's own words, not ours**: each one is
the last heading segment (`:0.<n>`) of that sutta, which is the rule the
reader itself uses to title a page (`sutta_titles.last_heading`). Copy them
from the DB, don't compose them — a card and the page it opens have to show
the same name, or the reader looks like it renamed the sutta. Where a sutta
is widely known under another title, that name belongs in the blurb, said to
be a traditional title, never in the title fields.

`blurb` is our own prose. It may describe, but every count and claim in it
has to hold against the text, and it never appraises a translation, a
teacher, or anyone's work.
"""

FEATURED_SUTTAS: list[dict] = [
    {
        "category": "Start here",
        "emoji": "🌱",
        "items": [
            {
                "sutta_id": "sn56.11",
                "title_pali": "Dhammacakkappavattanasutta",
                "title_en": "Rolling Forth the Wheel of Dhamma",
                "blurb": "Traditionally counted as the first discourse — the four noble truths, with the noble eightfold path spelled out inside the fourth.",
            },
            # The one card that does not use the last heading. For `dhp1-20`
            # that heading is `dhp1:0.4 = Cakkhupālattheravatthu`, a story
            # title of the commentary layer that sits in bilara's root file
            # and that the translator left untranslated (the English file goes
            # :0.1, :0.2, :0.3, then straight to :1). The line above it,
            # `dhp1:0.3 = Yamakavagga / "1. Pairs"`, is the chapter this card
            # actually opens, so that is the name shown here — minus the "1."
            # numbering. The heading rule mis-titles the whole Dhammapada;
            # fixing it is a separate task, not this file's business.
            {
                "sutta_id": "dhp1-20",
                "title_pali": "Yamakavagga",
                "title_en": "Pairs",
                "blurb": "The Dhammapada's opening chapter — twenty verses in contrasting pairs on intention, on hatred and how it is laid to rest, and on reciting the teaching versus living it.",
            },
            {
                "sutta_id": "mn10",
                "title_pali": "Satipaṭṭhānasutta",
                "title_en": "Mindfulness Meditation",
                "blurb": "The four kinds of mindfulness meditation set out in full, and shorter than DN 22 — 235 segments against 454.",
            },
            {
                "sutta_id": "sn22.59",
                "title_pali": "Anattalakkhaṇasutta",
                "title_en": "The Characteristic of Not-Self",
                "blurb": "The five aggregates examined as not-self; by the end the group of five mendicants are freed of defilements. Traditionally counted as the second discourse.",
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
                "title_en": "The Great Discourse on the Buddha’s Extinguishment",
                "blurb": "The longest discourse in the four nikāyas at 1,664 segments — the final journey, the final instructions, the parinibbāna.",
            },
            {
                "sutta_id": "mn26",
                "title_pali": "Pāsarāsisutta",
                "title_en": "The Noble Quest",
                "blurb": "Autobiographical — the going forth, the search, the awakening, then the group of five mendicants won over in the deer park at Isipatana. Traditional title: Ariyapariyesanāsutta.",
            },
            {
                "sutta_id": "mn128",
                "title_pali": "Upakkilesasutta",
                "title_en": "Corruptions",
                "blurb": "After the quarrel at Kosambī the Buddha leaves town reciting verses on wandering alone, and later tells Anuruddha the eleven corruptions of the mind he gave up himself.",
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
                "title_en": "The Longer Discourse on Mindfulness Meditation",
                "blurb": "Extended satipaṭṭhāna, with a full exposition of the four noble truths inside the dhammānupassanā section.",
            },
            {
                "sutta_id": "mn118",
                "title_pali": "Ānāpānassatisutta",
                "title_en": "Mindfulness of Breathing",
                "blurb": "Sixteen steps of breath meditation, in four sets of four — and how they fulfil the four kinds of mindfulness meditation.",
            },
            {
                "sutta_id": "snp1.8",
                "title_pali": "Mettasutta",
                "title_en": "The Discourse on Love",
                "blurb": "The classic mettā chant — the conduct asked of one who would reach peace, then love spread over the whole world. Traditional title: Karaṇīyamettasutta.",
            },
        ],
    },
    {
        "category": "Foundations",
        "emoji": "💎",
        "items": [
            {
                "sutta_id": "an3.65",
                "title_pali": "Kesamuttisutta",
                "title_en": "With the Kālāmas of Kesamutta",
                "blurb": "Don't go by oral transmission, lineage, scripture, logic, or “the ascetic is our teacher” — know for yourself whether a thing leads to harm or to welfare. Traditional title: Kālāmasutta.",
            },
            {
                "sutta_id": "sn12.2",
                "title_pali": "Vibhaṅgasutta",
                "title_en": "Analysis",
                "blurb": "The twelve links of dependent origination, each one defined in turn, from ignorance down to old age and death.",
            },
        ],
    },
]
