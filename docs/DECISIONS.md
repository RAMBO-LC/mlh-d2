# DECISIONS.md — Field Notes (append-only log)

Format: `## YYYY-MM-DD — N. Title` + Context / Decision / Consequences.
Choose, document, continue. Only ask the user when genuinely blocked.

## 2026-10-11 — 1. Default bird backend = BirdNET-Analyzer (NC weights accepted for hackathon)
- Context: BirdNET code is MIT but weights are CC BY-NC-SA 4.0 (LICENSES.md). Perch code is
  Apache-2.0 but weights terms unverified (Kaggle captcha on 2026-10-11).
- Decision: Default to BirdNET for location/week filtering; implement `detect/base.py` interface
  so Perch is a config-only swap (stub in Phase 2, full backend STRETCH).
- Consequences: Submission must say "open-source code + open-weight non-commercial model",
  never "fully open-source". Phase 9 swap demo re-verifies Perch weights terms first.

## 2026-10-11 — 2. Default journal LLM = Qwen3:4b via Ollama
- Context: Qwen3 weights Apache-2.0 (most permissive); Gemma 3 custom Terms with flow-down +
  termination; Llama custom Community License with 700M cap + attribution; Gemma 4 Apache-2.0
  but less widely available in Ollama tags at plan time.
- Decision: Default `qwen3:4b`; `gemma3:4b` / Gemma 4 / Llama swappable via `config.yaml` only.
- Consequences: Default path stays under OSI-approved terms. Journal prompt + hallucination guard
  are model-agnostic (Phase 6 tests mock the LLM).

## 2026-10-11 — 3. TTS = legacy Piper (MIT) + allowlisted libritts-high voice
- Context: `rhasspy/piper` is MIT but archived (2025-10-06); successor `OHF-Voice/piper1-gpl` is
  GPL-3.0 copyleft. Voices are per-voice licensed; libritts-high is CC-BY 4.0 (attribution).
- Decision: Pin legacy `piper-tts` binary + `en_US-libritts-high` voice; record MODEL_CARD +
  hash in docs/ATTRIBUTION.md. Phone uses OS speechSynthesis (no weights).
- Consequences: Avoids GPL copyleft on the default path. Re-verify espeak-ng/GPL note before Phase 4.

## 2026-10-11 — 4. Capture-first, Mode B must work regardless (Mode A time-boxed)
- Context: Live on-device bird ID in a browser PWA is high-risk (WASM model size, iOS limits,
  screen-lock audio survival unknown).
- Decision: PWA records audio+GPS and exports `.walk.json`; laptop batch analysis is the
  guaranteed path. Mode A (live on-device ID) gets a fixed time-box in Phase 1; fall back to B.
- Consequences: No schedule sink. Feasibility protocol in docs/PHONE_FEASIBILITY.md.

## 2026-10-11 — 5. No audio committed until licensed; download script otherwise
- Context: Fixture clips need redistribution-permitted licenses + attribution.
- Decision: Commit clips only with CC-BY/CC0/self-recorded provenance in docs/ATTRIBUTION.md;
  otherwise ship `scripts/download_fixtures.sh` + hashes.
- Consequences: Repo stays legally clean; tests generate synthetic WAVs where possible.

## 2026-10-11 — 6. Python 3.11+, FastAPI + vanilla HTML/JS, CPU-only, SQLite
- Context: Hard constraints from brief.
- Decision: As specified. No frontend frameworks. Migrations in-repo. Provenance
  (model name/version + config snapshot) stored per walk/detection.
- Consequences: Keeps offline + $0-cost story measurable in Phase 9/10.
