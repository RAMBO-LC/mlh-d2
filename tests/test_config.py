import pytest

from fieldnotes.config import DEFAULTS, load_config


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return str(p)


def test_defaults_used_for_empty_file(tmp_path):
    cfg = load_config(_write(tmp_path, "{}\n"))
    assert cfg == DEFAULTS
    assert cfg["privacy"]["gps_enabled"] is False
    assert cfg["llm_name"] == "gemma3:4b"


def test_missing_file_readable_error(tmp_path):
    with pytest.raises(ValueError, match="config file not found"):
        load_config(str(tmp_path / "nope.yaml"))


def test_bad_threshold_rejected(tmp_path):
    with pytest.raises(ValueError, match="confidence_threshold"):
        load_config(_write(tmp_path, "confidence_threshold: 1.5\n"))


def test_unknown_backend_rejected(tmp_path):
    with pytest.raises(ValueError, match="not available"):
        load_config(_write(tmp_path, "bird_backend: perch\n"))


def test_bad_week_rejected(tmp_path):
    with pytest.raises(ValueError, match="week_override"):
        load_config(_write(tmp_path, "week_override: 99\n"))


def test_overlap_must_be_less_than_window(tmp_path):
    with pytest.raises(ValueError, match="overlap"):
        load_config(_write(tmp_path, "window_s: 3.0\noverlap_s: 3.0\n"))


def test_partial_override_keeps_defaults(tmp_path):
    cfg = load_config(_write(tmp_path, "confidence_threshold: 0.5\nprivacy:\n  gps_enabled: true\n"))
    assert cfg["confidence_threshold"] == 0.5
    assert cfg["privacy"] == {"gps_enabled": True, "save_clips": True}
    assert cfg["window_s"] == 3.0


def test_local_yaml_overrides_region(tmp_path):
    base = _write(tmp_path, "region_lat: 0.0\nregion_lon: 0.0\n")
    (tmp_path / "config.local.yaml").write_text("region_lat: 12.9\nregion_lon: 77.5\n")
    cfg = load_config(base)
    assert (cfg["region_lat"], cfg["region_lon"]) == (12.9, 77.5)


def test_no_local_yaml_keeps_base(tmp_path):
    cfg = load_config(_write(tmp_path, "region_lat: 1.0\n"))
    assert cfg["region_lat"] == 1.0
