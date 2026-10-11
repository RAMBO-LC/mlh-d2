#!/usr/bin/env python3
"""Field Notes audio helper. Python standard library + ffmpeg only.

Subcommands
  bundled            Copy the 3 s sample.wav that ships inside birdnet-analyzer
                     (needs no account and no network).
  xc ID              Download Xeno-canto recording ID via the official API and
                     convert it to 48 kHz mono WAV. Needs a FREE Xeno-canto API key
                     (env XENO_CANTO_API_KEY, a git-ignored .env file, or --key).
                     Refuses NoDerivs licences automatically.
  prepare FILE       Convert ANY audio file (m4a, mp3, aac, ogg, wav...) to the
                     format the pipeline wants: 48 kHz, mono, 16-bit WAV.
  check FILE         Report whether a WAV is ready to upload.

Everything is written under data/ (git-ignored). Audio is never committed.
The API key is never printed or written anywhere.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

DATA = Path(os.environ.get("FIELDNOTES_DATA", "data"))
SAMPLES = DATA / "samples"
WALKS = DATA / "walks"
SOURCES = SAMPLES / "SOURCES.json"
TARGET_RATE = 48000
MIN_SECONDS = 3.0
XC_API = "https://xeno-canto.org/api/3/recordings"
UA = "FieldNotes-hackathon/0.1 (offline bird journal; contact: repo issues)"


class AudioError(Exception):
    """A problem with a readable message for the user."""


# ---------------------------------------------------------------- ffmpeg ----
def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:  # small bundled binary, avoids a big brew install on slow links
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise AudioError(
            "ffmpeg not found. Install it (brew install ffmpeg) or the smaller "
            "option: pip install imageio-ffmpeg"
        )


def to_wav(src: Path, dst: Path, start: float = 0.0, max_seconds: float | None = None) -> dict:
    """Convert any audio file to 48 kHz mono 16-bit PCM WAV."""
    if not src.exists():
        raise AudioError(f"File not found: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [find_ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vn"]
    if start > 0:
        cmd += ["-ss", str(start)]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-ar", str(TARGET_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dst)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dst.exists():
        raise AudioError(f"ffmpeg could not read {src.name}: {proc.stderr.strip()[:300]}")
    return describe_wav(dst)


def describe_wav(path: Path) -> dict:
    try:
        with wave.open(str(path), "rb") as w:
            frames, rate = w.getnframes(), w.getframerate()
            return {
                "path": str(path),
                "sample_rate": rate,
                "channels": w.getnchannels(),
                "seconds": round(frames / float(rate), 2) if rate else 0.0,
                "size_mb": round(path.stat().st_size / 1e6, 2),
            }
    except (wave.Error, EOFError) as exc:
        raise AudioError(f"{path.name} is not a readable WAV file ({exc}).")


def verdict(info: dict) -> list[str]:
    notes = []
    if info["seconds"] < MIN_SECONDS:
        notes.append(f"TOO SHORT: {info['seconds']} s (need at least {MIN_SECONDS:.0f} s).")
    if info["sample_rate"] != TARGET_RATE or info["channels"] != 1:
        notes.append(
            f"Not 48 kHz mono ({info['sample_rate']} Hz, {info['channels']} ch). "
            "Run: python scripts/get_audio.py prepare <file>"
        )
    if info["size_mb"] > 190:
        notes.append("Larger than ~200 MB upload cap. Trim with --max-seconds.")
    return notes or ["OK to upload."]


# -------------------------------------------------------------- sources -----
def record_source(entry: dict) -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(SOURCES.read_text()) if SOURCES.exists() else []
    except json.JSONDecodeError:
        existing = []
    existing = [e for e in existing if e.get("file") != entry["file"]]
    existing.append(entry)
    SOURCES.write_text(json.dumps(existing, indent=2))


# -------------------------------------------------------------- bundled -----
def cmd_bundled(_: argparse.Namespace) -> int:
    try:
        import birdnet_analyzer  # type: ignore
    except ImportError:
        raise AudioError("birdnet-analyzer is not installed in this environment (run make setup).")
    root = Path(birdnet_analyzer.__file__).parent
    hits = sorted(root.rglob("sample.wav")) or sorted(root.rglob("*sample*.wav"))
    if not hits:
        raise AudioError(f"No sample WAV found inside {root}.")
    dst = SAMPLES / "birdnet_sample.wav"
    SAMPLES.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hits[0], dst)
    info = describe_wav(dst)
    record_source({
        "file": dst.name,
        "origin": "sample clip shipped inside the birdnet-analyzer package",
        "licence": "see docs/ATTRIBUTION.md (check the package licence)",
        "downloaded": dt.date.today().isoformat(),
        "is_my_recording": False,
    })
    print(f"Copied bundled sample -> {dst}  {info}")
    print("NOTE: this is a library sample, not a field recording of mine.")
    return 0


# ---------------------------------------------------------- xeno-canto ------
def load_key(cli_key: str | None) -> str | None:
    if cli_key:
        return cli_key
    if os.environ.get("XENO_CANTO_API_KEY"):
        return os.environ["XENO_CANTO_API_KEY"]
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            m = re.match(r"\s*XENO_CANTO_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def licence_allows_conversion(lic: str) -> bool:
    """NoDerivs licences forbid format conversion/trimming, so refuse them."""
    return "-nd" not in lic.lower()


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def cmd_xc(args: argparse.Namespace) -> int:
    rec_id = re.sub(r"\D", "", args.id)
    if not rec_id:
        raise AudioError("Give the numeric Xeno-canto ID, e.g. 476378.")
    key = load_key(args.key)
    if not key:
        raise AudioError(
            "No Xeno-canto API key. Register (free) at xeno-canto.org, copy the key from "
            "your account page, then: export XENO_CANTO_API_KEY=... (or put it in a "
            "git-ignored .env file). Never commit it.\n"
            "Manual fallback: download the MP3 in your browser, then run\n"
            "  python scripts/get_audio.py prepare <downloaded.mp3>"
        )
    query = urllib.parse.urlencode({"query": f"nr:{rec_id}", "key": key})
    try:
        meta = json.loads(http_get(f"{XC_API}?{query}"))
    except urllib.error.HTTPError as exc:
        raise AudioError(
            f"Xeno-canto answered HTTP {exc.code}. Check your API key, or use the manual "
            "fallback: download the MP3 in a browser and run the 'prepare' command."
        )
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise AudioError(f"Could not reach or parse the Xeno-canto API ({exc}).")
    recs = meta.get("recordings") or []
    if not recs:
        raise AudioError(f"Xeno-canto returned no recording for XC{rec_id}.")
    r = recs[0]
    lic = str(r.get("lic", ""))
    if not licence_allows_conversion(lic):
        raise AudioError(
            f"XC{rec_id} is licensed NoDerivs ({lic}); converting or trimming it could "
            "count as a derivative. Pick a different recording."
        )
    file_url = str(r.get("file", ""))
    if file_url.startswith("//"):
        file_url = "https:" + file_url
    if not file_url.startswith("http"):
        raise AudioError("The API response had no downloadable file URL for this recording.")
    raw = SAMPLES / "raw" / f"XC{rec_id}.mp3"
    raw.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw.write_bytes(http_get(file_url))
    except urllib.error.URLError as exc:
        raise AudioError(f"Download failed ({exc}). Use the manual fallback.")
    dst = SAMPLES / f"XC{rec_id}.wav"
    info = to_wav(raw, dst, start=args.start, max_seconds=args.max_seconds)
    citation = f"{r.get('rec', 'unknown recordist')}, XC{rec_id}. Accessible at www.xeno-canto.org/{rec_id}."
    record_source({
        "file": dst.name,
        "origin": f"Xeno-canto XC{rec_id} ({r.get('en', 'unknown species')})",
        "recordist": r.get("rec"),
        "licence": lic,
        "citation": citation,
        "downloaded": dt.date.today().isoformat(),
        "converted": f"48 kHz mono WAV, start={args.start}s, max={args.max_seconds}s",
        "ground_truth_label": r.get("en"),
        "is_my_recording": False,
    })
    print(f"Saved {dst}  {info}")
    print(f"Cite as: {citation}  Licence: {lic}")
    print("Reminder: do not commit this audio; add the citation to docs/ATTRIBUTION.md.")
    return 0


# -------------------------------------------------------------- prepare -----
def cmd_prepare(args: argparse.Namespace) -> int:
    src = Path(args.file).expanduser()
    out = Path(args.out) if args.out else WALKS / f"{src.stem}_48k.wav"
    info = to_wav(src, out, start=args.start, max_seconds=args.max_seconds)
    print(f"Wrote {out}  {info}")
    for line in verdict(info):
        print(" -", line)
    print("Privacy: listen before sharing; recordings can contain voices. Keep location off.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    info = describe_wav(Path(args.file).expanduser())
    print(info)
    notes = verdict(info)
    for line in notes:
        print(" -", line)
    return 0 if notes == ["OK to upload."] else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bundled").set_defaults(fn=cmd_bundled)
    x = sub.add_parser("xc")
    x.add_argument("id")
    x.add_argument("--key")
    x.add_argument("--start", type=float, default=0.0)
    x.add_argument("--max-seconds", type=float, default=60.0)
    x.set_defaults(fn=cmd_xc)
    pr = sub.add_parser("prepare")
    pr.add_argument("file")
    pr.add_argument("--out")
    pr.add_argument("--start", type=float, default=0.0)
    pr.add_argument("--max-seconds", type=float, default=None)
    pr.set_defaults(fn=cmd_prepare)
    c = sub.add_parser("check")
    c.add_argument("file")
    c.set_defaults(fn=cmd_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except AudioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
