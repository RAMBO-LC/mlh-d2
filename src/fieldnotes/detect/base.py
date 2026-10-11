"""Detector interface. Backend swap via config needs no code change (tested).

Design note: backends analyze whole files with their native pipeline (BirdNET's
own 3s / 48kHz windowing + location/week filter). audio/windows.py powers silence
stats, bench timing math, and tests — it is not dead code.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Detection:
    species_common: str
    species_sci: str
    confidence: float
    start_s: float
    end_s: float


def get_backend(name: str):
    """Return the backend module for config bird_backend. No code change needed to swap."""
    if name == "birdnet":
        from . import birdnet as mod

        return mod
    raise ValueError(
        f"bird_backend {name!r} is not available in this build. "
        "Available: ['birdnet']. (Perch is future work — see README.)"
    )
