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


def test_html_has_no_external_references():
    from fieldnotes.web.app import PAGE

    import re

    assert "http://127" not in PAGE and "https://" not in PAGE, \
        "page must not reference external assets"
    assert not re.search(r'https?://(?!127\.0\.0\.1)', PAGE)


def test_server_binds_localhost_only(tmp_path):
    import threading
    from http.server import HTTPServer

    from fieldnotes.web.app import Handler

    Handler.cfg = {"database": str(tmp_path / "x.db"), "clips_dir": str(tmp_path / "c")}
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.shutdown()


def test_exports_match_db(tmp_path, monkeypatch):
    import csv
    import io
    import urllib.request

    from fieldnotes.store import db

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        with urllib.request.urlopen(base + "/api/analyze?date=2026-10-11",
                                    data=_wav_bytes(tmp_path)) as r:
            j = __import__("json").loads(r.read())
        con = db.connect(str(tmp_path / "w.db"))
        try:
            rows = db.walk_detections(con, j["walk_id"])
        finally:
            con.close()
        with urllib.request.urlopen(base + f"/api/export?id={j['walk_id']}&fmt=csv") as r:
            exported = list(csv.DictReader(io.StringIO(r.read().decode())))
        assert len(exported) == len(rows) == 1
        assert exported[0]["scientific"] == rows[0]["species_sci"]
        assert float(exported[0]["confidence"]) == rows[0]["confidence"]
        with urllib.request.urlopen(base + f"/api/export?id={j['walk_id']}&fmt=md") as r:
            md = r.read().decode()
        assert "Alpha" in md and "## Detections" in md
    finally:
        srv.shutdown()


def _wav_bytes(tmp_path):
    from .helpers import make_wav

    p = make_wav(str(tmp_path / "u.wav"), seconds=6.0)
    return open(p, "rb").read()


def test_bad_upload_gives_4xx_with_message(tmp_path, monkeypatch):
    import urllib.error

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        for body, ctype in [(b"", "application/octet-stream"),
                            (b"not audio at all" * 10, "application/octet-stream")]:
            req = urllib.request.Request(base + "/api/analyze", data=body,
                                         headers={"Content-Type": ctype})
            try:
                urllib.request.urlopen(req)
                raise AssertionError("expected HTTPError")
            except urllib.error.HTTPError as e:
                assert 400 <= e.code < 500
                assert "error" in e.read().decode().lower()
    finally:
        srv.shutdown()


def test_upload_hint_present_and_offline():
    from fieldnotes.web.app import PAGE

    assert "48 kHz mono WAV" in PAGE and "get_audio.py prepare" in PAGE
    assert "WHAT_TO_UPLOAD.md" in PAGE


def test_unfriendly_files_point_to_prepare(tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    from .helpers import make_wav

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        # not a WAV (mp3 suffix via multipart)
        boundary = "B2"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"wav\"; "
                f"filename=\"song.mp3\"\r\nContent-Type: audio/mpeg\r\n\r\n").encode() + \
            b"\x00" * 2000 + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(base + "/api/analyze", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            urllib.request.urlopen(req)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 400 and "get_audio.py prepare" in e.read().decode()
        # under 3 seconds
        short = make_wav(str(tmp_path / "short.wav"), seconds=1.0)
        req2 = urllib.request.Request(base + "/api/analyze", data=open(short, "rb").read(),
                                      headers={"Content-Type": "application/octet-stream"})
        try:
            urllib.request.urlopen(req2)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 400 and "get_audio.py prepare" in e.read().decode()
    finally:
        srv.shutdown()
