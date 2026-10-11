# Field Notes — an offline bird journal

A calm companion for the "Touch Grass" theme: record outside (phone in pocket),
come home, and get detections + a field journal — all on your own computer.
No cloud, no account, no telemetry. The screen is for setup and recap only.

## Setup (Linux/macOS, Python 3.11+)

```sh
git clone https://github.com/RAMBO-LC/mlh-d2.git && cd mlh-d2
make setup     # venv + pinned deps + one-time 224 MB BirdNET model download
```

Optional, once (needs network, then works offline): install Ollama and
`ollama pull gemma3:4b` for LLM-written journals. Without it, the built-in
template journal is used automatically.

## How to run

```sh
# Analyze a recording (3 s windows, season filter from --date):
PYTHONPATH=src .venv/bin/python -m fieldnotes.cli --config config.yaml \
  analyze docs/demo/blackbird-southern-finland.ogg --lat 60.17 --lon 24.94 --date 2025-05-15
# walk 5: 4 detections in 8 windows (2 gated as silence)
#       0.0s  Eurasian Blackbird (Turdus merula)  conf=0.78  [first_ever]
# ...

# Journal for a walk (template shown; LLM text when Ollama is up):
PYTHONPATH=src .venv/bin/python -m fieldnotes.cli --config config.yaml journal 5

# Recap page (localhost only):  make run   ->  http://127.0.0.1:8765

# Offline proof (external network blocked, fails loudly otherwise):
make offline-demo
# analyzed 1 windows -> 2 detections (Lesser Redpoll, Common Redpoll)
# journal [template:...] (425 chars), external connection attempts: 0
# OFFLINE DEMO OK

make test   # fast suite (slow model tests deselected)
make test-slow  # real BirdNET model on the bundled sample, still offline
```

Copy `config.yaml` settings to `config.local.yaml` (git-ignored) for your
coordinates. GPS is off by default; audio never leaves the machine.

## Models (open core, precise words)

| Part | What runs | Code | Weights | Commercial |
|---|---|---|---|---|
| Bird ID | BirdNET-Analyzer 2.4.0, GLOBAL_6K_V2.4 | MIT (open-source) | CC BY-NC-SA 4.0 — open-weight, **not** open-source | No (weights) |
| Journal | `gemma3:4b` via Ollama (local; template fallback needs no model) | Ollama: MIT | Custom [Gemma Terms of Use](https://ai.google.dev/gemma/terms) — open-weight, **not** OSI open-source | Yes, with conditions |

Details + check dates in [LICENSES.md](LICENSES.md). Demo clip: public-domain
Blackbird song by Oona Räisänen, see [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).

## What this does NOT yet do (Future work)

Phone PWA / on-device phone inference, Perch backend, quest cards, kids' mode,
live-mic mode, spoken announcements, whisper.cpp voice commands, run-club mode,
Raspberry Pi recorder, cloud-comparison adapter, UI polish beyond the notebook page.

## Submission notes

Built new inside the Hacktoberfest window (Oct 5–11, 2026). Commits after the
deadline, if any, will be listed here — none so far.
