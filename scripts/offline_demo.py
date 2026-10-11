"""Offline demo: analyze -> journal on the bundled sample with external network blocked.

What is blocked: every TCP connect to a NON-localhost host raises (and is counted).
What stays open: localhost (127.0.0.1 / ::1) — Ollama is a local service, and the
web UI is localhost-only by design. Localhost traffic never leaves the device.
Exits non-zero on any external connection attempt or any pipeline error.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_BLOCKED: list = []
_real_connect = socket.socket.connect


def _guarded_connect(self, addr):
    host = addr[0] if isinstance(addr, tuple) else addr
    if host in ("127.0.0.1", "localhost", "::1"):
        return _real_connect(self, addr)
    _BLOCKED.append(str(host))
    raise ConnectionError(f"offline-demo: external connection blocked (tried {host})")


socket.socket.connect = _guarded_connect  # noqa: E402 — must precede any network use


def main() -> int:
    from fieldnotes import service as S
    from fieldnotes.config import load_config

    cfg = load_config("config.yaml")
    fixture = os.path.join(
        os.path.dirname(__file__), "..", ".venv", "lib",
        "python3.12", "site-packages", "birdnet_analyzer",
        "checkpoints", "V2.4", "BirdNET_GLOBAL_6K_V2.4_Model_TFJS",
        "static", "sample.wav",
    )
    fixture = os.path.normpath(fixture)
    if not os.path.isfile(fixture):
        print("offline-demo FAILED: fixture missing: " + fixture)
        return 1
    with tempfile.TemporaryDirectory(prefix="fieldnotes-demo-") as tmp:
        cfg = dict(cfg)
        cfg["database"] = os.path.join(tmp, "demo.db")
        cfg["clips_dir"] = os.path.join(tmp, "clips")
        try:
            summary = S.analyze_walk(fixture, cfg, date="2026-10-11")
        except ValueError as exc:
            print(f"offline-demo FAILED during analyze (is the BirdNET model downloaded? "
                  f"run `make setup` once): {exc}")
            return 1
        try:
            md, prov, model = S.journal_for_walk(cfg, summary["walk_id"])
        except ValueError as exc:
            print(f"offline-demo FAILED during journal: {exc}")
            return 1
    if _BLOCKED:
        print(f"offline-demo FAILED: {_BLOCKED!r} external connection attempts were made.")
        return 1
    print(f"analyzed {summary['n_windows']} windows -> "
          f"{summary['n_detections']} detections "
          f"({', '.join(s['common'] for s in summary['species']) or 'none'})")
    print(f"journal [{prov}] ({len(md)} chars), external connection attempts: 0")
    print("OFFLINE DEMO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
