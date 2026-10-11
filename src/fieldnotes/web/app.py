"""Minimal local web UI: stdlib http.server, one page, no external assets, localhost only.

Design: "a naturalist's field notebook". Plain HTML + inline CSS + vanilla JS.
No external fonts/scripts/icons/images/CDN. System font stacks only.
"""
from __future__ import annotations

import csv
import io
import json
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MAX_UPLOAD_BYTES = 200 * 1024 * 1024
PAGE_MAX_BYTES = 100 * 1024


def conf_word(confidence: float, count: int) -> str:
    """Confidence as a word + number. 'uncertain' follows the shared guard rule
    (single window or best confidence below 0.5); otherwise likely/confident."""
    from ..journal.guard import uncertain

    if uncertain({"confidence": confidence, "count": count}):
        return "uncertain"
    if confidence >= 0.8:
        return "confident"
    return "likely"


PAGE = """<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Field Notes — an offline bird journal</title>
<style>
:root{
  --bg:#F4EFE3; --card:#FBF8F0; --text:#1F2A1F; --muted:#4F5A48;
  --moss:#2F5D34; --rust:#9A3F1D; --border:#D9D0BC;
  --btn-text:#FFFFFF; --focus:#1F2A1F;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="paper"]){
    --bg:#121A14; --card:#1B261D; --text:#E8EBDD; --muted:#B3BDA6;
    --moss:#9CCB8A; --rust:#F0A27A; --border:#2E3B30;
    --btn-text:#0E150F; --focus:#E8EBDD;
  }
}
:root[data-theme="dusk"]{
  --bg:#121A14; --card:#1B261D; --text:#E8EBDD; --muted:#B3BDA6;
  --moss:#9CCB8A; --rust:#F0A27A; --border:#2E3B30;
  --btn-text:#0E150F; --focus:#E8EBDD;
}
*{box-sizing:border-box}
html{font-size:18px}
body{background:var(--bg);color:var(--text);
  background-image:linear-gradient(175deg,var(--bg) 0%,var(--card) 130%);
  font-family:ui-sans-serif,system-ui,-apple-system,sans-serif;
  max-width:760px;margin:0 auto;padding:1rem 1.2rem 4rem;line-height:1.6}
h1,h2,h3,.serif{font-family:Georgia,"Iowan Old Style","Palatino Linotype",serif;
  font-weight:600;line-height:1.25}
h1{font-size:2.1rem;margin:.4rem 0 .1rem}
h2{font-size:1.45rem;margin:2.2rem 0 .8rem}
.subtitle{color:var(--muted);margin:0 0 .2rem}
.local-line{color:var(--muted);font-size:.95rem;margin:0 0 1.4rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:.7rem;
  padding:1.1rem 1.2rem;margin:0 0 1.2rem}
label{display:block;margin:.7rem 0 .2rem}
input[type="text"],input[type="date"],input[type="file"]{font-size:1rem;
  padding:.55rem .6rem;min-height:44px;max-width:100%;
  background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:.4rem}
input[type="checkbox"]{width:1.3rem;height:1.3rem;accent-color:var(--moss)}
button{font-size:1.05rem;min-height:44px;padding:.6rem 1.2rem;border:0;border-radius:.5rem;
  background:var(--moss);color:var(--btn-text);cursor:pointer}
button.ghost{background:transparent;color:var(--text);border:1px solid var(--border)}
button.danger{background:transparent;color:var(--rust);border:1px solid var(--rust)}
button + button{margin-left:.6rem}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.hint{color:var(--muted);font-size:.95rem}
code{background:var(--bg);border:1px solid var(--border);border-radius:.3rem;
  padding:0 .35rem;font-size:.9em}
.specimen{border-left:4px solid var(--moss)}
.specimen.quiet{border-left:4px dashed var(--border)}
.specimen h3{font-size:1.35rem;margin:.1rem 0}
.specimen .sci{font-style:italic;color:var(--muted)}
.confword{font-weight:700}
.stamp{display:inline-block;border:2px solid var(--rust);color:var(--rust);
  border-radius:.35rem .9rem .35rem .9rem;padding:.1rem .6rem;font-size:.9rem;
  transform:rotate(-2deg);margin-left:.6rem}
.timeline{display:flex;gap:3px;margin:.6rem 0;flex-wrap:nowrap}
.timeline .cell{flex:1 1 0;min-width:8px;height:22px;border:1px solid var(--border);
  border-radius:3px;background:transparent}
.timeline .cell.heard{background:var(--moss);border-color:var(--moss)}
.timeline .cell.heard::after{content:"●";display:block;text-align:center;
  font-size:12px;line-height:20px;color:var(--btn-text)}
.axis{display:flex;justify-content:space-between;color:var(--muted);font-size:.85rem}
.journal-page{font-family:Georgia,"Iowan Old Style","Palatino Linotype",serif;
  line-height:1.85;font-size:1.08rem;
  background-image:repeating-linear-gradient(var(--card) 0 1.78em,
    var(--border) 1.78em calc(1.78em + 1px));
  padding:.4rem .2rem;white-space:pre-wrap}
.badge{display:inline-block;border:1px solid var(--moss);color:var(--moss);
  border-radius:2rem;padding:.15rem .8rem;font-size:.9rem;margin:.4rem .4rem 0 0}
.badge.template{border-style:dashed}
table{border-collapse:collapse;width:100%}
td,th{border:1px solid var(--border);padding:.45rem .6rem;text-align:left}
details.card summary{cursor:pointer;min-height:44px;font-size:1.1rem}
.skip{position:absolute;left:-999px}
.skip:focus{position:static;background:var(--card);padding:.5rem}
footer{color:var(--muted);font-size:.9rem;margin-top:2.4rem;
  border-top:1px solid var(--border);padding-top:1rem}
.danger-zone{border:1px solid var(--rust)}
audio{width:100%;margin-top:.5rem}
svg.illus{color:var(--moss)}
.fade{transition:opacity 150ms ease}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media print{
  form,button,.no-print,#res .warn{display:none!important}
  body{background:#fff;color:#000;max-width:100%}
  .card{border:0}
}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header>
<svg class="illus" width="46" height="46" viewBox="0 0 46 46" role="img" aria-label="A small leaf sprig">
<path d="M23 42 C23 28 23 16 23 6" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
<path d="M23 34 C16 33 11 29 9 22 C16 23 21 27 23 34 Z" fill="none" stroke="currentColor" stroke-width="1.6"/>
<path d="M23 26 C30 25 35 21 37 14 C30 15 25 19 23 26 Z" fill="none" stroke="currentColor" stroke-width="1.6"/>
<path d="M23 18 C18 17 14 14 13 9 C18 10 21 13 23 18 Z" fill="none" stroke="currentColor" stroke-width="1.6"/>
</svg>
<h1>Field Notes</h1>
<p class="subtitle">an offline bird journal</p>
<p class="local-line">runs on this computer · <button id="theme" class="ghost no-print" type="button">dusk / paper</button></p>
</header>
<main id="main">
<section class="card" aria-labelledby="add-h">
<h2 id="add-h">Add a recording</h2>
<p class="hint">Tip: upload a 48 kHz mono WAV at least 3 s long. Anything else? Run
<code>python scripts/get_audio.py prepare YOURFILE</code> first — see docs/WHAT_TO_UPLOAD.md in the repo.</p>
<form id="up" aria-label="Upload a walk recording">
<label for="wav">Recording (WAV)</label>
<input type="file" id="wav" name="wav" accept=".wav,.flac,.ogg" required>
<label for="date">Date of recording</label>
<input type="date" id="date" name="date" required>
<label for="own"><input type="checkbox" id="own" name="own" value="1"> This is my own recording</label>
<label for="useloc"><input type="checkbox" id="useloc" name="useloc" value="1"> Use location filter (needs lat/lon below)</label>
<div id="locrow" hidden>
<label for="lat">Lat</label><input type="text" id="lat" name="lat" inputmode="decimal" placeholder="e.g. 60.17">
<label for="lon">Lon</label><input type="text" id="lon" name="lon" inputmode="decimal" placeholder="e.g. 24.94">
</div>
<label for="weather">Weather note</label>
<input type="text" id="weather" name="weather" placeholder="cool, overcast…">
<p><button type="submit">Listen</button></p>
</form>
</section>
<section aria-labelledby="res-h" aria-live="polite">
<h2 id="res-h" class="serif">Results</h2>
<div id="res" class="fade"><p class="hint">Nothing listened to yet.</p></div>
</section>
<section aria-labelledby="heard-h">
<h2 id="heard-h">What it heard</h2>
<div id="cards"><div class="card"><p>No calls cleared the threshold. A quiet walk is still a walk.</p></div></div>
<div id="strip"></div>
</section>
<section class="card" aria-labelledby="jr-h">
<h2 id="jr-h">Field journal</h2>
<div id="journal"><p class="hint">The journal appears here after a recording is analyzed.</p></div>
</section>
<section class="card" aria-labelledby="life-h">
<details id="lifedetails">
<summary id="life-h">My life list</summary>
<div id="life"></div>
</details>
</section>
<section class="card no-print" aria-labelledby="exp-h">
<h2 id="exp-h">Export</h2>
<p><button id="expMd" class="ghost" type="button">Journal (.md)</button>
<button id="expCsv" class="ghost" type="button">Detections (.csv)</button></p>
</section>
<section class="card danger-zone no-print" aria-labelledby="del-h">
<h2 id="del-h">Delete all my data</h2>
<p class="hint">Removes the database and every saved clip on this computer. This cannot be undone.</p>
<p><button id="wipe" class="danger" type="button">Delete all my data</button></p>
</section>
</main>
<footer>
<p id="versions"></p>
<p>Done here? Close the laptop. The birds are outside.</p>
</footer>
<script>
"use strict";
const $=id=>document.getElementById(id);
let walkId=null, timer=null, dateTouched=false;
function todayStr(){return new Date().toISOString().slice(0,10);}
function num(v){const f=parseFloat(v);return isFinite(f)?f:null;}
$("date").value=todayStr();
$("date").addEventListener("change",()=>{dateTouched=true;});
$("wav").addEventListener("change",()=>{if(!dateTouched&&$("wav").files.length){
  $("date").value=new Date($("wav").files[0].lastModified).toISOString().slice(0,10);}});
$("useloc").addEventListener("change",()=>{$("locrow").hidden=!$("useloc").checked;});
$("theme").onclick=()=>{const h=document.documentElement;
  h.dataset.theme=h.dataset.theme==="dusk"?"paper":(h.dataset.theme==="paper"?"":"dusk");};
function esc(s){return String(s).replace(/</g,"&lt;");}
$("up").onsubmit=async e=>{e.preventDefault();
  const t0=Date.now();
  $("res").innerHTML="<p>Listening… 0s</p>";
  timer=setInterval(()=>{$("res").innerHTML="<p>Listening… "+Math.floor((Date.now()-t0)/1000)+"s</p>";},1000);
  const fd=new FormData(e.target);
  const useLoc=$("useloc").checked;
  const lat=useLoc?num(fd.get("lat")):null, lon=useLoc?num(fd.get("lon")):null;
  const q=new URLSearchParams({date:fd.get("date")||"",weather:fd.get("weather")||"",
    lat:lat===null?"":lat,lon:lon===null?"":lon,
    own:$("own").checked?"1":""});
  try{
    const r=await fetch("/api/analyze?"+q,{method:"POST",body:fd.get("wav")});
    const j=await r.json();
    clearInterval(timer);
    if(!r.ok){$("res").innerHTML="<p><strong>Could not listen:</strong> "+esc(j.error||r.status)+"</p>";return;}
    walkId=j.walk_id;
    let html="";
    if(j.sample_note)html+="<p><strong>Note:</strong> this is a sample/reference clip, not a field recording of mine.</p>";
    if(j.date_warning)html+="<p><strong>Warning:</strong> "+esc(j.date_warning)+"</p>";
    html+="<p>Walk "+j.walk_id+": <strong>"+j.n_detections+"</strong> detections in "+j.n_windows+" windows.</p>";
    $("res").innerHTML=html;
    await showWalk(); journal(); life();
  }catch(err){clearInterval(timer);
    $("res").innerHTML="<p><strong>Could not listen:</strong> "+esc(err.message)+"</p>";}
};
async function showWalk(){if(walkId===null)return;
  const r=await fetch("/api/walk?id="+walkId);const w=await r.json();
  if(!r.ok){$("cards").innerHTML="<p>Could not load results.</p>";return;}
  if(!w.cards.length){
    $("cards").innerHTML='<div class="card"><svg class="illus" width="40" height="40" viewBox="0 0 40 40" role="img" aria-label="A small bird silhouette"><path d="M6 26 C12 18 20 14 30 14 L26 18 L34 18 L24 24 C18 27 12 28 6 26 Z" fill="currentColor"/><circle cx="27" cy="17" r="1.4" fill="var(--card)"/></svg><p>No calls cleared the threshold. A quiet walk is still a walk.</p></div>';
  }else{
    $("cards").innerHTML=w.cards.map(c=>{
      const stamp=c.novelty==="first_ever"?'<span class="stamp">new to my list</span>':"";
      const clip=c.clip_url?'<audio controls preload="none" src="'+c.clip_url+'" aria-label="Saved clip of '+esc(c.common)+'"></audio>':"";
      return '<article class="card specimen'+(c.word==="uncertain"?" quiet":"")+'" aria-label="'+esc(c.common)+'">'+
        "<h3>"+esc(c.common)+stamp+"</h3>"+
        '<p class="sci">'+esc(c.sci)+"</p>"+
        '<p><span class="confword">'+c.word+"</span> · "+c.confidence.toFixed(2)+
        " · detected in "+c.windows_occupied+" of "+w.windows.n+" listening windows</p>"+clip+"</article>";
    }).join("");
  }
  if(w.windows&&w.windows.n>0){
    const cells=w.windows.filled.map((f,i)=>'<span class="cell'+(f?" heard":"")+'" aria-label="window '+(i+1)+": "+(f?"detection":"no detection")+'"></span>').join("");
    $("strip").innerHTML='<h3 class="serif">Listening windows</h3><div class="timeline" role="img" aria-label="'+
      w.windows.filled.filter(Boolean).length+" of "+w.windows.n+' windows with detections">'+cells+
      '</div><div class="axis"><span>0s</span><span>'+Math.round(w.windows.duration_s)+'s</span></div>';
  }else{$("strip").innerHTML="";}
}
async function journal(){if(walkId===null)return;
  const r=await fetch("/api/journal",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({walk_id:walkId})});
  const j=await r.json();
  const cls=j.provenance&&j.provenance.indexOf("template:")===0?"badge template":"badge";
  $("journal").innerHTML='<div class="journal-page">'+esc(j.markdown)+"</div>"+
    '<p><span class="'+cls+'">'+esc(j.badge)+"</span></p>";
}
async function life(){const r=await fetch("/api/life");const j=await r.json();
  document.querySelector("#lifedetails summary").textContent="My life list ("+j.length+")";
  $("life").innerHTML=j.length?("<table><tr><th>Species</th><th>First seen</th></tr>"+
    j.map(x=>"<tr><td>"+esc(x.species_common)+" ("+esc(x.species_sci)+")</td><td>"+esc(x.first_seen)+"</td></tr>").join("")+"</table>"):"<p>No species yet.</p>";
}
$("expMd").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=md";};
$("expCsv").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=csv";};
$("wipe").onclick=async()=>{if(!confirm("Delete ALL local data (database + clips)?"))return;
  const r=await fetch("/api/wipe",{method:"POST"});const j=await r.json();
  alert(j.ok?"Deleted.":"Error: "+j.error);walkId=null;life();
  $("journal").innerHTML="";$("res").innerHTML="";$("cards").innerHTML="";$("strip").innerHTML="";};
fetch("/api/versions").then(r=>r.json()).then(j=>{$("versions").textContent=j.text;});
life();
</script>
</body>
</html>
"""

assert len(PAGE.encode()) < PAGE_MAX_BYTES, f"page is {len(PAGE.encode())} bytes"


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
        if u.path == "/api/walk":
            return self._walk(int(q.get("id", [0])[0]))
        if u.path == "/api/clip":
            return self._clip(int(q.get("walk", [0])[0]), q.get("name", [""])[0])
        if u.path == "/api/versions":
            return self._json({"text": _versions_text(self.cfg)})
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
            form = _parse_multipart(raw, ctype)
            if form is None or b"wav" not in form or not form[b"wav"][1]:
                return self._json({"error": "no 'wav' file in upload"}, 400)
            filename, raw = form[b"wav"]
            filename = Path(filename).name or "upload.wav"
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

        datestr = (q.get("date", [""])[0] or "").strip()
        if not datestr:
            return self._json({"error": "date is required: pick the recording date "
                                        "(it drives the season filter and the journal)"}, 400)
        own = (q.get("own", [""])[0] == "1")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(raw)
            tmp = tf.name
        try:
            try:
                summary = _svc.analyze_walk(
                    tmp, self.cfg,
                    lat=f(q.get("lat")), lon=f(q.get("lon")),
                    date=datestr,
                    weather_note=(q.get("weather", [""])[0] or ""),
                    own_recording=own,
                )
            except ValueError as exc:
                return self._json({"error": str(exc)}, 400)
        finally:
            Path(tmp).unlink(missing_ok=True)
        summary["sample_note"] = (not own) or ("sample" in Path(filename).stem.lower())
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
        if prov.startswith("template:"):
            badge = "template (no LLM)"
        else:
            badge = f"written by {model}"
        return self._json({"markdown": md, "provenance": prov, "model": model, "badge": badge})

    def _walk(self, walk_id: int):
        from ..store import db as _db

        con = _db.connect(self.cfg["database"])
        try:
            walk = con.execute("SELECT * FROM walks WHERE id=?", (walk_id,)).fetchone()
            if walk is None:
                return self._json({"error": f"walk {walk_id} not found"}, 404)
            rows = _db.walk_detections(con, walk_id)
            clips = list(con.execute("SELECT * FROM clips WHERE walk_id=?", (walk_id,)))
        finally:
            con.close()
        try:
            import json as _json

            wcfg = _json.loads(walk["config_json"] or "{}")
        except ValueError:
            wcfg = {}
        window_s = wcfg.get("window_s", 3.0) or 3.0
        n = int(walk["duration_s"] // window_s)
        filled = [False] * n
        by_sci: dict[str, dict] = {}
        for r in rows:
            idx = int(r["start_s"] // window_s)
            if 0 <= idx < n:
                filled[idx] = True
            slot = by_sci.setdefault(r["species_sci"], {
                "common": r["species_common"], "sci": r["species_sci"],
                "confidence": 0.0, "windows": set(), "novelties": []})
            slot["confidence"] = max(slot["confidence"], r["confidence"])
            if 0 <= idx < n:
                slot["windows"].add(idx)
            slot["novelties"].append(r["novelty"])
        clip_by_species: dict[str, str] = {}
        for c in clips:
            key = str(c["species_common"])
            if key not in clip_by_species:
                clip_by_species[key] = (
                    f"/api/clip?walk={walk_id}&name="
                    + urllib.parse.quote(str(Path(c["path"]).name))
                )
        rank = {"first_ever": 0, "first_this_walk": 1, "repeat": 2}
        cards = []
        for s in by_sci.values():
            cards.append({
                "common": s["common"], "sci": s["sci"],
                "confidence": s["confidence"],
                "word": conf_word(s["confidence"], len(s["windows"])),
                "windows_occupied": len(s["windows"]),
                "novelty": min(s["novelties"], key=lambda v: rank.get(v, 9)),
                "clip_url": clip_by_species.get(s["common"]),
            })
        cards.sort(key=lambda c: -c["confidence"])
        return self._json({
            "walk_id": walk_id,
            "windows": {"n": n, "duration_s": walk["duration_s"], "filled": filled},
            "cards": cards,
        })

    def _clip(self, walk_id: int, name: str):
        base = Path(self.cfg["clips_dir"]).resolve() / f"walk_{walk_id}"
        target = (base / Path(name).name).resolve()
        if base not in target.parents or target.suffix.lower() != ".wav" or not target.is_file():
            return self._json({"error": "clip not found"}, 404)
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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


def _parse_multipart(raw: bytes, ctype: str):
    """Minimal multipart/form-data parser (stdlib only): {field: (filename, bytes)}."""
    import re

    m = re.search(r"boundary=([^;]+)", ctype)
    if not m:
        return None
    boundary = ("--" + m.group(1).strip().strip('"')).encode()
    out: dict[bytes, tuple[str, bytes]] = {}
    for part in raw.split(boundary):
        if b"Content-Disposition" not in part:
            continue
        head, _, body = part.partition(b"\r\n\r\n")
        fm = re.search(br'name="([^"]+)"', head)
        if not fm:
            continue
        nm = re.search(br'filename="([^"]*)"', head)
        out[fm.group(1)] = (nm.group(1).decode("utf-8", "replace") if nm else "",
                            body.rstrip(b"\r\n").rstrip(b"--").rstrip(b"\r\n"))
    return out


def _versions_text(cfg: dict) -> str:
    try:
        from ..detect import birdnet as _b

        det = f"Bird detector: {getattr(_b, 'MODEL_VERSION', 'unknown')} · weights CC BY-NC-SA 4.0 (non-commercial, open-weight)"
    except ImportError:
        det = "Bird detector: not installed (run make setup)"
    return f"{det} · Journal model: {cfg.get('llm_name', '?')} (local via Ollama)"


def serve(cfg: dict, port: int = 8765) -> None:
    Handler.cfg = cfg
    srv = HTTPServer(("127.0.0.1", port), Handler)  # localhost only: audio never leaves the device
    print(f"Field Notes at http://127.0.0.1:{port} (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
