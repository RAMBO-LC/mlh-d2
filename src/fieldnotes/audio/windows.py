"""3s windowing: mono mix, resample to model rate, overlap, silence/noise gating."""
from __future__ import annotations

from dataclasses import dataclass
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


@dataclass
class Window:
    audio: np.ndarray  # mono float32 at target_sr
    start_s: float
    end_s: float
    kept: bool  # False when gated out as silence
    rms: float


def load_mono(path: str, target_sr: int = 48000) -> tuple[np.ndarray, int]:
    """Load any audio file as mono float32 at target_sr. Readable errors on bad input."""
    try:
        data, sr = sf.read(path, always_2d=True)
    except Exception as exc:
        raise ValueError(
            f"could not read audio file {path!r}: {exc}. "
            "Use a WAV/FLAC/OGG file (16-bit PCM WAV recommended)."
        ) from exc
    mono = data.mean(axis=1).astype(np.float32)
    if sr != target_sr:
        mono = _resample(mono, sr, target_sr)
    return mono, target_sr


def _resample(audio: np.ndarray, sr: int, target_sr: int) -> np.ndarray:
    g = gcd(sr, target_sr)
    up, down = target_sr // g, sr // g
    if up <= 100 and down <= 100:
        return resample_poly(audio, up, down).astype(np.float32)
    n = int(round(len(audio) * target_sr / sr))
    return np.fft.irfft(np.fft.rfft(audio), n=n).astype(np.float32)[:n]


def make_windows(
    audio: np.ndarray,
    sample_rate: int,
    window_s: float = 3.0,
    overlap_s: float = 0.0,
    silence_rms: float = 0.005,
) -> list[Window]:
    """Slice audio into fixed windows. Windows below silence_rms are kept=False (gated)."""
    win_n = int(round(window_s * sample_rate))
    step_n = int(round((window_s - overlap_s) * sample_rate))
    if win_n <= 0 or step_n <= 0:
        raise ValueError("window/overlap configuration yields empty windows")
    out: list[Window] = []
    # Full windows only; a trailing partial window is dropped (documented, tested).
    for start in range(0, len(audio) - win_n + 1, step_n):
        chunk = audio[start : start + win_n]
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
        out.append(
            Window(
                audio=chunk,
                start_s=start / sample_rate,
                end_s=(start + win_n) / sample_rate,
                kept=rms >= silence_rms,
                rms=rms,
            )
        )
    return out
