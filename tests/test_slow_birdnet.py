"""Slow tests: real BirdNET model on the bundled sample. Needs the model downloaded
(`make setup`) but no network and no Ollama. Run with `make test-slow`.

Expectations below describe the *pipeline* on the vendor's own sample file, observed
2026-10-11 (Lesser Redpoll top-1 at 0.94 without location filter; fully excluded by
the (0,0) species list). They are characterization, not eval ground truth — eval
labels must still come from a human or documented source (see eval/)."""
import os

import pytest

pytestmark = pytest.mark.slow

SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", ".venv", "lib", "python3.12", "site-packages",
    "birdnet_analyzer", "checkpoints", "V2.4",
    "BirdNET_GLOBAL_6K_V2.4_Model_TFJS", "static", "sample.wav",
)

from fieldnotes import service as S  # noqa: E402
from fieldnotes.config import DEFAULTS  # noqa: E402


def _cfg(tmp_path):
    cfg = dict(DEFAULTS)
    cfg["database"] = str(tmp_path / "s.db")
    cfg["clips_dir"] = str(tmp_path / "clips")
    return cfg


def test_sample_with_generic_location_yields_zero(tmp_path):
    if not os.path.isfile(SAMPLE):
        pytest.skip("BirdNET model/sample not downloaded (run `make setup`)")
    summary = S.analyze_walk(SAMPLE, _cfg(tmp_path), lat=0.0, lon=0.0, date="2026-10-11")
    assert summary["n_detections"] == 0


def test_sample_without_location_yields_redpolls(tmp_path):
    if not os.path.isfile(SAMPLE):
        pytest.skip("BirdNET model/sample not downloaded (run `make setup`)")
    summary = S.analyze_walk(SAMPLE, _cfg(tmp_path), date="2026-10-11")
    names = {s["common"] for s in summary["species"]}
    assert len(summary["species"]) >= 2
    assert any("Redpoll" in n for n in names)
    top = max(summary["species"], key=lambda s: s["confidence"])
    assert top["confidence"] > 0.5
