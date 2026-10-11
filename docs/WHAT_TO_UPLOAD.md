# What to upload

Field Notes analyzes **one audio recording at a time** and lists the bird calls it can identify.
This page tells you what makes a good recording, and how to get it into the right format.

## The short version

| Question | Answer |
|---|---|
| Format the pipeline wants | **WAV, 48 kHz, mono** |
| Minimum length | **3 seconds** (the model scores 3-second windows) |
| Good length for a walk | 10 to 60 minutes |
| Upload size cap | about 200 MB per file (the web page's limit) |
| Other formats (m4a, mp3, aac, ogg) | Convert first: `python scripts/get_audio.py prepare <file>` |
| Check a file before uploading | `python scripts/get_audio.py check <file.wav>` |

## Three ways to get a file

### 1. Your own walk (best)

1. Record with any phone recorder app (Voice Memos on iPhone, any recorder app on Android).
   Start it, put the phone in your pocket or a bag with the microphone uncovered, and walk.
2. Move the recording to your laptop (AirDrop, USB, or a cable).
3. Convert it, trimming if it is very long:
   `python scripts/get_audio.py prepare ~/Downloads/walk.m4a --max-seconds 1800`
4. Upload `data/walks/walk_48k.wav` on the page, set the **date** to the day you recorded,
   and leave location off unless you want the location filter.

### 2. The sample that ships with BirdNET (works with no account)

`python scripts/get_audio.py bundled` copies a 3-second library sample to `data/samples/`.
It is **not a field recording of yours**. It contains redpoll finches, which are subarctic birds,
so with an ordinary mid-latitude location the filter should return nothing. That is the
filter working, not a failure.

### 3. A documented reference recording from Xeno-canto (needs a free key)

1. Register at xeno-canto.org (free) and copy the API key from your account page.
2. `export XENO_CANTO_API_KEY=...` (or put it in a git-ignored `.env` file). Never commit it.
3. `python scripts/get_audio.py xc 476378`

The script downloads the clip, converts it, refuses NoDerivs licences, and records the
citation in `data/samples/SOURCES.json`. If the download is blocked, download the MP3 in a
browser and run the `prepare` command on it.

Xeno-canto labels come from the recordist. A single clean, single-species clip is a sanity
check, **not a measure of how it performs on a real walk**.

## What works well and what does not

These are practical tips, not measured results.

**Works better**
- Early morning, when birds are most active.
- The phone held or placed with its microphone clear of cloth.
- Calm weather and a quiet spot.
- Stopping for a few minutes at a pond edge, hedge, or tree line.

**Works worse**
- Strong wind across the microphone.
- Traffic, machinery, or loud conversation.
- Birds heard only through a loudspeaker (playing recordings at a bird is also discouraged).
- Very distant or very faint calls.

## Reading the results

- **Confidence** is the model's score, not a probability that the bird is really there.
  Treat low scores as "uncertain".
- **Always listen to the saved clip** for a new species before you believe it.
- A walk with zero detections is a normal result.
- The location filter uses your location and the date. A wrong date or location can hide
  real birds or admit unlikely ones.

## Privacy

- Recordings can contain voices. Listen before sharing, and trim anything personal.
- Location is off by default. If you turn it on, keep exact coordinates out of any repo.
- Everything stays in the local `data/` folder. "Delete all my data" on the page, or
  `fieldnotes wipe --yes`, removes the database and every saved clip.

## Licences for sample audio

Never commit audio you did not record yourself. Credit the recordist and licence for any
reference clip in `docs/ATTRIBUTION.md`.
