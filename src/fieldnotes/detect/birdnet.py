"""BirdNET backend: file in, detections out. 3s windows, 48kHz mono, location/week filter.

Uses birdnet-analyzer's own file pipeline (its native 3s / 48 kHz windowing), so the
"3s windows + location/week filtering" behavior is the upstream-tested one, not a re-implementation.
Model files are fetched once (setup / first run); afterwards everything runs offline.
"""
from __future__ import annotations

import csv
import glob
import io
import os
import tempfile
from contextlib import redirect_stdout

from .base import Detection

MODEL_VERSION = "birdnet-analyzer 2.4.0 (BirdNET GLOBAL_6K_V2.4 checkpoints)"


def analyze_file(
    path: str,
    *,
    min_conf: float = 0.3,
    lat: float = -1,
    lon: float = -1,
    week: int = -1,
    overlap_s: float = 0.0,
    language: str = "en",
    threads: int = 2,
) -> list[Detection]:
    """Analyze one audio file. Raises ValueError with a readable message on failure."""
    if not os.path.isfile(path):
        raise ValueError(f"audio file not found: {path}")
    try:
        from birdnet_analyzer.analyze.core import analyze
    except ImportError as exc:
        raise ValueError(
            "BirdNET is not installed. Run `make setup` first "
            "(it downloads the Python package and model files once)."
        ) from exc

    with tempfile.TemporaryDirectory(prefix="fieldnotes-") as tmp:
        try:
            with redirect_stdout(io.StringIO()):  # keep CLI output ours; errors still raise
                analyze(
                    path,
                    tmp,
                    min_conf=min_conf,
                    lat=lat,
                    lon=lon,
                    week=week,
                    overlap=overlap_s,
                    rtype="csv",
                    locale=language,
                    threads=threads,
                )
        except FileNotFoundError as exc:
            raise ValueError(f"audio file not found: {path}") from exc
        except Exception as exc:
            raise ValueError(_readable_error(exc)) from exc
        csvs = glob.glob(os.path.join(tmp, "*.BirdNET.results.csv"))
        if not csvs:
            return []
        return _parse_csv(csvs[0])


def _parse_csv(csv_path: str) -> list[Detection]:
    out: list[Detection] = []
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                out.append(
                    Detection(
                        species_common=row["Common name"].strip(),
                        species_sci=row["Scientific name"].strip(),
                        confidence=float(row["Confidence"]),
                        start_s=float(row["Start (s)"]),
                        end_s=float(row["End (s)"]),
                    )
                )
            except (KeyError, ValueError):
                continue  # skip malformed rows rather than failing the walk
    return out


def _readable_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "ffmpeg" in msg or "libsndfile" in msg or "format" in msg:
        return (
            f"BirdNET could not decode the audio ({exc}). "
            "Convert to 16-bit PCM WAV, 44.1/48 kHz mono, e.g.: "
            "ffmpeg -i input.m4a -ar 48000 -ac 1 walk.wav"
        )
    if "model" in msg and ("download" in msg or "not found" in msg or "missing" in msg):
        return (
            f"BirdNET model files are missing ({exc}). "
            "Run `make setup` once with network access, then go offline."
        )
    return f"BirdNET analysis failed: {exc}"
