import numpy as np

from fieldnotes.audio import windows as W


def test_window_counts_no_overlap(tmp_path):
    p = str(tmp_path / "a.wav")
    from .helpers import make_wav

    make_wav(p, seconds=9.0)
    audio, sr = W.load_mono(p)
    assert sr == 48000
    wins = W.make_windows(audio, sr, 3.0, 0.0)
    assert len(wins) == 3
    assert [(w.start_s, w.end_s) for w in wins] == [(0.0, 3.0), (3.0, 6.0), (6.0, 9.0)]
    assert all(w.kept for w in wins)


def test_trailing_partial_window_dropped(tmp_path):
    from .helpers import make_wav

    p = make_wav(str(tmp_path / "b.wav"), seconds=7.0)
    audio, sr = W.load_mono(p)
    assert len(W.make_windows(audio, sr, 3.0, 0.0)) == 2  # 1s tail dropped


def test_overlap_doubles_windows(tmp_path):
    from .helpers import make_wav

    p = make_wav(str(tmp_path / "c.wav"), seconds=9.0)
    audio, sr = W.load_mono(p)
    wins = W.make_windows(audio, sr, 3.0, 1.5)
    assert len(wins) == 5
    assert wins[1].start_s == 1.5


def test_silence_gated_but_listed(tmp_path):
    from .helpers import make_silence

    p = make_silence(str(tmp_path / "s.wav"), seconds=6.0)
    audio, sr = W.load_mono(p)
    wins = W.make_windows(audio, sr, 3.0, 0.0)
    assert len(wins) == 2
    assert not any(w.kept for w in wins)


def test_resample_44100_to_48000(tmp_path):
    import soundfile as sf

    sr0 = 44100
    t = np.arange(3 * sr0) / sr0
    sf.write(str(tmp_path / "r.wav"), (0.2 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32), sr0)
    audio, sr = W.load_mono(str(tmp_path / "r.wav"))
    assert sr == 48000
    assert abs(len(audio) / 48000 - 3.0) < 0.05


def test_bad_file_readable_error(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="could not read audio file"):
        W.load_mono(str(tmp_path / "missing.wav"))
