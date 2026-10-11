"""Service + backend-swap: FakeBackend proves config swap needs no code change."""
import os

import pytest

from fieldnotes import service as S
from fieldnotes.config import DEFAULTS
from fieldnotes.detect.base import Detection, get_backend


class FakeBackend:
    MODEL_VERSION = "fake-1.0"

    @staticmethod
    def analyze_file(path, **kw):
        assert os.path.isfile(path)
        FakeBackend.seen_kwargs = kw
        return [Detection("Alpha", "SciA", 0.9, 0.0, 3.0),
                Detection("Alpha", "SciA", 0.8, 60.0, 63.0),
                Detection("Beta", "SciB", 0.4, 120.0, 123.0)]


def _cfg(tmp_path, **over):
    cfg = dict(DEFAULTS)
    cfg.update(over)
    cfg["database"] = str(tmp_path / "f.db")
    cfg["clips_dir"] = str(tmp_path / "clips")
    return cfg


def test_get_backend_birdnet_has_analyze_file():
    mod = get_backend("birdnet")
    assert callable(mod.analyze_file) and isinstance(mod.MODEL_VERSION, str)


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError, match="not available"):
        get_backend("perch")


def test_analyze_walk_fake_backend(tmp_path, monkeypatch):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    wav = make_wav(str(tmp_path / "walk.wav"), seconds=130.0)
    summary = S.analyze_walk(wav, _cfg(tmp_path), lat=1.0, lon=2.0, date="2026-10-11")
    assert summary["n_windows"] == 43 and summary["n_detections"] == 3
    kinds = [s["novelty"] for s in summary["species"]]
    assert kinds == ["first_ever", "repeat", "first_ever"]
    assert FakeBackend.seen_kwargs["lat"] == 1.0
    assert FakeBackend.seen_kwargs["week"] == S.iso_to_birdnet_week("2026-10-11")
    # clips saved for the two firsts, life list has both species
    clips = list((tmp_path / "clips").rglob("*.wav"))
    assert len(clips) == 2
    from fieldnotes.store import db

    con = db.connect(_cfg(tmp_path)["database"])
    try:
        assert {r["species_sci"] for r in db.life_list(con)} == {"SciA", "SciB"}
    finally:
        con.close()


def test_second_walk_marks_first_this_walk(tmp_path, monkeypatch):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    cfg = _cfg(tmp_path)
    wav = make_wav(str(tmp_path / "w.wav"), seconds=130.0)
    S.analyze_walk(wav, cfg, date="2026-10-11")
    summary2 = S.analyze_walk(wav, cfg, date="2026-10-11")
    assert [s["novelty"] for s in summary2["species"]] == [
        "first_this_walk", "repeat", "first_this_walk"]


def test_geo_defaults_to_no_filter_without_opt_in(tmp_path):
    cfg = _cfg(tmp_path)
    assert S.resolve_geo(cfg, None, None) == (-1, -1)
    assert S.resolve_geo(cfg, 1.0, 2.0) == (1.0, 2.0)
    cfg["privacy"]["gps_enabled"] = True
    assert S.resolve_geo(cfg, None, None) == (cfg["region_lat"], cfg["region_lon"])


def test_bad_week_date_rejected():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        S.iso_to_birdnet_week("yesterday")


def test_missing_wav_readable_error(tmp_path, monkeypatch):
    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    with pytest.raises(ValueError, match="could not read audio file"):
        S.analyze_walk(str(tmp_path / "nope.wav"), _cfg(tmp_path))


class ThresholdBackend:
    MODEL_VERSION = "thr-1.0"

    @staticmethod
    def analyze_file(path, **kw):
        return [Detection("At", "SciAt", 0.30, 0.0, 3.0),
                Detection("Above", "SciAbove", 0.3001, 3.0, 6.0),
                Detection("Below", "SciBelow", 0.2999, 6.0, 9.0)]


def test_threshold_boundaries(tmp_path, monkeypatch):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: ThresholdBackend)
    cfg = _cfg(tmp_path)  # threshold 0.3
    wav = make_wav(str(tmp_path / "t.wav"), seconds=12.0)
    summary = S.analyze_walk(wav, cfg, date="2026-10-11")
    kept = {s["common"] for s in summary["species"]}
    assert kept == {"At", "Above"}, f"exactly-at and above kept, below dropped, got {kept}"


def test_walk2_second_hearing_is_repeat(tmp_path, monkeypatch):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    cfg = _cfg(tmp_path)
    wav = make_wav(str(tmp_path / "w.wav"), seconds=130.0)
    S.analyze_walk(wav, cfg, date="2026-10-11")
    s2 = S.analyze_walk(wav, cfg, date="2026-10-11")
    assert [s["novelty"] for s in s2["species"]][0] == "first_this_walk"


def _expect_user_error(tmp_path, monkeypatch, filename: str, content: bytes):
    import subprocess

    p = tmp_path / filename
    p.write_bytes(content)
    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    with __import__("pytest").raises(ValueError, match="(?i)(could not read|too small|too short|empty)"):
        S.analyze_walk(str(p), _cfg(tmp_path))


def test_corrupt_wav_readable_error(tmp_path, monkeypatch):
    _expect_user_error(tmp_path, monkeypatch, "bad.wav", b"this is not audio" * 100)


def test_zero_length_file_readable_error(tmp_path, monkeypatch):
    _expect_user_error(tmp_path, monkeypatch, "empty.wav", b"")


def test_under_3s_readable_error(tmp_path, monkeypatch):
    from .helpers import make_wav

    p = make_wav(str(tmp_path / "short.wav"), seconds=1.0)
    import pytest

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    with pytest.raises(ValueError, match="at least one 3s window"):
        S.analyze_walk(p, _cfg(tmp_path))


def test_stereo_44100hz_accepted(tmp_path, monkeypatch):
    import numpy as np
    import soundfile as sf

    sr, n = 44100, 44100 * 6
    t = np.arange(n) / sr
    stereo = np.stack([0.2 * np.sin(2 * np.pi * 2000 * t)] * 2, axis=1).astype(np.float32)
    p = str(tmp_path / "st.wav")
    sf.write(p, stereo, sr)
    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    summary = S.analyze_walk(p, _cfg(tmp_path), date="2026-10-11")
    assert summary["n_windows"] == 2


def test_cli_never_shows_traceback(tmp_path, monkeypatch, capsys):
    import pytest

    from fieldnotes.cli import main

    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(f"database: {tmp_path}/c.db\nclips_dir: {tmp_path}/cl\n")
    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    with pytest.raises(SystemExit) as ei:
        main(["--config", str(cfg_path), "analyze", str(tmp_path / "missing.wav")])
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err and "analyze failed:" in err


def test_iso_week_mapping_boundaries():
    assert S.iso_to_birdnet_week("2026-01-01") == 1      # ISO week 1 -> BirdNET 1
    assert S.iso_to_birdnet_week("2026-10-11") == 38     # observed in production runs
    assert S.iso_to_birdnet_week("2026-12-27") == 48     # ISO week 52 clamps to 48
    assert S.iso_to_birdnet_week("2020-12-31") == 48     # ISO week 53 clamps to 48


def test_parse_real_birdnet_csv_and_empty(tmp_path):
    from fieldnotes.detect import birdnet as B

    # Real output captured from the bundled sample.wav run, 2026-10-11.
    csv_text = ("Start (s),End (s),Scientific name,Common name,Confidence,File\n"
                "0.0,3.0,Acanthis cabaret,Lesser Redpoll,0.9444,/tmp/bird_sample.wav\n"
                "0.0,3.0,Acanthis flammea,Common Redpoll,0.7997,/tmp/bird_sample.wav\n"
                "0.0,3.0,Acanthis hornemanni,Hoary Redpoll,0.059,/tmp/bird_sample.wav\n")
    p = tmp_path / "r.BirdNET.results.csv"
    p.write_text(csv_text)
    dets = B._parse_csv(str(p))
    assert [(d.species_common, d.confidence) for d in dets] == [
        ("Lesser Redpoll", 0.9444), ("Common Redpoll", 0.7997), ("Hoary Redpoll", 0.059)]
    assert dets[0].start_s == 0.0 and dets[0].end_s == 3.0
    empty = tmp_path / "e.BirdNET.results.csv"
    empty.write_text("Start (s),End (s),Scientific name,Common name,Confidence,File\n")
    assert B._parse_csv(str(empty)) == []
