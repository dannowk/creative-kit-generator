"""Copy Kit UI (independent of the visual kit): lean wizard + review table.

Reuses the visual kit's chrome (ui._STYLE/_modal/_JS_UTIL/_open_folder and the HTTP
helpers of ui.Handler), but pages, strings and routes are its own — copy never touches
campaign/render/ppc. Wizard: briefing + examples (text only). Review: row-by-row table
with approve/reject/redo+note. Runs on 127.0.0.1, one UI at a time. English-only.
"""

import json
import os
import re
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import copy, i18n, ui

_STEPS = ["Briefing", "Generate", "Review", "Deliver"]

_TABLE_STYLE = """<style>
.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:12px;max-height:72vh}
table.copy{width:100%;border-collapse:collapse;font-size:13.5px}
table.copy th{text-align:left;color:var(--mut);font-weight:600;font-size:11.5px;text-transform:uppercase;
 letter-spacing:.03em;padding:9px 10px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--surface);z-index:1}
table.copy td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
table.copy tr:hover td{background:#fbfcfd}
table.copy .txt{min-width:240px;max-width:440px}
table.copy .acts{white-space:nowrap}
table.copy .acts button{min-height:28px;padding:3px 9px;font-size:12.5px}
.fieldlabel{font-size:12.5px;color:var(--mut);font-weight:600}
</style>"""


def _head(title):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>copy-kit · ' + title + '</title>' + ui._STYLE + _TABLE_STYLE + '</head><body>')


def _stepper(current, done):
    out = ['<div class="stepper">']
    for i, label in enumerate(_STEPS, 1):
        cls = "done" if i <= done else ("current" if i == current else "")
        mark = "✓" if i <= done else str(i)
        out.append(f'<span class="step {cls}" data-step="{i}"><span class="n">{mark}</span>{label}</span>')
        if i < len(_STEPS):
            out.append('<span class="bar"></span>')
    out.append("</div>")
    return "".join(out)


_TEMPLATE_LINES = {l.strip() for l in copy.BRIEF_TEMPLATE.splitlines() if l.strip()}


def _brief_progress(text):
    """Filled sections: a line that is neither a '(…)' placeholder nor a template line."""
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    filled = 0
    for s in sections:
        body = s.split("\n", 1)[1] if "\n" in s else ""
        for l in body.splitlines():
            l = l.strip()
            if not l or l in _TEMPLATE_LINES or (l.startswith("(") and l.endswith(")")):
                continue
            filled += 1
            break
    return filled, len(sections)


_WIZ_T = {
    "title": "Copy — briefing + examples",
    "prog": "{filled}/{total} briefing sections filled",
    "ready": "Briefing filled. Paste examples if you like, save and say “ready” in chat.",
    "missing": "Fill the briefing (at least the objective) and save. Examples are optional.",
    "p1.title": "Briefing + examples",
    "p1.desc": "Text only: no logo, brandbook or visual references. The agent generates copy from this.",
    "brief.label": "Copy briefing",
    "examples.label": "Example texts (paste copy you like / want to use as a model)",
    "save": "Save",
    "saved": "Briefing and examples saved.",
    "p2.title": "Generate with the agent",
    "p2.desc": "Copy the line below and paste it in chat. The agent generates copy and opens the table review.",
    "agentline": "Ready! Briefing and examples in {folder} — generate the copy (PPC + overlay) and open the review.",
    "copy": "Copy",
    "copied": "Line copied — paste it in chat.",
    "hascopy": "copy.json already exists in this folder — the agent can open the review directly.",
    "nocopy": "No copy.json yet — the agent generates it after your “ready”.",
}


def wizard_page():
    t = _WIZ_T
    return _head(t["title"]) + f"""
<header><span class="brand">copy-kit</span><h1>{t['title']}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button onclick="load()">{i18n.t('btn.refresh')}</button></header>
<div class="banner">
""" + _stepper(1, 0) + f"""
<span class="meta" id="prog"></span>
<div class="callout warn" id="ready"></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">1</span>{t['p1.title']}</h2>
<p class="desc">{t['p1.desc']}</p>
<label class="fieldlabel" for="brief">{t['brief.label']}</label>
<textarea id="brief"></textarea>
<label class="fieldlabel" for="examples">{t['examples.label']}</label>
<textarea id="examples" style="min-height:180px"></textarea>
<div class="row"><button class="btn primary" onclick="save()">{t['save']}</button></div></div>
<div class="panel"><h2><span class="n">2</span>{t['p2.title']}</h2>
<p class="desc">{t['p2.desc']}</p>
<div class="row"><input type="text" id="agentline" readonly style="flex:1">
<button class="btn primary" onclick="copyAgent()">{t['copy']}</button></div>
<p class="hint" id="copynote"></p></div>
</div>
""" + ui._modal() + ui._JS_UTIL + (
        '<script>const T=' + json.dumps(t, ensure_ascii=False) + ';</script>') + """
<script>
let S=null;
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
async function load(){
  S=await (await fetch("/state")).json();
  document.getElementById("meta").textContent=S.folder;
  const b=document.getElementById("brief"),e=document.getElementById("examples");
  if(document.activeElement!==b) b.value=S.briefing;
  if(document.activeElement!==e) e.value=S.examples;
  document.getElementById("prog").textContent=fill(T.prog,{filled:S.filled,total:S.total});
  const r=document.getElementById("ready");
  if(S.ready){r.className="callout ok";r.textContent=T.ready;}
  else{r.className="callout warn";r.textContent=T.missing;}
  document.getElementById("agentline").value=fill(T.agentline,{folder:S.folder});
  document.getElementById("copynote").textContent=S.has_copy?T.hascopy:T.nocopy;
}
async function save(){
  await fetch("/save",{method:"POST",body:JSON.stringify({
    briefing:document.getElementById("brief").value,
    examples:document.getElementById("examples").value})});
  await load();notify(T.saved);
}
async function copyAgent(){
  await navigator.clipboard.writeText(document.getElementById("agentline").value);
  notify(T.copied);
}
load();
</script></body></html>"""


_REV_T = {
    "title": "Review copy",
    "meta": "local · {origin}",
    "stats": "<span class='stat'><b>{total}</b> rows</span><span class='stat'><b>{approved}</b> approved</span>"
             "<span class='stat'><b>{pending}</b> pending</span><span class='stat'><b>{rejected}</b> rejected</span>"
             "<span class='stat'><b>{redo}</b> redo</span>",
    "legend": "Legend:",
    "lbl.working": "Working", "lbl.approved": "Approved", "lbl.pending": "Pending",
    "lbl.rejected": "Rejected", "lbl.redo": "Redo",
    "sing.pending": "pending", "sing.approved": "approved", "sing.rejected": "rejected", "sing.redo": "redo",
    "dest.all": "All", "dest.ppc": "PPC", "dest.overlay": "Overlay",
    "allconcepts": "All concepts ({n})",
    "concept": "Concept:",
    "th.status": "Status", "th.dest": "Dest", "th.concept": "Concept", "th.axis": "Axis",
    "th.kind": "Kind", "th.text": "Text", "th.lang": "Lang", "th.acts": "Actions",
    "approve": "Approve", "reject": "Reject", "redo": "Redo",
    "regenask": "What to adjust in this copy? (note required)",
    "approvetoast": "Copy approved.", "rejecttoast": "Copy rejected — the agent recreates.",
    "regentoast": "Marked for redo — the agent rewrites with the note.",
    "empty": "No rows in this filter.",
    "p3.title": "Review copy",
    "p3.desc": "Approve/reject/redo row by row. Nothing ships unapproved. Redo requires a note.",
    "p4.title": "Deliver",
    "p4.desc": "Exports only approved copy to sheets (Meta / Google RSA / overlay) in the Desktop folder.",
    "p4.hint": "CSV + XLSX. URL/budget/IDs are left blank for the PPC team.",
    "continue": "Export approved",
    "deliver.done": "{n} approved rows exported to {dir}",
    "deliver.empty": "No approved copy — approve rows in the table first.",
    "deliver.toast": "{n} rows exported.",
    "deliver.warn": "RSA limits exceeded (truncated on export)",
    "openfolder": "Open folder",
    "openfolder.toast": "Folder opened: {dir}",
    "openfolder.empty": "empty delivery folder — export first",
}


def review_page():
    t = _REV_T
    return _head(t["title"]) + f"""
<header><span class="brand">copy-kit</span><h1 id="title">{t['title']}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button onclick="load()">{i18n.t('btn.refresh')}</button></header>
<div class="banner">
""" + _stepper(3, 2) + f"""
<div class="stats" id="stats"></div>
<div class="legend"><b>{t['legend']}</b>
<span class="tag approved"><span class="dot"></span>{t['sing.approved']}</span>
<span class="tag"><span class="dot"></span>{t['sing.pending']}</span>
<span class="tag rejected"><span class="dot"></span>{t['sing.rejected']}</span>
<span class="tag redo"><span class="dot"></span>{t['sing.redo']}</span></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">3</span>{t['p3.title']}</h2>
<p class="desc">{t['p3.desc']}</p>
<div class="filters" id="filters"></div>
<div class="filters" id="dfilters"></div>
<div class="row" style="align-items:center"><span class="meta">{t['concept']}</span><div class="filters" id="cfilters"></div></div>
<div class="tablewrap"><table class="copy">
<thead><tr><th>{t['th.status']}</th><th>{t['th.dest']}</th><th>{t['th.concept']}</th><th>{t['th.axis']}</th>
<th>{t['th.kind']}</th><th>{t['th.text']}</th><th>{t['th.lang']}</th><th>{t['th.acts']}</th></tr></thead>
<tbody id="tbody"></tbody></table></div></div>
<div class="panel"><h2><span class="n">4</span>{t['p4.title']}</h2>
<p class="desc">{t['p4.desc']}</p>
<div class="row" style="align-items:center"><button class="btn primary" onclick="continueBatch()">{t['continue']}</button>
<button class="btn" id="openfolder" onclick="openFolder()" style="display:none">{t['openfolder']}</button>
<span class="meta">{t['p4.hint']}</span></div>
<div id="deliver-result"></div></div>
</div>
""" + ui._modal() + ui._JS_UTIL + (
        '<script>const T=' + json.dumps(t, ensure_ascii=False) + ';</script>') + """
<script>
let state=null,filter="working",dest="all",cf="all",last="";
const LBL={working:T["lbl.working"],approved:T["lbl.approved"],pending:T["lbl.pending"],rejected:T["lbl.rejected"],redo:T["lbl.redo"]};
const SING={pending:T["sing.pending"],approved:T["sing.approved"],rejected:T["sing.rejected"],redo:T["sing.redo"]};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
async function load(){applyState(await (await fetch("/state")).json());}
function applyState(s){
  state=s;last=JSON.stringify(s);
  document.getElementById("title").textContent=s.folder+" · "+T.title;
  document.getElementById("meta").textContent=fill(T.meta,{origin:location.origin});
  const c=st=>s.rows.filter(r=>r.status===st).length;
  const working=s.rows.filter(r=>r.status!=="approved").length;
  document.getElementById("stats").innerHTML=fill(T.stats,
    {total:s.rows.length,approved:c("approved"),pending:c("pending"),rejected:c("rejected"),redo:c("redo")});
  const counts={working,approved:c("approved"),pending:c("pending"),rejected:c("rejected"),redo:c("redo")};
  document.getElementById("filters").innerHTML=Object.entries(counts)
    .map(([k,v])=>`<button class="${k===filter?'on':''}" onclick="setFilter('${k}')">${LBL[k]} (${v})</button>`).join("");
  document.getElementById("dfilters").innerHTML=["all","ppc","overlay"].map(d=>
    `<button class="${d===dest?'on':''}" onclick="setDest('${d}')">${T["dest."+d]} (${d==="all"?s.rows.length:s.rows.filter(r=>r.destination===d).length})</button>`).join("");
  const cc={};for(const r of s.rows)cc[r.concept]=(cc[r.concept]||0)+1;
  const concepts=(s.concepts&&s.concepts.length?s.concepts:Object.keys(cc));
  document.getElementById("cfilters").innerHTML=
    `<button class="${cf==='all'?'on':''}" onclick="setConcept('all')">${fill(T.allconcepts,{n:s.rows.length})}</button>`+
    concepts.map(k=>`<button class="${cf===k?'on':''}" onclick="setConcept('${esc(k)}')">${esc(k)} (${cc[k]||0})</button>`).join("");
  draw();
}
function setFilter(f){filter=f;draw();}
function setDest(d){dest=d;draw();}
function setConcept(k){cf=k;draw();}
function draw(){
  const items=state.rows.filter(r=>
    (filter==="working"?r.status!=="approved":r.status===filter)&&
    (dest==="all"||r.destination===dest)&&(cf==="all"||r.concept===cf));
  const tb=document.getElementById("tbody");
  if(!items.length){tb.innerHTML=`<tr><td colspan="8"><div class="empty">${T.empty}</div></td></tr>`;return;}
  tb.innerHTML=items.map(r=>{
    const note=(r.status==="redo"&&r.note)?`<div class="hint">↻ ${esc(r.note)}</div>`:"";
    return `<tr>
      <td><span class="tag ${r.status}"><span class="dot"></span>${SING[r.status]}</span></td>
      <td>${esc(r.destination)}</td><td>${esc(r.concept)}</td><td>${esc(r.axis)}</td>
      <td>${esc(r.kind)}</td><td class="txt">${esc(r.text)}${note}</td><td>${esc(r.lang)}</td>
      <td class="acts">
        <button class="btn ok" onclick="decide('${r.id}','approved')">${T.approve}</button>
        <button class="btn no" onclick="decide('${r.id}','rejected')">${T.reject}</button>
        <button class="btn" onclick="regen('${r.id}')">${T.redo}</button></td>
    </tr>`;}).join("");
}
async function decide(id,status){
  await fetch("/decide",{method:"POST",body:JSON.stringify({id,status,who:"user"})});
  await load();notify(status==="approved"?T.approvetoast:T.rejecttoast);
}
async function regen(id){
  const note=await ask(T.regenask);
  if(note===null||note.trim()==="")return;
  const r=await fetch("/decide",{method:"POST",body:JSON.stringify({id,status:"redo",note,who:"user"})});
  if(!r.ok){await tell((await r.json()).error);return;}
  await load();notify(T.regentoast);
}
async function poll(){
  if(document.querySelector("dialog[open]"))return;
  const s=await (await fetch("/state")).json();
  if(JSON.stringify(s)!==last)applyState(s);
}
function setStep(n){document.querySelectorAll(".stepper .step").forEach(el=>{
  const i=+el.dataset.step;el.classList.toggle("done",i<n);el.classList.toggle("current",i===n);
  const d=el.querySelector(".n");if(d)d.textContent=i<n?"✓":String(i);});}
async function continueBatch(){
  const r=await fetch("/deliver",{method:"POST",body:"{}"});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"error");return;}
  const box=document.getElementById("deliver-result");
  if(j.exported===0){box.innerHTML="";notify(T["deliver.empty"]);return;}
  let html=`<div class="callout ok">${fill(T["deliver.done"],{n:j.exported,dir:esc(j.dir)})}</div>`;
  if(j.warnings&&j.warnings.length)
    html+=`<div class="callout warn">${T["deliver.warn"]}: ${j.warnings.map(w=>esc(w.id+" "+w.kind+" "+w.chars+">"+w.limit)).join(", ")}</div>`;
  html+=`<div class="row" style="flex-wrap:wrap;margin-top:10px">`+
    j.files.map(f=>`<a class="btn" href="/download?file=${encodeURIComponent(f)}" download>${esc(f)}</a>`).join("")+`</div>`;
  box.innerHTML=html;
  document.getElementById("openfolder").style.display="";
  notify(fill(T["deliver.toast"],{n:j.exported}));
  setStep(4);
}
async function openFolder(){
  const r=await fetch("/open-folder",{method:"POST",body:"{}"});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"error");return;}
  notify(fill(T["openfolder.toast"],{dir:esc(j.path)}));
}
load();
setInterval(poll,4000);
</script></body></html>"""


class CopyHandler(ui.Handler):
    """Inherits _send/_safe/log_message from ui.Handler; own routes."""

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            page = wizard_page() if self.mode == "onboard" else review_page()
            self._send(200, page.encode(), "text/html; charset=utf-8")
        elif url.path == "/state":
            if self.mode == "onboard":
                brief = copy.read_text(self.root, "briefing.md")
                filled, total = _brief_progress(brief)
                self._send(200, {
                    "folder": self.root, "briefing": brief,
                    "examples": copy.read_text(self.root, "examples.txt"),
                    "filled": filled, "total": total, "ready": filled > 0,
                    "has_copy": os.path.isfile(os.path.join(self.root, "copy.json"))})
            else:
                payload = copy.review_payload(self.root)
                if payload is None:
                    return self._send(200, {"folder": os.path.basename(self.root),
                                            "rows": [], "counts": {}, "concepts": []})
                data = copy.load(self.root)
                payload["folder"] = os.path.basename(self.root)
                payload["concepts"] = data.get("concepts") or []
                self._send(200, payload)
        elif url.path == "/download":
            fname = os.path.basename(parse_qs(url.query).get("file", [""])[0])
            d = copy.delivery_dir(self.root)
            path = os.path.realpath(os.path.join(d, fname))
            if not fname or not path.startswith(os.path.realpath(d) + os.sep) or not os.path.isfile(path):
                return self._send(404, {"error": "not found"})
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        url = urlparse(self.path)
        if self.mode == "onboard":
            if url.path == "/save":
                with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                    f.write(payload.get("briefing", ""))
                with open(os.path.join(self.root, "examples.txt"), "w", encoding="utf-8") as f:
                    f.write(payload.get("examples", ""))
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})
        if url.path == "/decide":
            try:
                found = copy.decide(self.root, payload.get("id"), payload.get("status"),
                                    payload.get("note", ""), payload.get("who", ""))
            except ValueError as e:
                return self._send(400, {"error": str(e)})
            if not found:
                return self._send(404, {"error": "unknown id"})
            return self._send(200, {"ok": True})
        if url.path == "/deliver":
            return self._send(200, copy.deliver(self.root))
        if url.path == "/open-folder":
            d = copy.delivery_dir(self.root)
            if not os.path.isdir(d):
                return self._send(400, {"error": "empty delivery folder — export first"})
            ui._open_folder(d)
            return self._send(200, {"ok": True, "path": d})
        self._send(404, {"error": "not found"})


def _serve(folder, port, open_browser, shortcut_name):
    server = None
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), CopyHandler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError(f"no free port in {port}..{port + 19}")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shortcut = os.path.join(folder, shortcut_name)
    with open(shortcut, "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0;url={url}">'
                '<title>copy-kit</title></head>'
                '<body style="font-family:system-ui,sans-serif;padding:40px">'
                f'<p>{i18n.t("cli.shortcut.opening", url=url)} <a href="{url}">{url}</a></p>'
                f'<p>{i18n.t("cli.shortcut.manual")}</p>'
                '</body></html>\n')
    print(f"\n  ➜  {url}\n  ({i18n.t('cli.serve.shortcut', name=shortcut_name)})\n", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server, url


def serve_onboard(folder, port=8767, open_browser=True):
    folder = os.path.abspath(os.path.expanduser(folder))
    copy.scaffold(folder)
    CopyHandler.mode = "onboard"
    CopyHandler.root = folder
    return _serve(folder, port, open_browser, "OPEN-COPY.html")


def serve_review(folder, port=8768, open_browser=True):
    folder = os.path.abspath(os.path.expanduser(folder))
    CopyHandler.mode = "review"
    CopyHandler.root = folder
    return _serve(folder, port, open_browser, "OPEN-COPY-REVIEW.html")