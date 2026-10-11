"""Offline tests for scripts/get_audio.py. The network is always mocked."""
import importlib.util
import json
import math
import struct
import sys
import wave
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "get_audio.py"
spec = importlib.util.spec_from_file_location("get_audio", SCRIPT)
ga = importlib.util.module_from_spec(spec)
sys.modules["get_audio"] = ga
spec.loader.exec_module(ga)


def make_wav(path: Path, seconds: float, rate: int = 44100, channels: int = 2) -> Path:
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) * channels
            for i in range(n)
        )
        w.writeframes(frames)
    return path


@pytest.fixture(autouse=True)
def isolate_data(tmp_path, monkeypatch):
    monkeypatch.setattr(ga, "DATA", tmp_path / "data")
    monkeypatch.setattr(ga, "SAMPLES", tmp_path / "data" / "samples")
    monkeypatch.setattr(ga, "WALKS", tmp_path / "data" / "walks")
    monkeypatch.setattr(ga, "SOURCES", tmp_path / "data" / "samples" / "SOURCES.json")
    monkeypatch.delenv("XENO_CANTO_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)


def test_prepare_converts_to_48k_mono(tmp_path):
    src = make_wav(tmp_path / "walk.wav", 4.0, rate=44100, channels=2)
    assert ga.main(["prepare", str(src)]) == 0
    out = ga.WALKS / "walk_48k.wav"
    info = ga.describe_wav(out)
    assert info["sample_rate"] == 48000 and info["channels"] == 1
    assert 3.9 < info["seconds"] < 4.1


def test_prepare_trim(tmp_path):
    src = make_wav(tmp_path / "long.wav", 10.0, rate=48000, channels=1)
    ga.main(["prepare", str(src), "--start", "2", "--max-seconds", "5"])
    info = ga.describe_wav(ga.WALKS / "long_48k.wav")
    assert 4.9 < info["seconds"] < 5.1


def test_short_clip_is_flagged(tmp_path):
    src = make_wav(tmp_path / "short.wav", 1.0, rate=48000, channels=1)
    info = ga.describe_wav(src)
    assert any("TOO SHORT" in n for n in ga.verdict(info))


def test_check_ok_and_not_ok(tmp_path):
    good = make_wav(tmp_path / "good.wav", 4.0, rate=48000, channels=1)
    bad = make_wav(tmp_path / "bad.wav", 4.0, rate=44100, channels=2)
    assert ga.main(["check", str(good)]) == 0
    assert ga.main(["check", str(bad)]) == 1


def test_missing_and_corrupt_files_give_readable_errors(tmp_path, capsys):
    assert ga.main(["prepare", str(tmp_path / "nope.mp3")]) == 2
    corrupt = tmp_path / "x.wav"
    corrupt.write_bytes(b"not audio at all")
    assert ga.main(["check", str(corrupt)]) == 2
    assert "error:" in capsys.readouterr().err


def test_xc_without_key_explains_how_to_get_one(capsys):
    assert ga.main(["xc", "476378"]) == 2
    err = capsys.readouterr().err
    assert "API key" in err and "manual" in err.lower()


def test_load_key_priority(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("XENO_CANTO_API_KEY=fromfile\n")
    assert ga.load_key(None) == "fromfile"
    monkeypatch.setenv("XENO_CANTO_API_KEY", "fromenv")
    assert ga.load_key(None) == "fromenv"
    assert ga.load_key("fromcli") == "fromcli"


def test_nd_licence_refused(monkeypatch, capsys):
    meta = {"recordings": [{"lic": "//creativecommons.org/licenses/by-nc-nd/4.0/",
                            "file": "https://example.invalid/x.mp3", "rec": "A", "en": "Bird"}]}
    monkeypatch.setattr(ga, "http_get", lambda url, timeout=60: json.dumps(meta).encode())
    assert ga.main(["xc", "1", "--key", "SECRETKEY"]) == 2
    assert "NoDerivs" in capsys.readouterr().err


def test_xc_happy_path_mocked(tmp_path, monkeypatch, capsys):
    mp3_like = make_wav(tmp_path / "fake_source.wav", 5.0, rate=44100, channels=2).read_bytes()
    meta = {"recordings": [{"lic": "//creativecommons.org/licenses/by-sa/4.0/",
                            "file": "//example.invalid/XC1.mp3", "rec": "Jane Doe",
                            "en": "Asian Koel"}]}

    def fake_get(url, timeout=60):
        return json.dumps(meta).encode() if "api/3" in url else mp3_like

    monkeypatch.setattr(ga, "http_get", fake_get)
    assert ga.main(["xc", "XC476378", "--key", "SECRETKEY"]) == 0
    out = capsys.readouterr()
    assert "SECRETKEY" not in out.out + out.err  # key is never printed
    sources = json.loads(ga.SOURCES.read_text())
    assert sources[0]["ground_truth_label"] == "Asian Koel"
    assert "SECRETKEY" not in ga.SOURCES.read_text()
    assert sources[0]["is_my_recording"] is False
    assert ga.describe_wav(ga.SAMPLES / "XC476378.wav")["sample_rate"] == 48000
