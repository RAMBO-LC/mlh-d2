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
