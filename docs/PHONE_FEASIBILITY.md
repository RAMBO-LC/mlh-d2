# PHONE_FEASIBILITY.md — Phase 1b protocol + results

Status (2026-10-11, Phase 0): PROTOCOL ONLY — no measurements yet. Do not quote numbers
from this file until the Results table is filled with real runs.

## Decision to be made (gate at end of Phase 1)
Choose **Mode A** (live on-device ID in PWA), **Mode B** (PWA records audio+GPS, laptop
analyzes after), or **both**. Mode B must work regardless. Fixed time-box on Mode A; fall back to B.

## Hypotheses (to be confirmed/refuted with data)
- H1: A bird model (BirdNET or Perch TFLite/ONNX via WASM in a Web Worker) can score a 3s
  window on a mid-range Android phone in <1× real time (<3000 ms/window) after warmup.
- H2: Audio capture can survive screen lock via Wake Lock + black pocket-mode overlay
  (tap-and-hold to wake) on Android Chrome; iOS Safari background behavior is the known risk.
- H3: Chunked IndexedDB writes keep RAM flat over a 60-min walk (never hold full walk in RAM).

## Method — laptop spike (Phase 1a, reference numbers for phone)
1. Fixture WAV → 3s windows, resample 48 kHz mono, overlap per config.
2. Run BirdNET-Analyzer; confirm location/week filtering changes the candidate list.
3. Report: model load time, ms/window (mean/p50/p95), CPU %, RAM, disk. CPU-only.

## Method — phone spike (Phase 1b)
1. **Model packaging:** export/obtain TFLite or ONNX bird model; record bytes + quantization.
   Try ONNX Runtime Web or TFLite WASM delegate inside a dedicated Web Worker (never main thread).
2. **Load test:** cold load time (ms), warm load, failure on iOS Safari (record exact error).
3. **Inference test:** 10× 3s windows (48 kHz mono, same preprocessing as laptop) → ms/window
   mean/p50/p95, UI jank observed y/n, worker memory.
4. **Battery:** 15-min continuous classification run, % drain + device temp note + Android model.
5. **Capture survival:** start getUserMedia → lock screen → 2 min → unlock → count gaps.
   Repeat with Wake Lock + pocket overlay. Record: continuous / gaps / stopped + browser + OS.
6. **Storage:** 10-min capture → IndexedDB bytes, chunk scheme (e.g. 5s Opus/WAV chunks),
   auto-save every 10 s, resume-after-kill test, low-storage warning threshold.
7. **GPS (opt-in, off default):** sample every N s, record accuracy + battery delta.

## Devices to test (fill what is available; mark the rest "not measured")
- [ ] Mid-range Android (e.g. Pixel 6a / Galaxy A-series) + Chrome
- [ ] iOS Safari (iPhone, version noted)
- [ ] Laptop reference (Linux/macOS/Windows, CPU model noted)

## Results (fill in Phase 1 — DO NOT FABRICATE)

| Test | Device / browser | Metric | Value | Notes |
|---|---|---|---|---|
| Model size | — | bytes | _not measured_ | |
| Cold load | — | ms | _not measured_ | |
| ms / 3s window (mean/p50/p95) | — | ms | _not measured_ | |
| Battery (15 min classify) | — | % drain | _not measured_ | |
| Screen-lock capture | — | continuous/gaps/stopped | _not measured_ | |
| 10-min IndexedDB size | — | MB | _not measured_ | |
| GPS sampled track | — | points / accuracy | _not measured_ | |

## Gate criteria (proposed; confirm with user only if borderline)
- Mode A ships iff: p95 ms/window < 3000 on target Android AND capture survives lock with
  Wake Lock AND battery drain acceptable (<~10 %/h classify) AND iOS has a documented fallback.
- Else: Mode B only, Mode A documented as "attempted, blocked by X" with numbers.
