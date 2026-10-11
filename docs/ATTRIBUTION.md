# ATTRIBUTION.md — Fixture clips & voices (must be filled before committing audio)

No audio is committed as of 2026-10-11 (Phase 0). Before any `.wav` is added:

1. Use only clips whose license permits redistribution (e.g. CC0, CC-BY with attribution,
   self-recorded with a signed note), or
2. Ship `scripts/download_fixtures.sh` instead of committing audio.

## Voice allowlist (TTS)

| Voice file | Source | License (from MODEL_CARD) | Hash (sha256) | Attribution text |
|---|---|---|---|---|
| `en_US-libritts-high` (to be pinned in Phase 4 setup) | https://huggingface.co/rhasspy/piper-voices | CC-BY 4.0 (verify MODEL_CARD at download) | `TODO` | `TODO: copy MODEL_CARD attribution` |

## Fixture clips (detector tests / eval)

| File | Species | Source URL | License | Recordist / credit | Verified on |
|---|---|---|---|---|---|
| _no committed audio_ — test fixture is `sample.wav` shipped inside the `birdnet-analyzer` 2.4.0 PyPI package (`checkpoints/V2.4/.../static/sample.wav`), used in place, never copied into the repo | Lesser Redpoll (model top-1, 0.94) | n/a (ships with https://github.com/birdnet-team/BirdNET-Analyzer) | Same terms as BirdNET weights (CC BY-NC-SA 4.0); used locally only, not redistributed | BirdNET team (packaged test file) | 2026-10-11 |

## Rules
- Every row needs source URL + license + date verified.
- BirdNET weights (CC BY-NC-SA 4.0) and Perch weights are NOT redistributed — fetched once by
  `make setup`, never committed.
