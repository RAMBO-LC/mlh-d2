"""Shared test helpers: tiny synthetic WAVs (no committed audio, no license issues)."""
from __future__ import annotations

import numpy as np
import soundfile as sf


def make_wav(path: str, seconds: float = 6.0, sr: int = 48000, freq: float = 3000.0) -> str:
    """Write a short FM-sweep chirp (bird-ish, synthetic) as 16-bit WAV."""
    t = np.arange(int(seconds * sr)) / sr
    sweep = np.sin(2 * np.pi * (freq + 800 * np.sin(2 * np.pi * 3 * t)) * t)
    env = np.minimum(1.0, t * 4) * np.minimum(1.0, (seconds - t) * 4)
    sf.write(path, (0.3 * sweep * env).astype(np.float32), sr)
    return path


def make_silence(path: str, seconds: float = 6.0, sr: int = 48000) -> str:
    sf.write(path, np.zeros(int(seconds * sr), dtype=np.float32), sr)
    return path
