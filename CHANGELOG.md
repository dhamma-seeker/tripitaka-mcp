# Changelog

All notable changes to Tripitaka MCP are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `define_from_suttas` now finds similes that never name the term. The four jhāna
  similes (bath powder, deep lake, lotus pond, white cloth) contain no word for
  *jhāna*: they illustrate the `vivicceva kāmehi …` formula that opens the
  paragraph. Such a simile is returned when its paragraph holds a complete
  `seyyathāpi … evameva` pair and the paragraph's opening line carries the term.
  Results are tagged `context: true` and the embed says plainly that the term is
  not in the quoted line. Two reserved slots at most, so they cannot crowd out a
  real definition. Measured over the corpus: jhāna 26 similes, kāya 21,
  dukkha 21, citta 14, sati 8, magga 2, taṇhā and nibbāna none.
  Reported by [Dhamma.Gift](https://github.com/dhammagift).

### Fixed
- `define_from_suttas` counted a term as defined when it merely appeared beside a
  definitional formula. In `ariyassa vinaye vuccanti` ("in the training of the
  Noble One they are called…") the word *vinaya* is a locative setting the scene,
  and the thing being defined is elsewhere in the sentence; likewise *sīla* in
  `ayaṁ vuccati puggalo sīlesu ca paripūrakārī`, which defines the person, not
  virtue. A term that appears only in the locative, instrumental or ablative is no
  longer treated as the subject of a definition. Nominative subjects and the
  genitive that `adhivacana` governs (`kāyassa adhivacanaṁ`) are unaffected.
  Reported by [Dhamma.Gift](https://github.com/dhammagift).
- The interrogative marker `katama-` ("which?") also matched `kataṁ` ("done"),
  which occurs in 10,915 segments. A lookup of *sāsana* returned four verses of
  `kataṁ buddhassa sāsanaṁ` ("the Buddha's instruction has been carried out"),
  none of which define anything.
- Results were ordered by whatever sequence the database returned, so a term whose
  top matches tied on score could resolve to different suttas under PostgreSQL and
  SQLite. Ranking and duplicate-collapsing now break ties on citation.
- Sutta titles were read from segment `:0.2`, which is the sutta's name only in
  the Dīgha and Majjhima. Elsewhere that slot holds the chapter or book, so
  SN 35.245 was titled "19. Āsīvisavagga" instead of "Kiṁsukopamasutta", and
  Iti 44 was titled "Dukanipāta". The heading segments run collection → book →
  chapter → sutta, so the title is the last of them. This affected 3,315 texts
  across SN, AN, Itivuttaka and the Dhammapada, in `get_sutta`, the citation
  string built by `get_reference`, and every reader page.
  Reported by [Dhamma.Gift](https://github.com/dhammagift), who asked for Pāli
  names in the embed and prompted the check that found it.

## 2026-07-31

### Added
- New tool `define_from_suttas`: surfaces how the suttas and Vinaya define a Pāli
  term in their own words, detecting canonical formulas such as "Katamañca X?" ...
  "ayaṁ vuccati X", "X adhivacana", and the Vinaya "X nāma" pattern. The detection
  patterns were contributed by [Dhamma.Gift](https://github.com/dhammagift), shared in
  [GitHub issue #4](https://github.com/dhamma-seeker/tripitaka-mcp/issues/4).
  Thank you!
