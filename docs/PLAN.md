# PLAN.md — Field Notes Phase 0 (no code yet)

## 1. Proposed repo tree

```
fieldnotes/
  LICENSES.md              # checked 2026-10-11 (root)
  README.md                # Phase 11 (setup <10 min, phone install, troubleshooting)
  Makefile                 # setup, run, test, offline-demo, bench, eval, compare, clean-data
  config.yaml              # single config: backend, LLM, threshold, window/overlap,
                           # TTS voice, lat/lon, week override, language, debounce,
                           # privacy flags (gps off default). Example values Phase 2.
  requirements.txt         # pinned versions (Phase 1/2); Python 3.11+
  pyproject.toml           # ruff + pytest + coverage (>80% on logic modules)
  scripts/
    setup.sh / download_fixtures.sh / download_models.sh
    switch_backend.py      # Phase 9 swap demo (config-only)
  src/fieldnotes/
    __init__.py
    config.py              # load/validate config.yaml
    detect/
      base.py              # Detection dataclass + Detector protocol
      birdnet.py           # real backend (Phase 2)
      perch.py             # stub → working backend (STRETCH)
    audio/
      windows.py           # 3s windows, overlap, resample 48kHz mono, silence gate
      fixtures.py          # synthetic WAV generation for tests (no committed audio)
    store/
      db.py                # SQLite + migrations
      logic.py             # debounce / novelty (first-ever / first-walk / repeat)
      models.py            # walks, detections, clips, life_list, quests, settings
    feedback/
      tts.py               # Piper wrapper + quiet mode + <2s cap
      chime.py
    live/
      stream.py            # sounddevice ring buffer (laptop)
    ingest/
      bundle.py            # import .walk.json → DB + batch analyze
    journal/
      llm.py               # Ollama client + model auto-pick
      prompt.py            # prompt builder (facts-only, trivia labeling)
      guard.py             # species-in-log check + one regen
      template.py          # fallback when Ollama missing
    quests/
      cards.py             # hemisphere-aware, verified vs log
    web/
      app.py               # FastAPI
      templates/ + static/ # plain HTML/JS, no frameworks, dark mode, huge text
    privacy/
      wipe.py              # delete-all-data (CLI + button)
  pwa/                     # vanilla JS, service worker, installable, offline-first
    index.html  app.js  sw.js  manifest.webmanifest
    recorder.js (getUserMedia → IndexedDB chunks)  export.js (.walk.json via Share/download)
  tests/                   # pytest; unit + offline socket-block test
    test_windows.py  test_detect_interface.py  test_debounce.py
    test_db.py  test_journal_guard.py  test_offline.py  test_wipe.py
  benchmarks/  eval/  compare/   # Phase 9 (latency, precision/recall, cloud adapter DISABLED default)
  docs/
    PLAN.md  DECISIONS.md  LICENSES→(root)  ATTRIBUTION.md
    PHONE_FEASIBILITY.md   WHY_OPEN.md  FIELD_TEST.md  POST_DRAFT.md  DEMO_SCRIPT.md
  fixtures/                # empty until licensed clips confirmed; else download script
```

Estimated disk/RAM (to be measured in Phase 1/9, stated here as budgets):
- BirdNET weights ~ tens of MB; RAM budget ~1–2 GB CPU inference; disk <2 GB incl. DB+clips.
- `qwen3:4b` ~2.5 GB weights, ~4–6 GB RAM via Ollama CPU. `gemma3:4b` similar.
- Piper voice ~50–100 MB per voice. Total laptop budget: ~8 GB disk, 8 GB RAM min.

## 2. Model choices (with license findings — see LICENSES.md)

| Slot | Default | Why | License story (precise words) |
|---|---|---|---|
| Bird ID | BirdNET-Analyzer | 3s/48kHz-mono native, location/week filter built in | Code **open-source** (MIT); weights **open-weight, non-commercial** (CC BY-NC-SA 4.0). OK for hackathon/personal; never claim "fully open-source". |
| Bird alt | Perch-Hoplite (stub Phase 2) | 10k+ species, embeddings path | Code **open-source** (Apache-2.0); weights **unverified** — re-check Kaggle terms before use. |
| Journal LLM | `qwen3:4b` via Ollama | Small, CPU-OK, most permissive | Runner **open-source** (MIT); weights **open-weight under Apache-2.0** (OSI-approved terms). |
| TTS laptop | Legacy Piper + `en_US-libritts-high` | Fast, local, tiny | Engine **open-source** (MIT legacy; successor is GPL-3.0 — avoid by pinning); voice CC-BY 4.0 (attribution). |
| TTS phone | speechSynthesis + vibration | Zero weights, offline voices where available | OS-provided; document fallback. |
| STRETCH voice cmd | whisper.cpp + Whisper weights | MIT code + MIT weights (cleanest) | Both **open-source / open-weight under MIT**. Deferred. |

`config.yaml` keys (all configurable): `bird_backend`, `llm_name`, `confidence_threshold`,
`window_s`, `overlap_s`, `tts_voice`, `region_lat`, `region_lon`, `week_override`, `language`,
`debounce_minutes`, `privacy.{gps_enabled,audio_retention}`, `model_versions` (recorded per walk).

## 3. Phone-feasibility plan (summary; full protocol in PHONE_FEASIBILITY.md)

- Time-box Mode A (live on-device ID via TFLite/ONNX+WASM worker). Mode B (record → export
  `.walk.json` → laptop batch) is guaranteed regardless.
- Measure: model size, load time, ms/3s-window, RAM, battery, screen-lock survival
  (Wake Lock + pocket-mode overlay), iOS Safari vs Android Chrome.
- Gate at end of Phase 1: A / B / both, decided with numbers, not hope.

## 4. Gates & quality bar
- After every phase: `pytest + ruff`, show output, update docs, commit. Never advance on red.
- Coverage >80% on detector interface, debounce, DB, journal builder/guard.
- Every failure mode gets a graceful path + user-readable message (no mic/GPS, denied perms,
  missing model, Ollama down, full storage, corrupt bundle).
- Reproducibility: seed randoms; store model versions + config snapshot per walk.
- No unverified numbers: unmeasured = "not measured".
