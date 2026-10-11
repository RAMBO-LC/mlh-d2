"""Minimal local web UI: stdlib http.server, one page, no external assets, localhost only."""
from __future__ import annotations

import cgi
import csv
import io
import json
import re
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

MAX_UPLOAD_BYTES = 200 * 1024 * 1024

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Field Notes — walk recap</title>
<style>
:root{
--bg:#F4EFE3;--card:#FBF8F0;--text:#1F2A1F;--muted:#4F5A48;
--moss:#2F5D34;--rust:#9A3F1D;--border:#D9D0BC;--btn-text:#FFFFFF;
--focus:#9A3F1D;
--serif:Georgia,"Iowan Old Style","Palatino Linotype",serif;
--sans:ui-sans-serif,system-ui,sans-serif;
}
@media (prefers-color-scheme:dark){
:root{--bg:#121A14;--card:#1B261D;--text:#E8EBDD;--muted:#B3BDA6;
--moss:#9CCB8A;--rust:#F0A27A;--border:#2E3B30;--btn-text:#0E150F;--focus:#F0A27A;}
}
html[data-theme="paper"]{--bg:#F4EFE3;--card:#FBF8F0;--text:#1F2A1F;--muted:#4F5A48;
--moss:#2F5D34;--rust:#9A3F1D;--border:#D9D0BC;--btn-text:#FFFFFF;--focus:#9A3F1D;}
html[data-theme="dusk"]{--bg:#121A14;--card:#1B261D;--text:#E8EBDD;--muted:#B3BDA6;
--moss:#9CCB8A;--rust:#F0A27A;--border:#2E3B30;--btn-text:#0E150F;--focus:#F0A27A;}
html{font-size:112.5%;scroll-behavior:auto;}
body{background:var(--bg);background-image:linear-gradient(180deg,rgba(255,255,255,.28),rgba(0,0,0,.035));color:var(--text);font-family:var(--sans);margin:0;line-height:1.6;font-size:1rem;}
.wrap{max-width:760px;margin:0 auto;padding:1rem 1.25rem;}
.skip{position:absolute;left:-9999px;top:0;background:var(--moss);color:var(--btn-text);padding:.75rem 1rem;z-index:50;border-radius:.4rem;}
.skip:focus{left:1rem;top:1rem;}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px;border-radius:.2rem;}
h1,h2,h3{font-family:var(--serif);line-height:1.2;margin:1.2rem 0 .6rem;}
h1{font-size:2.2rem;margin:0;}
h2{font-size:1.5rem;}h3{font-size:1.15rem;}
.subtitle{font-family:var(--serif);font-style:italic;font-size:1.15rem;margin:.2rem 0;}
.runs{color:var(--muted);font-size:.95rem;margin:.1rem 0 0;}
.muted{color:var(--muted);}.small{font-size:.9rem;}
.site-head{padding-top:1.5rem;}
.brand-row{display:flex;gap:1rem;align-items:flex-start;}
.brand-row svg{flex:0 0 44px;margin-top:.3rem;}
.brand-row div{flex:1;}
.card{background:var(--card);border:1px solid var(--border);border-radius:.8rem;padding:1.25rem;margin:1.25rem 0;}
label{display:block;margin-top:.7rem;font-weight:600;}
input[type="text"],input[type="date"],input[type="file"]{display:block;width:100%;max-width:100%;box-sizing:border-box;min-height:44px;font-size:1rem;padding:.55rem .7rem;margin-top:.3rem;background:var(--bg);color:var(--text);border:1px solid var(--border);border-radius:.45rem;font-family:var(--sans);}
input[type="checkbox"]{width:1.4rem;height:1.4rem;min-width:44px;min-height:44px;vertical-align:middle;margin-right:.5rem;accent-color:var(--moss);}
.check{font-weight:600;}
.btn{background:var(--moss);color:var(--btn-text);border:2px solid var(--moss);border-radius:.55rem;padding:.65rem 1.2rem;min-height:44px;min-width:44px;font-size:1.05rem;cursor:pointer;font-family:var(--sans);font-weight:700;margin:.5rem .4rem .2rem 0;}
.btn.ghost{background:transparent;color:var(--text);}
.btn.danger{background:transparent;color:var(--rust);border-color:var(--rust);}
.hint{font-size:.95rem;color:var(--muted);}
.hint a,.quiet a,.card a{color:var(--moss);}
html[data-theme="dusk"] .hint a,html[data-theme="dusk"] .card a{color:var(--moss);}
code{font-size:.9em;}
.divider{width:100%;height:14px;color:var(--muted);margin:.4rem 0;}
.specimen{border:2px solid var(--moss);border-radius:.7rem;padding:1rem;margin:1rem 0;background:var(--card);}
.specimen.quiet{border:1px dashed var(--border);}
.specimen .common{font-family:var(--serif);font-size:1.45rem;margin:0;}
.specimen .sci{font-style:italic;font-family:var(--serif);margin:.15rem 0 .4rem;}
.specimen .conf{font-weight:700;}
.stamp{display:inline-block;border:2px solid var(--rust);color:var(--rust);border-radius:.3rem;padding:.1rem .55rem;font-size:.85rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;transform:rotate(-2deg);margin-left:.6rem;vertical-align:middle;}
audio{width:100%;margin-top:.6rem;min-height:44px;}
table{border-collapse:collapse;width:100%;font-size:1rem;}
td,th{border:1px solid var(--border);padding:.5rem;text-align:left;}
th{font-family:var(--sans);}
.strip{display:flex;flex-wrap:wrap;gap:2px;margin:.6rem 0 .2rem;}
.cell{width:11px;height:22px;border:1px solid var(--border);border-radius:2px;box-sizing:border-box;}
.cell.hit{background:var(--moss);border-color:var(--moss);}
.axis{display:flex;justify-content:space-between;color:var(--muted);font-size:.9rem;}
.notebook{background:var(--card);border:1px solid var(--border);border-radius:.4rem;padding:1.2rem 1.2rem 1.4rem;font-family:var(--serif);line-height:1.8;background-image:repeating-linear-gradient(transparent,transparent 1.7em,rgba(120,120,120,.18) 1.7em,rgba(120,120,120,.18) calc(1.7em + 1px));}
.notebook pre{white-space:pre-wrap;font-family:var(--serif);font-size:1.08rem;line-height:1.8;margin:0;background:transparent;border:0;padding:0;}
.writer-badge{display:inline-block;border:2px solid var(--moss);color:var(--text);border-radius:2rem;padding:.2rem .8rem;font-size:.9rem;font-weight:700;}
.note{border:1px solid var(--border);border-left:6px solid var(--moss);border-radius:.4rem;padding:.7rem .9rem;background:var(--card);}
.note.sample{border-left-color:var(--rust);}
.errcard{border:1px solid var(--border);border-left:6px solid var(--rust);border-radius:.4rem;padding:.8rem 1rem;background:var(--card);}
.emptycard{display:flex;gap:.9rem;align-items:flex-start;border:1px solid var(--border);border-radius:.6rem;padding:1rem;background:var(--card);}
.closing{font-family:var(--serif);font-style:italic;color:var(--muted);margin-top:1.4rem;}
.danger-zone{border:2px solid var(--rust);}
footer.quiet{color:var(--muted);font-size:.92rem;padding-bottom:3rem;}
details{margin:.6rem 0;}
summary{min-height:44px;font-size:1.05rem;font-weight:700;cursor:pointer;padding:.5rem 0;}
.fade{animation:fade 150ms ease;}
@keyframes fade{from{opacity:.35}to{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important;}}
@media print{
.site-head .btn,#up,.btn,#themeBtn,.no-print,#stripWrap,audio{display:none !important;}
body{background:#fff;color:#000;}
.card,.notebook{border:0;background:#fff;}
.wrap{max-width:100%;}
}
</style></head><body>
<a class="skip" href="#main">Skip to results</a>
<header class="wrap site-head">
<div class="brand-row">
<svg width="44" height="44" viewBox="0 0 48 48" role="img" aria-label="Leaf sprig"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M24 42 C24 30 24 18 25 7"/><path d="M24 32 C17 31 12 26 10 18 C18 20 23 25 24 32"/><path d="M25 25 C31 24 36 19 38 12 C31 13 26 18 25 25"/><path d="M24 38 C19 37 15 34 14 29 C19 30 23 33 24 38"/></g></svg>
<div><h1>Field Notes</h1><p class="subtitle">an offline bird journal</p><p class="runs">runs on this computer</p></div>
<button id="themeBtn" class="btn ghost no-print" type="button" aria-pressed="false">Dusk</button>
</div>
<svg class="divider" viewBox="0 0 120 12" aria-hidden="true"><path d="M2 6 C 12 2, 22 10, 32 6 S 52 2, 62 6 S 82 10, 92 6 S 112 2, 118 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
</header>
<main id="main" class="wrap">
<section aria-labelledby="add-h" class="card">
<h2 id="add-h">Add a recording</h2>
<form id="up" aria-label="Upload a walk recording">
<label for="wav">Recording (WAV)</label>
<input type="file" name="wav" id="wav" accept=".wav,.flac,.ogg" required>
<label for="date">Date of recording</label>
<input type="date" name="date" id="date" required>
<label class="check" for="own"><input type="checkbox" id="own"> This is my own recording</label>
<label class="check" for="useLoc"><input type="checkbox" id="useLoc"> Use location filter</label>
<div id="locFields" hidden>
<label for="lat">Lat</label><input type="text" id="lat" inputmode="decimal" placeholder="optional">
<label for="lon">Lon</label><input type="text" id="lon" inputmode="decimal" placeholder="optional">
</div>
<label for="weather">Weather note <span class="muted">(optional)</span></label>
<input type="text" id="weather" placeholder="cool, overcast…">
<button class="btn" type="submit">Listen</button>
<p class="hint">Tip: upload a 48 kHz mono WAV at least 3 s long. Anything else? Run <code>python scripts/get_audio.py prepare YOURFILE</code> first — see <a href="docs/WHAT_TO_UPLOAD.md">docs/WHAT_TO_UPLOAD.md</a>.</p>
</form>
</section>
<section aria-labelledby="heard-h" class="card">
<h2 id="heard-h">What it heard</h2>
<div id="res" role="status" aria-live="polite"></div>
<div id="cards"></div>
<div id="stripWrap" class="no-print"></div>
<p class="closing">Done here? Close the laptop. The birds are outside.</p>
</section>
<section aria-labelledby="journal-h" class="card">
<h2 id="journal-h">Field journal</h2>
<div id="journal"><p>No journal yet — analyze a walk first.</p></div>
<p id="writerBadge"></p>
<p id="scopeNote" class="muted small"></p>
</section>
<section aria-labelledby="list-h" class="card">
<h2 id="list-h">My life list</h2>
<details id="lifeDetails"><summary>Show my life list</summary><div id="life"><p>Loading…</p></div></details>
<h3>Export</h3>
<p><button id="expMd" class="btn">Export journal (.md)</button> <button id="expCsv" class="btn">Export detections (.csv)</button></p>
</section>
<section aria-labelledby="danger-h" class="card danger-zone">
<h2 id="danger-h">Delete all my data</h2>
<p>This removes the local database and every saved clip on this computer. The app and its settings stay put.</p>
<p><button id="wipe" class="btn danger">Delete all my data</button></p>
</section>
</main>
<footer class="wrap quiet">
<svg width="64" height="30" viewBox="0 0 64 32" role="img" aria-label="Generic small bird silhouette"><path d="M6 21 C13 12 26 9 35 14 L43 7 L45 14 L55 16 L45 20 C37 27 18 27 6 21 Z" fill="currentColor"/><circle cx="38" cy="14" r="1.2" fill="var(--bg)"/></svg>
<p id="versions">Model versions loading…</p>
<p>Licences: <a href="LICENSES.md">LICENSES.md</a> · <a href="docs/ATTRIBUTION.md">docs/ATTRIBUTION.md</a> · <a href="docs/WHAT_TO_UPLOAD.md">docs/WHAT_TO_UPLOAD.md</a></p>
<p class="closing">Done here? Close the laptop. The birds are outside.</p>
</footer>
<script>
let walkId=null, windowS=3;
const $=id=>document.getElementById(id);
let themeMem="auto";
function setTheme(t){themeMem=t;const r=document.documentElement;
if(t==="auto"){r.removeAttribute("data-theme");$("themeBtn").textContent="Dusk";$("themeBtn").setAttribute("aria-pressed","false");}
else{r.setAttribute("data-theme",t);const d=(t==="dusk");$("themeBtn").textContent=d?"Paper":"Dusk";$("themeBtn").setAttribute("aria-pressed",d?"true":"false");}
try{const u=new URL(location.href);u.searchParams.set("theme",t);history.replaceState(null,"",u.pathname+u.search);}catch(e){}}
(function(){let t="auto";try{t=new URL(location.href).searchParams.get("theme")||"auto";}catch(e){} if(t!=="paper"&&t!=="dusk")t="auto";setTheme(t);})();
$("themeBtn").onclick=()=>{setTheme(themeMem==="dusk"?"paper":"dusk");};
function num(v){const f=parseFloat(v);return isFinite(f)?f:null;}
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function confWord(c,count){if(count<=1||c<0.5)return "uncertain";if(c>=0.7)return "confident";return "likely";}
const dEl=$("date"),wEl=$("wav");let dateTouched=false;
dEl.addEventListener("change",()=>{dateTouched=true;});
function todayStr(){return new Date().toISOString().slice(0,10);}
dEl.value=todayStr();
wEl.addEventListener("change",()=>{if(!dateTouched&&wEl.files.length){try{dEl.value=new Date(wEl.files[0].lastModified).toISOString().slice(0,10);}catch(e){}}});
$("useLoc").addEventListener("change",()=>{$("locFields").hidden=!$("useLoc").checked;});
async function meta(){try{const r=await fetch("/api/meta");const j=await r.json();
windowS=j.window_s||3;
$("versions").textContent="Detector "+j.bird_backend+" "+j.model_version+" · journal model "+j.llm_name+" · threshold "+j.confidence_threshold;}catch(e){$("versions").textContent="Model versions unavailable (page still works).";}}
$("up").onsubmit=async e=>{e.preventDefault();
const f=wEl.files[0];if(!f){$("res").innerHTML='<div class="errcard"><p>Choose a WAV file first.</p></div>';return;}
if(!dEl.value){$("res").innerHTML='<div class="errcard"><p>A date is required: pick the recording date (it drives the season filter and the journal).</p></div>';return;}
const own=$("own").checked, fname=f.name||"upload.wav";
const t0=Date.now();let secs=0;
$("res").innerHTML="<p>Listening… 0s</p>";$("cards").innerHTML="";$("stripWrap").innerHTML="";
const tick=setInterval(()=>{secs=Math.floor((Date.now()-t0)/1000);const r=$("res");if(r&&r.textContent.indexOf("Listening")===0)r.textContent="Listening… "+secs+"s";},1000);
try{
const lat=$("useLoc").checked?num($("lat").value):null, lon=$("useLoc").checked?num($("lon").value):null;
const q=new URLSearchParams({date:dEl.value||"",weather:$("weather").value||"",lat:lat===null?"":lat,lon:lon===null?"":lon,own:own?"1":""});
const r=await fetch("/api/analyze?"+q,{method:"POST",body:f});
const j=await r.json();clearInterval(tick);
if(!r.ok){$("res").innerHTML='<div class="errcard"><p>Error: '+esc(j.error||r.status)+'</p><p class="hint">If it mentions format or length, run <code>python scripts/get_audio.py prepare YOURFILE</code> — see <a href="docs/WHAT_TO_UPLOAD.md">docs/WHAT_TO_UPLOAD.md</a>.</p></div>';return;}
walkId=j.walk_id;
let html="<p>Walk "+j.walk_id+": <strong>"+j.n_detections+"</strong> detections in "+j.n_windows+" listening windows.</p>";
if(j.date_warning)html+="<p><strong>Note:</strong> "+esc(j.date_warning)+"</p>";
if(!own||/sample/i.test(fname))html+='<p class="note sample">This is a sample/reference clip, not a field recording of mine.</p>';
$("res").innerHTML=html;
await renderCards(j,own,fname);renderStrip(j);journal();life();
}catch(err){clearInterval(tick);$("res").innerHTML='<div class="errcard"><p>Something went wrong: '+esc(err&&err.message||err)+'</p><p class="hint">Check the file is a readable WAV of at least 3 s, then try again.</p></div>';}
};
function groupSpecies(list){const m=new Map();
(list||[]).forEach(s=>{const k=s.sci||s.common;let g=m.get(k);
if(!g){g={common:s.common,sci:s.sci,confidence:0,count:0,novelty:"repeat",starts:[]};m.set(k,g);}
g.count+=1;g.confidence=Math.max(g.confidence,s.confidence||0);g.starts.push(s.start_s||0);
if(s.novelty==="first_ever")g.novelty="first_ever";else if(s.novelty==="first_this_walk"&&g.novelty!=="first_ever")g.novelty="first_this_walk";});
return Array.from(m.values()).sort((a,b)=>b.confidence-a.confidence);}
async function renderCards(summary,own,fname){
const box=$("cards");const groups=groupSpecies(summary.species);const M=summary.n_windows||0;
if(!groups.length){box.innerHTML='<div class="emptycard"><svg width="40" height="24" viewBox="0 0 64 32" role="img" aria-label="Small bird"><path d="M6 21 C13 12 26 9 35 14 L43 7 L45 14 L55 16 L45 20 C37 27 18 27 6 21 Z" fill="currentColor"/></svg><p>No calls cleared the threshold. A quiet walk is still a walk.</p></div>';return;}
let clips=[];try{const r=await fetch("/api/clips?id="+summary.walk_id);if(r.ok)clips=await r.json();}catch(e){}
box.innerHTML=groups.map(g=>{const w=confWord(g.confidence,g.count);const q=w==="uncertain";
const clip=clips.find(c=>c.species_common===g.common);
const stamp=(g.novelty==="first_ever")?'<span class="stamp">new to my list</span>':"";
const audio=clip?'<audio controls preload="none" src="'+esc(clip.url)+'" aria-label="Play saved clip of '+esc(g.common)+'"><a href="'+esc(clip.url)+'">Download clip</a></audio>':"";
return '<article class="specimen fade'+(q?" quiet":"")+'"><h3 class="common">'+esc(g.common)+stamp+'</h3><p class="sci">'+esc(g.sci)+'</p><p class="conf">'+w+' · '+g.confidence.toFixed(2)+'</p><p>detected in '+g.count+' of '+M+' listening windows</p>'+audio+'</article>';}).join("");
}
function renderStrip(summary){
const wrap=$("stripWrap");wrap.innerHTML="";const M=summary.n_windows||0;if(!M||M<1)return;
const ws=windowS||3,filled=new Set();
(summary.species||[]).forEach(s=>{const i=Math.floor((s.start_s||0)/ws);if(i>=0&&i<M)filled.add(i);});
const dur=(M*ws).toFixed(0);
let cells="";for(let i=0;i<M;i++)cells+='<span class="cell'+(filled.has(i)?" hit":"")+'"></span>';
wrap.innerHTML='<h3>Listening windows</h3><div class="strip" role="img" aria-label="'+filled.size+' of '+M+' listening windows had a detection">'+cells+'</div><p class="axis"><span>0s</span><span>'+dur+'s</span></p><p class="muted small">One cell per '+ws+'s listening window; filled cells had a detection.</p>';
}
async function journal(){if(walkId===null)return;
try{const r=await fetch("/api/journal",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({walk_id:walkId})});
const j=await r.json();
if(!r.ok){$("journal").innerHTML='<div class="errcard"><p>Error: '+esc(j.error||r.status)+'</p></div>';return;}
$("journal").innerHTML='<div class="notebook"><pre>'+esc(j.markdown)+'</pre></div>';
const prov=j.provenance||"",model=j.model||"";
$("writerBadge").innerHTML=(prov.indexOf("template:")===0)?'<span class="writer-badge">template (no LLM)</span>':'<span class="writer-badge">written by '+esc(model)+'</span>';
try{const w=await (await fetch("/api/walk?id="+walkId)).json();
if(w&&w.walk_id)$("scopeNote").textContent="Date "+w.date+" · location filter "+w.location_filter+" · confidence threshold "+w.threshold;}catch(e){}
}catch(e){$("journal").innerHTML='<div class="errcard"><p>Journal failed: '+esc(e.message||e)+'</p></div>';}
}
async function life(){try{const r=await fetch("/api/life");const j=await r.json();
$("life").innerHTML=j.length?("<table><caption>My life list</caption><tr><th scope="col">Species</th><th scope="col">First seen</th></tr>"+j.map(x=>"<tr><td>"+esc(x.species_common)+" (<i>"+esc(x.species_sci)+"</i>)</td><td>"+esc(x.first_seen)+"</td></tr>").join("")+"</table>"):"<p>Life list is empty.</p>";}catch(e){$("life").innerHTML="<p>Life list unavailable.</p>";}}
$("expMd").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=md";};
$("expCsv").onclick=()=>{if(walkId!==null)location.href="/api/export?id="+walkId+"&fmt=csv";};
$("wipe").onclick=async()=>{if(!confirm("Delete ALL local data (database + clips)?"))return;
try{const r=await fetch("/api/wipe",{method:"POST"});const j=await r.json();
alert(j.ok?"Deleted.":"Error: "+j.error);walkId=null;life();$("journal").innerHTML="<p>No journal yet — analyze a walk first.</p>";$("writerBadge").innerHTML="";$("scopeNote").textContent="";$("res").textContent="";$("cards").innerHTML="";$("stripWrap").innerHTML="";}catch(e){alert("Error: "+e);}};
meta();life();
</script></body></html>
"""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


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
            try:
                return self._export(int(q.get("id", [0])[0]), q.get("fmt", ["md"])[0])
            except (ValueError, TypeError):
                return self._json({"error": "id must be an integer"}, 400)
        if u.path == "/api/meta":
            return self._meta()
        if u.path == "/api/clips":
            try:
                return self._clips_json(int(q.get("id", [0])[0]))
            except (ValueError, TypeError):
                return self._json({"error": "id must be an integer"}, 400)
        if u.path == "/api/walk":
            try:
                return self._walk_json(int(q.get("id", [0])[0]))
            except (ValueError, TypeError):
                return self._json({"error": "id must be an integer"}, 400)
        if u.path.startswith("/clips/"):
            return self._serve_clip(u.path[len("/clips/"):])
        if u.path in ("/LICENSES.md", "/docs/ATTRIBUTION.md",
                      "/docs/WHAT_TO_UPLOAD.md", "/WHAT_TO_UPLOAD.md"):
            return self._serve_doc(u.path)
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

    def _meta(self):
        cfg = self.cfg
        try:
            from ..detect import base as _base

            backend = _base.get_backend(cfg.get("bird_backend", "birdnet"))
            model_version = getattr(backend, "MODEL_VERSION", "unknown")
        except ValueError:
            model_version = "unknown"
        return self._json({
            "bird_backend": cfg.get("bird_backend", "birdnet"),
            "model_version": model_version,
            "llm_name": cfg.get("llm_name", "?"),
            "confidence_threshold": cfg.get("confidence_threshold", "?"),
            "window_s": cfg.get("window_s", 3.0),
            "overlap_s": cfg.get("overlap_s", 0.0),
        })

    def _clips_json(self, walk_id: int):
        from ..store import db as _db

        con = _db.connect(self.cfg["database"])
        try:
            rows = con.execute(
                "SELECT species_common, path, start_s, end_s FROM clips"
                " WHERE walk_id=? ORDER BY start_s", (walk_id,)).fetchall()
        finally:
            con.close()
        out = []
        for r in rows:
            name = Path(r["path"]).name
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*", name):
                continue
            out.append({"species_common": r["species_common"],
                        "start_s": r["start_s"], "end_s": r["end_s"],
                        "url": f"/clips/walk_{walk_id}/{name}"})
        return self._json(out)

    def _walk_json(self, walk_id: int):
        from ..store import db as _db

        con = _db.connect(self.cfg["database"])
        try:
            walk = con.execute("SELECT * FROM walks WHERE id=?", (walk_id,)).fetchone()
            if walk is None:
                return self._json({"error": f"walk {walk_id} not found"}, 404)
            rows = _db.walk_detections(con, walk_id)
        finally:
            con.close()
        try:
            snap = json.loads(walk["config_json"] or "{}")
        except ValueError:
            snap = {}
        window_s = snap.get("window_s") or self.cfg.get("window_s", 3.0) or 3.0
        threshold = snap.get("confidence_threshold", self.cfg.get("confidence_threshold", "?"))
        try:
            duration = float(walk["duration_s"])
        except (TypeError, ValueError):
            duration = 0.0
        n_windows = int(duration // window_s) if window_s > 0 else 0
        loc_on = walk["lat"] is not None and walk["lon"] is not None
        return self._json({
            "walk_id": walk_id,
            "date": walk["started_at"],
            "duration_s": duration,
            "n_windows": n_windows,
            "window_s": window_s,
            "location_filter": "on" if loc_on else "off",
            "threshold": threshold,
            "own_recording": bool(walk["is_own_recording"]) if "is_own_recording" in walk.keys() else False,
            "detections": [{"common": r["species_common"], "sci": r["species_sci"],
                            "confidence": r["confidence"], "start_s": r["start_s"],
                            "end_s": r["end_s"], "novelty": r["novelty"]} for r in rows],
        })

    def _serve_clip(self, rest: str):
        parts = rest.split("/")
        if len(parts) != 2 or not re.fullmatch(r"walk_\d+", parts[0]):
            return self._json({"error": "not found"}, 404)
        name = parts[1]
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*\.(wav|flac|ogg)", name, re.IGNORECASE):
            return self._json({"error": "not found"}, 404)
        base = Path(self.cfg["clips_dir"]).resolve()
        target = (base / parts[0] / name).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            return self._json({"error": "not found"}, 404)
        if not target.is_file():
            return self._json({"error": "clip not found"}, 404)
        data = target.read_bytes()
        ctype = {"wav": "audio/wav", "flac": "audio/flac", "ogg": "audio/ogg"}.get(
            target.suffix.lower().lstrip("."), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_doc(self, url_path: str):
        root = _repo_root()
        mapping = {
            "/LICENSES.md": root / "LICENSES.md",
            "/docs/ATTRIBUTION.md": root / "docs" / "ATTRIBUTION.md",
            "/docs/WHAT_TO_UPLOAD.md": root / "WHAT_TO_UPLOAD.md",
            "/WHAT_TO_UPLOAD.md": root / "WHAT_TO_UPLOAD.md",
        }
        src = mapping.get(url_path)
        if src is None or not src.is_file():
            return self._json({"error": "not found"}, 404)
        data = src.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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
