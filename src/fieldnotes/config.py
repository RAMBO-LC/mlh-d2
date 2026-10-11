"""Load and validate config.yaml. Every tunable lives here; code reads config, not constants."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

DEFAULTS: dict = {
    "bird_backend": "birdnet",
    "confidence_threshold": 0.3,
    "window_s": 3.0,
    "overlap_s": 0.0,
    "region_lat": 37.77,
    "region_lon": -122.41,
    "week_override": 0,
    "language": "en",
    "debounce_minutes": 10,
    "llm_name": "gemma3:4b",
    "llm_timeout_s": 120,
    "privacy": {"gps_enabled": False, "save_clips": True},
    "tts_voice": "none",
    "database": "data/fieldnotes.db",
    "clips_dir": "data/clips",
}

_VALID_BACKENDS = {"birdnet"}  # perch intentionally absent in MVP (see README Future work)


def load_config(path: str | Path) -> dict:
    """Load config.yaml over DEFAULTS. Raises ValueError with a readable message on bad input."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"config file not found: {p} (copy config.yaml and edit it)")
    try:
        raw = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"config file {p} is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"config file {p} must be a mapping of key: value pairs")
    cfg = copy.deepcopy(DEFAULTS)
    _deep_update(cfg, raw)
    # Personal overrides (e.g. your region_lat/region_lon): git-ignored
    # config.local.yaml next to the main config file, merged on top.
    local = p.parent / "config.local.yaml"
    if local.exists():
        try:
            extra = yaml.safe_load(local.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"config file {local} is not valid YAML: {exc}") from exc
        if not isinstance(extra, dict):
            raise ValueError(f"config file {local} must be a mapping of key: value pairs")
        _deep_update(cfg, extra)
    _validate(cfg)
    return cfg


def _deep_update(base: dict, override: dict) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _validate(cfg: dict) -> None:
    thr = cfg["confidence_threshold"]
    if not isinstance(thr, (int, float)) or not 0.0 <= thr <= 1.0:
        raise ValueError(f"confidence_threshold must be 0.0-1.0, got {thr!r}")
    if cfg["window_s"] <= 0:
        raise ValueError(f"window_s must be positive, got {cfg['window_s']!r}")
    if not 0 <= cfg["overlap_s"] < cfg["window_s"]:
        raise ValueError(
            f"overlap_s must satisfy 0 <= overlap < window_s, got {cfg['overlap_s']!r}"
        )
    if cfg["bird_backend"] not in _VALID_BACKENDS:
        raise ValueError(
            f"bird_backend {cfg['bird_backend']!r} is not available in this build. "
            f"Available: {sorted(_VALID_BACKENDS)}. (Perch is future work.)"
        )
    week = cfg["week_override"]
    if not isinstance(week, int) or not 0 <= week <= 48:
        raise ValueError(f"week_override must be an int 0-48, got {week!r}")
    if cfg["debounce_minutes"] < 0:
        raise ValueError("debounce_minutes must be >= 0")
    if not cfg["llm_name"] or not isinstance(cfg["llm_name"], str):
        raise ValueError("llm_name must be a non-empty Ollama model tag, e.g. gemma3:4b")
