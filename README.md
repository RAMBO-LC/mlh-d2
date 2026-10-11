# Field Notes — an offline bird journal

*Walk with your phone in your pocket. Come home to a journal page — written entirely
on your own computer. No cloud, no account, no telemetry.*

Built for the **Hacktoberfest Open-Source AI Challenge, Week 1: Touch Grass**.

Watch it: [`docs/demo/field-notes-demo.mp4`](docs/demo/field-notes-demo.mp4)
(47 s, rendered from real app output) · Try it: the public-domain clip in
[`docs/demo/`](docs/demo/) analyzes in seconds.

---

## How it works

| Step | What happens | Where |
|---|---|---|
| 🎙️ You walk | Phone records audio in your pocket. The screen stays off. | Outside |
| 🐦 It listens | BirdNET (open bird-ID model) scores 3-second windows, filtered by your place and date | Your laptop |
| 📓 It remembers | Detections go to a local SQLite log: *first ever* → life list, plus a short clip per new species so you can verify by ear | `data/` (git-ignored) |
| ✍️ It writes | A local Gemma model — or the built-in template when it's absent — writes ~150 words: species of the day, one idea for next time. Uncertain IDs are labeled *uncertain*; a guard rejects any bird not in the log | Recap page |
| 📖 You recap | One calm notebook page: specimen cards, a per-window timeline, playable clips, journal, life list, exports | `http://127.0.0.1:8765` |

## Quickstart (under 10 minutes on a decent link)

```sh
git clone https://github.com/RAMBO-LC/mlh-d2.git && cd mlh-d2
make setup      # virtualenv + pinned deps + one-time 224 MB BirdNET model download
```

**Your first detection** (no account, no key needed):

```sh
make sample     # copies BirdNET's bundled 3 s sample to data/samples/
make run        # open http://127.0.0.1:8765, upload data/samples/birdnet_sample.wav
```

**Your own walk** — record with any phone recorder app (≥3 s), then either
convert it or check it first (see [docs/WHAT_TO_UPLOAD.md](docs/WHAT_TO_UPLOAD.md)
for the full guide):

```sh
make prepare FILE=~/Downloads/walk.m4a   # → data/walks/walk_48k.wav (48 kHz mono)
make sample-xc ID=476378                 # reference clip from Xeno-canto (free key needed)
PYTHONPATH=src .venv/bin/python -m fieldnotes.cli --config config.yaml \
  analyze data/walks/walk_48k.wav --lat <you> --lon <you> --date <YYYY-MM-DD> --own
```

**Proof it never phones home:**

```sh
make offline-demo
# analyzed 1 windows -> 2 detections (Lesser Redpoll, Common Redpoll)
# journal [template:…] (425 chars), external connection attempts: 0
# OFFLINE DEMO OK
```

**Tests:** `make test` (fast, 80+ tests) · `make test-slow` (real BirdNET model, still offline).

Put your coordinates in `config.local.yaml` (git-ignored, sits next to
`config.yaml`). GPS stays off unless you opt in; audio never leaves the machine;
`Delete all my data` (page) or `make clean-data` removes everything local.

## The open core (precise words)

| Part | Runs | Code | Weights / data | Commercial |
|---|---|---|---|---|
| Bird ID | BirdNET-Analyzer 2.4.0 (`GLOBAL_6K_V2.4`) | MIT — open-source | CC BY-NC-SA 4.0 — open-weight, **not** open-source | No (weights) |
| Journal | `gemma3:4b` via Ollama, local (template needs no model) | Ollama: MIT | Custom [Gemma Terms of Use](https://ai.google.dev/gemma/terms) — open-weight, **not** OSI open-source | Yes, with conditions |

Every row was verified against the source repos on 2026-10-11 — full table in
[LICENSES.md](LICENSES.md), clip credits in [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).
Decisions are logged in [docs/DECISIONS.md](docs/DECISIONS.md).

## Repo map

```
config.yaml / config.local.yaml   all settings (local file is git-ignored)
src/fieldnotes/  detect/ store/ journal/ web/ + service.py, cli.py
scripts/  get_audio.py (audio helper)  offline_demo.py  make_demo.py
tests/    90+ tests, incl. offline + privacy guards
docs/     WHAT_TO_UPLOAD.md  ATTRIBUTION.md  DECISIONS.md  demo/
```

## Not in scope (future work)

Phone PWA and on-device inference, Perch backend, quest cards, kids' mode,
live-mic mode and spoken announcements, whisper.cpp voice commands, run-club mode,
Raspberry Pi recorder, cloud comparisons, multi-page UI polish.

## Submission notes

Built new inside the Hacktoberfest window (Oct 5–11, 2026). Commits after the
deadline, if any, will be listed here — none so far.
