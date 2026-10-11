"""Shared service layer used by both the CLI and the web UI (one code path)."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

import soundfile as sf

from .audio import windows as _windows
from .detect import base as _base
from .journal import writer as _writer
from .store import db as _db
from .store import logic as _logic


def iso_to_birdnet_week(date_str: str) -> int:
    """YYYY-MM-DD -> BirdNET week 1..48. Raises ValueError on bad dates."""
    try:
        dt = _dt.date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(f"--date must be YYYY-MM-DD, got {date_str!r}") from exc
    iso = dt.isocalendar().week
    return max(1, min(48, round(iso * 48 / 52)))


def resolve_geo(cfg: dict, lat: float | None, lon: float | None) -> tuple[float, float]:
    """Explicit flags win (that run is opt-in). Else config region if gps enabled. Else (-1,-1)."""
    if lat is not None and lon is not None:
        return lat, lon
    if cfg["privacy"]["gps_enabled"]:
        return cfg["region_lat"], cfg["region_lon"]
    return -1, -1


def analyze_walk(
    wav_path: str,
    cfg: dict,
    lat: float | None = None,
    lon: float | None = None,
    date: str | None = None,
    weather_note: str = "",
    own_recording: bool = False,
) -> dict:
    """Full pipeline: windows -> BirdNET -> DB -> clips. Returns a summary dict."""
    backend = _base.get_backend(cfg["bird_backend"])
    glat, glon = resolve_geo(cfg, lat, lon)
    if date:
        week_from_date = iso_to_birdnet_week(date)  # validates YYYY-MM-DD even if overridden
    else:
        week_from_date = -1
    if cfg["week_override"]:
        week = cfg["week_override"]
    elif date:
        week = week_from_date
    else:
        week = -1  # year-round (no date supplied)
    date_warning = None
    if date:
        delta = abs((_dt.date.today() - _dt.date.fromisoformat(date)).days)
        if delta > 30:
            date_warning = (
                f"warning: date {date} is {delta} days from today — the season "
                f"filter and the journal use it as-is."
            )

    audio, sr = _windows.load_mono(wav_path, 48000)
    if len(audio) < int(round(cfg["window_s"] * sr)):
        have = len(audio) / sr
        raise ValueError(
            f"audio is only {have:.1f}s long — need at least one {cfg['window_s']:.0f}s "
            f"window. Convert a longer recording with "
            f"`python scripts/get_audio.py prepare <file>` (see docs/WHAT_TO_UPLOAD.md)."
        )
    wins = _windows.make_windows(audio, sr, cfg["window_s"], cfg["overlap_s"])
    kept = [w for w in wins if w.kept]

    detections = backend.analyze_file(
        wav_path,
        min_conf=cfg["confidence_threshold"],
        lat=glat,
        lon=glon,
        week=week,
        overlap_s=cfg["overlap_s"],
        language=cfg["language"],
    )
    # Enforce the configured threshold regardless of backend (boundaries: >= keeps).
    detections = [d for d in detections if d.confidence >= cfg["confidence_threshold"]]

    con = _db.connect(cfg["database"])
    try:
        seen_ever = {r["species_sci"] for r in _db.life_list(con)}
        labeled = _logic.assign_novelty(list(detections), seen_ever, cfg["debounce_minutes"])
        started = date or _dt.date.today().isoformat()
        walk_id = _db.add_walk(
            con,
            source_file=str(wav_path),
            started_at=started,
            duration_s=len(audio) / sr,
            lat=glat if glat != -1 else None,
            lon=glon if glon != -1 else None,
            week=week if week != -1 else None,
            model_name=cfg["bird_backend"],
            model_version=getattr(backend, "MODEL_VERSION", "unknown"),
            config_json=_db.config_snapshot(cfg),
            is_own_recording=1 if own_recording else 0,
        )
        firsts_saved: list[str] = []
        for d, novelty in labeled:
            _db.add_detection(con, walk_id, novelty, d)
            if novelty == _logic.FIRST_EVER:
                _db.mark_seen(con, d.species_sci, d.species_common, started)
            if novelty in (_logic.FIRST_EVER, _logic.FIRST_THIS_WALK):
                if cfg["privacy"]["save_clips"] and d.species_common not in firsts_saved:
                    _save_clip(con, cfg, audio, sr, walk_id, d)
                    firsts_saved.append(d.species_common)
        con.commit()
    finally:
        con.close()
    return {
        "walk_id": walk_id,
        "n_windows": len(wins),
        "n_gated": len(wins) - len(kept),
        "n_detections": len(labeled),
        "date_warning": date_warning,
        "species": [
            {"common": d.species_common, "sci": d.species_sci,
             "confidence": d.confidence, "start_s": d.start_s, "novelty": n}
            for d, n in labeled
        ],
    }


def _save_clip(con, cfg: dict, audio, sr: int, walk_id: int, d) -> None:
    """Save a verification clip. Reuses the caller's connection (same transaction)."""
    clips_dir = Path(cfg["clips_dir"]) / f"walk_{walk_id}"
    clips_dir.mkdir(parents=True, exist_ok=True)
    pad = int(0.5 * sr)
    s = max(0, int(d.start_s * sr) - pad)
    e = min(len(audio), int(d.end_s * sr) + pad)
    safe = "".join(c if c.isalnum() else "_" for c in d.species_sci)[:60]
    path = clips_dir / f"{safe}_{d.start_s:.0f}s.wav"
    sf.write(str(path), audio[s:e], sr)
    _db.add_clip(con, walk_id, d.species_common, str(path), d.start_s, d.end_s)


def build_log(cfg: dict, walk_id: int) -> dict:
    con = _db.connect(cfg["database"])
    try:
        walk = con.execute("SELECT * FROM walks WHERE id=?", (walk_id,)).fetchone()
        if walk is None:
            raise ValueError(f"walk {walk_id} not found in {cfg['database']}")
        rows = _db.walk_detections(con, walk_id)
    finally:
        con.close()
    by_species: dict[str, dict] = {}
    for r in rows:
        key = r["species_sci"]
        slot = by_species.setdefault(key, {
            "species_common": r["species_common"], "species_sci": key,
            "confidence": 0.0, "count": 0,
            "novelty": r["novelty"], "start_s": r["start_s"]})
        slot["count"] += 1
        slot["confidence"] = max(slot["confidence"], r["confidence"])
    try:
        import json as _json

        walk_cfg = _json.loads(walk["config_json"] or "{}")
    except ValueError:
        walk_cfg = {}
    window_s = walk_cfg.get("window_s", 3.0) or 3.0
    n_windows = int(walk["duration_s"] // window_s)  # real full windows stored via duration
    loc_on = walk["lat"] is not None and walk["lon"] is not None
    return {
        "place": "unstated location" if not loc_on else "filtered location",
        "date": walk["started_at"],
        "duration_s": walk["duration_s"],
        "n_windows": n_windows,
        "own_recording": bool(walk["is_own_recording"]),
        "detections": sorted(by_species.values(), key=lambda d: -d["count"]),
        "weather_note": "",
        "scope": {
            "date": walk["started_at"],
            "location_filter": "on" if loc_on else "off",
            "threshold": walk_cfg.get("confidence_threshold", "?"),
        },
    }


def journal_for_walk(cfg: dict, walk_id: int, weather_note: str = "") -> tuple[str, str, str]:
    """Returns (markdown, provenance, model_used). Never raises on LLM failure (template fallback)."""
    log = build_log(cfg, walk_id)
    log["weather_note"] = weather_note
    from .journal import llm as _llm

    try:
        model = _llm.pick_model(cfg["llm_name"], timeout_s=5)
    except _llm.OllamaDown:
        model = cfg["llm_name"]  # writer will fall back to template and say so
    md, prov = _writer.write_journal(log, model, cfg["llm_timeout_s"])
    journals = Path("data/journals")
    journals.mkdir(parents=True, exist_ok=True)
    (journals / f"walk_{walk_id}.md").write_text(md)
    return md, prov, model
