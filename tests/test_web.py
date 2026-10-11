"""Web UI smoke test against a live localhost server (FakeBackend, template journal)."""
import io
import json
import threading
import urllib.request
from http.server import HTTPServer

from fieldnotes import service as S
from fieldnotes.config import DEFAULTS
from fieldnotes.detect.base import Detection
from fieldnotes.web.app import Handler


class FakeBackend:
    MODEL_VERSION = "web-test"

    @staticmethod
    def analyze_file(path, **kw):
        return [Detection("Alpha", "SciA", 0.9, 0.0, 3.0)]


def _start(tmp_path):
    cfg = dict(DEFAULTS)
    cfg["database"] = str(tmp_path / "w.db")
    cfg["clips_dir"] = str(tmp_path / "clips")
    Handler.cfg = cfg
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


def _post(url, body: bytes, ctype: str):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": ctype})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


def test_web_flow(tmp_path, monkeypatch):
    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        with urllib.request.urlopen(base + "/") as r:
            assert r.status == 200 and "Field Notes" in r.read().decode()
        wav = make_wav(str(tmp_path / "u.wav"), seconds=6.0)
        raw = open(wav, "rb").read()
        boundary = "BOUNDARY"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"wav\"; "
                f"filename=\"u.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode() + raw + \
            f"\r\n--{boundary}--\r\n".encode()
        st, j = _post(base + "/api/analyze?date=2026-10-11",
                      body, f"multipart/form-data; boundary={boundary}")
        assert st == 200 and j["walk_id"] == 1 and j["n_detections"] == 1
        st, j = _post(base + "/api/journal", json.dumps({"walk_id": 1}).encode(),
                      "application/json")
        assert st == 200 and "Alpha" in j["markdown"] and j["provenance"].startswith("template:")
        with urllib.request.urlopen(base + "/api/life") as r:
            life = json.loads(r.read())
        assert [x["species_sci"] for x in life] == ["SciA"]
        with urllib.request.urlopen(base + "/api/export?id=1&fmt=csv") as r:
            assert "SciA" in r.read().decode()
        st, j = _post(base + "/api/wipe", b"", "application/json")
        assert st == 200 and j["ok"] is True
        with urllib.request.urlopen(base + "/api/life") as r:
            assert json.loads(r.read()) == []
    finally:
        srv.shutdown()
