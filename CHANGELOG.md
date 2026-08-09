# Changelog

All notable changes to Tripitaka MCP are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
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
