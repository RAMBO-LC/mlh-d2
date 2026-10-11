"""Offline proof at test level: with external sockets blocked, the file->DB->journal
path works and attempts zero external connections (localhost Ollama allowed by design)."""
import socket

import pytest

from fieldnotes import service as S
from fieldnotes.config import DEFAULTS
from fieldnotes.detect.base import Detection


class OfflineBackend:
    MODEL_VERSION = "offline-test"

    @staticmethod
    def analyze_file(path, **kw):
        return [Detection("Alpha", "SciA", 0.9, 0.0, 3.0)]


@pytest.fixture
def no_external_network(monkeypatch):
    real_connect = socket.socket.connect
    attempts: list = []

    def guarded(self, addr):
        host = addr[0] if isinstance(addr, tuple) else addr
        if host in ("127.0.0.1", "localhost", "::1"):
            return real_connect(self, addr)
        attempts.append(host)
        raise ConnectionError(f"network blocked in test (tried {host})")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    return attempts


def test_pipeline_runs_with_external_network_blocked(tmp_path, monkeypatch, no_external_network):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: OfflineBackend)
    cfg = dict(DEFAULTS)
    cfg["database"] = str(tmp_path / "o.db")
    cfg["clips_dir"] = str(tmp_path / "clips")
    wav = make_wav(str(tmp_path / "w.wav"), seconds=6.0)
    summary = S.analyze_walk(wav, cfg, date="2026-10-11")
    assert summary["n_detections"] == 1
    # Ollama is down in this sandbox -> template fallback, never a crash, never external net
    md, prov, model = S.journal_for_walk(cfg, summary["walk_id"])
    assert prov.startswith("template:") and "Alpha" in md
    assert no_external_network == [], f"external connections attempted: {no_external_network}"


def test_deliberate_external_attempt_fails(no_external_network):
    import socket

    with __import__("pytest").raises(ConnectionError, match="network blocked"):
        socket.create_connection(("203.0.11.99", 80), timeout=2)
    assert no_external_network == ["203.0.11.99"]
