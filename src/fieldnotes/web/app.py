"""Minimal local web UI: stdlib http.server, one page, no external assets, localhost only."""
from __future__ import annotations

import cgi
import csv
import io
import json
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MAX_UPLOAD_BYTES = 200 * 1024 * 1024

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Field Notes — walk recap</title>
<style>
body{background:#111;color:#f2f2f2;font-family:system-ui,sans-serif;max-width:44rem;margin:auto;padding:1rem;line-height:1.5}
h1{font-size:2rem}h2{font-size:1.4rem;margin-top:2rem}
input,button,select{font-size:1.1rem;padding:.5rem;margin:.25rem 0}
button{background:#ffd54a;border:0;border-radius:.4rem;padding:.6rem 1rem;cursor:pointer}
button.danger{background:#e06060;color:#fff}
table{border-collapse:collapse;width:100%;font-size:1.05rem}
td,th{border:1px solid #555;padding:.4rem;text-align:left}
pre{white-space:pre-wrap;background:#1d1d1d;padding:1rem;border-radius:.4rem}
.badge{border:1px solid #ffd54a;border-radius:.3rem;padding:0 .4rem;font-size:.85rem}
label{display:block;margin-top:.5rem}
</style></head><body>
<h1>Field Notes</h1>
<p>Screen is for setup + recap only. Go outside; the pocket does the work.</p>
<h2>1. Analyze a walk</h2>
<p><em>Tip: upload a 48 kHz mono WAV at least 3 s long. Anything else? Run
<code>python scripts/get_audio.py prepare YOURFILE</code> first — see docs/WHAT_TO_UPLOAD.md in the repo.</em></p>
<form id="up" aria-label="Upload a walk recording">
<label>Recording (WAV) <input type="file" name="wav" accept=".wav,.flac,.ogg" required></label>
<label>Date <input type="date" name="date"></label>
<label>Lat <input type="text" name="lat" inputmode="decimal" placeholder="optional"></label>
<label>Lon <input type="text" name="lon" inputmode="decimal" placeholder="optional"></label>
<label>Weather note <input type="text" name="weather" placeholder="cool, overcast…"></label>
<button type="submit">Analyze</button>
</form>
<div id="res" role="status"></div>
<h2>2. Journal</h2>
<div id="journal"><p>No journal yet — analyze a walk first.</p></div>
<h2>3. Life list</h2>
<div id="life"></div>
<h2>4. Export / danger zone</h2>
<p><button id="expMd">Export journal (.md)</button> <button id="expCsv">Export detections (.csv)</button></p>
<p><button id="wipe" class="danger">Delete all data</button></p>
<script>
let walkId=null;
const $=id=>document.getElementById(id);
function num(v){const f=parseFloat(v);return isFinite(f)?f:null;}
$("up").onsubmit=async e=>{e.preventDefault();
  $("res").textContent="Analyzing locally… (model runs on this machine)";
  const fd=new FormData(e.target);
  const lat=num(fd.get("lat")), lon=num(fd.get("lon"));
  const q=new URLSearchParams({date:fd.get("date")||"",weather:fd.get("weather")||"",
    lat:lat===null?"":lat,lon:lon===null?"":lon});
  const r=await fetch("/api/analyze?"+q,{method:"POST",body:fd.get("wav")});
  const j=await r.json();
  if(!r.ok){$("res").textContent="Error: "+(j.error||r.status);return;}
  walkId=j.walk_id;
  $("res").innerHTML=`<p>Walk ${j.walk_id}: <strong>${j.n_detections}</strong> detections. `+
    j.species.map(s=>`${s.common} <span class="badge">${s.novelty}</span> (${s.confidence.toFixed(2)})`).join(", ")+"</p>";
  journal();life();
};
async function journal(){if(walkId===null)return;
  const r=await fetch("/api/journal",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({walk_id:walkId})});
  const j=await r.json();
  $("journal").innerHTML="<pre>"+j.markdown.replace(/</g,"&lt;")+"</pre><p><em>"+j.provenance+" · "+j.model+"</em></p>";
}
async function life(){const r=await fetch("/api/life");const j=await r.json();
  $("life").innerHTML=j.length?("<table><tr><th>Species</th><th>First seen</th></tr>"+
    j.map(x=>`<tr><td>${x.species_common} (${x.species_sci})</td><td>${x.first_seen}</td></tr>`).join("")+"</table>"):"<p>Life list is empty.</p>";
}
$("expMd").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=md";};
$("expCsv").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=csv";};
$("wipe").onclick=async()=>{if(!confirm("Delete ALL local data (database + clips)?"))return;
  const r=await fetch("/api/wipe",{method:"POST"});const j=await r.json();
  alert(j.ok?"Deleted.":"Error: "+j.error);walkId=null;life();$("journal").innerHTML="";$("res").textContent="";};
life();
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    cfg = None  # set by serve()
    server_version = "FieldNotes/0"

    def log_message(self, *a):  # quieter logs
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from ..store import db as _db

        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/life":
            con = _db.connect(self.cfg["database"])
            try:
                return self._json([dict(r) for r in _db.life_list(con)])
            finally:
                con.close()
        if u.path == "/api/export":
            return self._export(int(q.get("id", [0])[0]), q.get("fmt", ["md"])[0])
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_UPLOAD_BYTES:
            return self._json({"error": "file too large (200 MB cap)"}, 413)
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/analyze":
            return self._analyze(q, self.rfile.read(length))
        if u.path == "/api/journal":
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json({"error": "body must be JSON {walk_id, weather?}"}, 400)
            return self._journal(payload)
        if u.path == "/api/wipe":
            from ..store import db as _db

            _db.wipe_all(self.cfg["database"], self.cfg["clips_dir"])
            return self._json({"ok": True})
        self._json({"error": "not found"}, 404)

    def _analyze(self, q, raw: bytes):
        from .. import service as _svc

        ctype = self.headers.get("Content-Type", "")
        filename = "upload.wav"
        if "multipart" in ctype:  # browser form upload
            form = cgi.FieldStorage(fp=io.BytesIO(raw), headers=self.headers,
                                    environ={"REQUEST_METHOD": "POST"})
            if "wav" not in form or not getattr(form["wav"], "file", None):
                return self._json({"error": "no 'wav' file in upload"}, 400)
            item = form["wav"]
            filename = Path(item.filename or "upload.wav").name
            raw = item.file.read()
        if len(raw) < 1000:
            return self._json({"error": "uploaded file is empty or too small"}, 400)
        suffix = Path(filename).suffix.lower() or ".wav"
        if suffix not in (".wav", ".flac", ".ogg"):
            return self._json({"error": f"unsupported audio type {suffix!r}: upload a WAV "
                                        "(see docs/WHAT_TO_UPLOAD.md), or convert it first with "
                                        "`python scripts/get_audio.py prepare <file>`"}, 400)

        def f(v):
            try:
                return float(v[0]) if v and v[0] not in ("", None) else None
            except (ValueError, TypeError):
                return None

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(raw)
            tmp = tf.name
        try:
            try:
                summary = _svc.analyze_walk(
                    tmp, self.cfg,
                    lat=f(q.get("lat")), lon=f(q.get("lon")),
                    date=(q.get("date", [""])[0] or None),
                    weather_note=(q.get("weather", [""])[0] or ""),
                )
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)
        finally:
            Path(tmp).unlink(missing_ok=True)
        return self._json(summary)

    def _journal(self, payload):
        from .. import service as _svc

        try:
            walk_id = int(payload.get("walk_id", 0))
        except (ValueError, TypeError):
            return self._json({"error": "walk_id must be an integer"}, 400)
        try:
            md, prov, model = _svc.journal_for_walk(
                self.cfg, walk_id, str(payload.get("weather", "") or ""))
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        return self._json({"markdown": md, "provenance": prov, "model": model})

    def _export(self, walk_id: int, fmt: str):
        from .. import service as _svc
        from ..store import db as _db

        con = _db.connect(self.cfg["database"])
        try:
            rows = _db.walk_detections(con, walk_id)
            walk = con.execute("SELECT * FROM walks WHERE id=?", (walk_id,)).fetchone()
        finally:
            con.close()
        if walk is None:
            return self._json({"error": f"walk {walk_id} not found"}, 404)
        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["start_s", "end_s", "common", "scientific", "confidence", "novelty"])
            for r in rows:
                w.writerow([r["start_s"], r["end_s"], r["species_common"],
                            r["species_sci"], r["confidence"], r["novelty"]])
            body, ctype, name = buf.getvalue().encode(), "text/csv", f"walk_{walk_id}.csv"
        else:
            jr = Path(f"data/journals/walk_{walk_id}.md")
            md = jr.read_text() if jr.exists() else _svc.journal_for_walk(self.cfg, walk_id)[0]
            det = "\n".join(f"- {r['start_s']:.1f}s {r['species_common']} ({r['confidence']:.2f})"
                            for r in rows)
            body = f"{md}\n\n## Detections\n{det}\n".encode()
            ctype, name = "text/markdown", f"walk_{walk_id}.md"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", f"attachment; filename={name}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(cfg: dict, port: int = 8765) -> None:
    Handler.cfg = cfg
    srv = HTTPServer(("127.0.0.1", port), Handler)  # localhost only: audio never leaves the device
    print(f"Field Notes at http://127.0.0.1:{port} (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
