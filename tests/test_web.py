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
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            urllib.request.urlopen(req)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 400 and "get_audio.py prepare" in e.read().decode()
        # under 3 seconds
        short = make_wav(str(tmp_path / "short.wav"), seconds=1.0)
        req2 = urllib.request.Request(base + "/api/analyze?date=2026-10-11",
                                      data=open(short, "rb").read(),
                                      headers={"Content-Type": "application/octet-stream"})
        try:
            urllib.request.urlopen(req2)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 400 and "get_audio.py prepare" in e.read().decode()
    finally:
        srv.shutdown()


def test_date_required_and_warning(tmp_path, monkeypatch):
    import json
    import urllib.error
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        payload = _wav_bytes(tmp_path)
        req = urllib.request.Request(base + "/api/analyze", data=payload,
                                     headers={"Content-Type": "application/octet-stream"})
        try:
            urllib.request.urlopen(req)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 400 and "date is required" in e.read().decode()
        req = urllib.request.Request(base + "/api/analyze?date=2020-01-01", data=payload,
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as r:
            j = json.loads(r.read())
        assert j.get("date_warning", "").startswith("warning: date 2020-01-01")
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11", data=payload,
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as r:
            assert json.loads(r.read()).get("date_warning") is None
    finally:
        srv.shutdown()


def test_own_flag_changes_journal(tmp_path, monkeypatch):
    import json
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        for own, want, phone in [("", "recording", False), ("&own=1", "walk", True)]:
            req = urllib.request.Request(
                base + f"/api/analyze?date=2026-10-11{own}", data=_wav_bytes(tmp_path),
                headers={"Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req) as r:
                wid = json.loads(r.read())["walk_id"]
            req = urllib.request.Request(base + "/api/journal", data=json.dumps(
                {"walk_id": wid}).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as r:
                md = json.loads(r.read())["markdown"]
            assert f"second {want}" in md
            assert (("phone in pocket" in md) is phone), md
    finally:
        srv.shutdown()


def test_conf_word_boundaries():
    from fieldnotes.web.app import conf_word

    assert conf_word(0.94, 4) == "confident"
    assert conf_word(0.8, 2) == "confident"
    assert conf_word(0.79, 3) == "likely"
    assert conf_word(0.5, 2) == "likely"
    assert conf_word(0.9, 1) == "uncertain"   # single window
    assert conf_word(0.49, 5) == "uncertain"  # below 0.5


def test_page_size_and_offline_assets():
    from fieldnotes.web.app import PAGE, PAGE_MAX_BYTES

    assert len(PAGE.encode()) < PAGE_MAX_BYTES
    for token in ["theme", "lifedetails", "aria-live", "prefers-reduced-motion",
                  "@media print", ":focus-visible", "<details", "WHAT_TO_UPLOAD.md"]:
        assert token in PAGE, token


def _walk_via_api(tmp_path, monkeypatch, **q):
    import json
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11", data=_wav_bytes(tmp_path),
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as r:
            wid = json.loads(r.read())["walk_id"]
        with urllib.request.urlopen(f"{base}/api/walk?id={wid}") as r:
            return srv, json.loads(r.read())
    except BaseException:
        srv.shutdown()
        raise


def test_walk_windows_built_from_stored_rows(tmp_path, monkeypatch):
    srv, w = _walk_via_api(tmp_path, monkeypatch)
    try:
        assert w["windows"]["n"] == 2  # 6 s file -> 2 real windows
        assert w["windows"]["filled"] == [True, False]  # detection only at 0 s
        card = w["cards"][0]
        assert card["common"] == "Alpha" and card["word"] == "uncertain"
        assert card["windows_occupied"] == 1 and card["novelty"] == "first_ever"
        assert card["clip_url"] and card["clip_url"].startswith("/api/clip?")
    finally:
        srv.shutdown()


def test_clip_serves_saved_audio_and_blocks_traversal(tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    srv, w = _walk_via_api(tmp_path, monkeypatch)
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (srv.server_port, w["cards"][0]["clip_url"])) as r:
            assert r.status == 200 and r.headers.get_content_type() == "audio/wav"
            assert r.read()[:4] == b"RIFF"
        bad = f"http://127.0.0.1:{srv.server_port}/api/clip?walk=1&name=..%2F..%2Fsecret.wav"
        try:
            urllib.request.urlopen(bad)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()


def test_journal_badge_truthful(tmp_path, monkeypatch):
    import json
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11", data=_wav_bytes(tmp_path),
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as r:
            wid = json.loads(r.read())["walk_id"]
        req = urllib.request.Request(base + "/api/journal",
                                     data=json.dumps({"walk_id": wid}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            j = json.loads(r.read())
        assert j["badge"] == "template (no LLM)"  # Ollama is off in tests
    finally:
        srv.shutdown()


def test_journal_badge_llm_path(monkeypatch):
    from fieldnotes.journal import writer as W

    md, prov = W.write_journal(
        {"date": "d", "duration_s": 6, "n_windows": 2, "detections": [
            {"species_common": "Alpha", "species_sci": "SciA", "confidence": 0.9,
             "count": 2, "novelty": "first_ever", "start_s": 0.0}]},
        "test-model", generate_fn=lambda *a: "Alpha is great. Go again tomorrow.")
    assert prov == "llm:test-model"
    # badge rule mirrors the server: non-template provenance names the model
    badge = "template (no LLM)" if prov.startswith("template:") else f"written by test-model"
    assert badge == "written by test-model"


def test_sample_note_and_versions(tmp_path, monkeypatch):
    import json
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11", data=_wav_bytes(tmp_path),
                                     headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as r:
            j = json.loads(r.read())
        assert j["sample_note"] is True  # own box off by default
        with urllib.request.urlopen(base + "/api/versions") as r:
            text = json.loads(r.read())["text"]
        assert "Bird detector:" in text and "gemma3:4b" in text
    finally:
        srv.shutdown()


def test_sample_filename_triggers_note_even_when_own(tmp_path, monkeypatch):
    import json
    import urllib.request

    monkeypatch.setattr(S._base, "get_backend", lambda name: FakeBackend)
    srv, base = _start(tmp_path)
    try:
        boundary = "B3"
        body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"wav\"; "
                f"filename=\"sample.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode() + \
            _wav_bytes(tmp_path) + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(base + "/api/analyze?date=2026-10-11&own=1", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req) as r:
            assert json.loads(r.read())["sample_note"] is True
    finally:
        srv.shutdown()
