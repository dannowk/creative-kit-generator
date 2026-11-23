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
table.copy .cnt{color:var(--mut);font-size:11.5px;white-space:nowrap}
table.copy .cnt.over{color:#B42318;font-weight:600}
.tag.new{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.queuelist{margin:8px 0 0;padding-left:18px}
.queuelist li{margin:3px 0}
table.copy .acts{white-space:nowrap}
table.copy .acts button{min-height:28px;padding:3px 9px;font-size:12.5px}
.fieldlabel{font-size:12.5px;color:var(--mut);font-weight:600}
.drop{border:2px dashed var(--line);border-radius:10px;padding:11px 14px;color:var(--mut);
 font-size:13px;cursor:pointer;margin:6px 0 10px;text-align:center;background:#fbfcfd;line-height:1.45}
.drop:hover,.drop.over{border-color:#0B6BCB;color:#0B6BCB;background:#f2f8ff}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}
.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:999px;
 padding:3px 6px 3px 12px;font-size:12.5px;background:var(--surface)}
.chip .sz{color:var(--mut);font-size:11.5px}
.chip button{border:none;background:none;cursor:pointer;color:var(--mut);font-size:15px;padding:0 5px;line-height:1}
.chip button:hover{color:#C62828}
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
    "brief.attach": "Have the briefing in a file? Drop it here or click to browse — .md/.txt content goes straight into the field.",
    "examples.label": "Example texts (paste copy you like / want to use as a model)",
    "examples.attach": "Already have copy written in a file? Drop it here or click to browse — .md/.txt content goes straight into the field.",
    "attach.list": "Attached files (the agent reads them — PDF/docx are extracted with its tools):",
    "attach.toast": "File attached — saved in the folder for the agent.",
    "attach.text": "File attached and its content inserted into the field.",
    "attach.err": "Could not attach the file.",
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
<div class="drop" id="drop-briefing" onclick="pick('briefing')" title="{t['brief.attach']}">⬇ {t['brief.attach']}</div>
<label class="fieldlabel" for="examples">{t['examples.label']}</label>
<textarea id="examples" style="min-height:180px"></textarea>
<div class="drop" id="drop-examples" onclick="pick('examples')" title="{t['examples.attach']}">⬇ {t['examples.attach']}</div>
<div id="attachwrap" style="display:none">
<label class="fieldlabel">{t['attach.list']}</label>
<div class="chips" id="chips"></div></div>
<input type="file" id="filepick" multiple style="display:none">
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
let S=null,pickSlot="examples";
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const TEXT_EXT=/\\.(md|markdown|txt|csv|json|rtf)$/i;
const fmtSize=n=>n<1024?n+" B":n<1048576?(n/1024).toFixed(0)+" KB":(n/1048576).toFixed(1)+" MB";
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
  const atts=S.attachments||[];
  document.getElementById("attachwrap").style.display=atts.length?"":"none";
  document.getElementById("chips").innerHTML=atts.map(a=>
    `<span class="chip">${esc(a.name)} <span class="sz">${fmtSize(a.size)}</span>`+
    `<button title="Remove" onclick="detach('${esc(a.name)}')">×</button></span>`).join("");
  document.getElementById("agentline").value=fill(T.agentline,{folder:S.folder});
  document.getElementById("copynote").textContent=S.has_copy?T.hascopy:T.nocopy;
}
async function save(msg){
  await fetch("/save",{method:"POST",body:JSON.stringify({
    briefing:document.getElementById("brief").value,
    examples:document.getElementById("examples").value})});
  await load();notify(msg||T.saved);
}
function pick(slot){pickSlot=slot;document.getElementById("filepick").click();}
document.getElementById("filepick").addEventListener("change",e=>{
  handleFiles(e.target.files);e.target.value="";});
for(const slot of ["briefing","examples"]){
  const z=document.getElementById("drop-"+slot);
  z.addEventListener("dragover",e=>{e.preventDefault();z.classList.add("over");});
  z.addEventListener("dragleave",e=>{e.preventDefault();z.classList.remove("over");});
  z.addEventListener("drop",e=>{e.preventDefault();z.classList.remove("over");handleFiles(e.dataTransfer.files,slot);});
}
async function handleFiles(files,slot){
  slot=slot||pickSlot;
  let anyText=false,ok=0;
  for(const f of files){
    const r=await fetch("/attach?slot="+slot+"&name="+encodeURIComponent(f.name),
      {method:"POST",headers:{"Content-Type":"application/octet-stream"},body:f});
    if(!r.ok){await tell(T["attach.err"]+" ("+esc(f.name)+")");continue;}
    ok++;
    if(TEXT_EXT.test(f.name)){
      const txt=(await f.text()).trim();
      if(txt){
        const ta=document.getElementById(slot==="briefing"?"brief":"examples");
        ta.value=(ta.value.trim()?ta.value.replace(/\\s*$/,"")+"\\n\\n":"")+txt+"\\n";
        anyText=true;
      }
    }
  }
  if(ok){
    if(anyText) await save(T["attach.text"]);
    else{await load();notify(T["attach.toast"]);}
  }
}
async function detach(name){
  const r=await fetch("/detach",{method:"POST",body:JSON.stringify({name})});
  if(!r.ok){await tell((await r.json()).error||"error");return;}
  await load();
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
    "pf.all": "All platforms", "pf.google": "Google", "pf.meta": "Meta",
    "stratnote": "Strategist's note",
    "metacta": "Recommended Meta CTA:",
    "allconcepts": "All concepts ({n})",
    "concept": "Concept:",
    "allprograms": "All programs",
    "program": "Program:",
    "th.status": "Status", "th.concept": "Concept", "th.program": "Program",
    "th.platform": "Platform", "th.type": "Type", "th.text": "Text", "th.acts": "Actions",
    "axis.hint": "axis",
    "pl.google": "Google", "pl.meta": "Meta", "pl.both": "Google + Meta", "pl.overlay": "Overlay",
    "kind.headline": "Headline", "kind.description": "Description",
    "kind.primary_text": "Primary text", "kind.link_description": "Link description",
    "kind.cta": "CTA button", "kind.hook": "Hook", "kind.kicker": "Kicker",
    "kind.program": "Program line",
    "approve": "Approve", "reject": "Reject", "redo": "Redo",
    "regenask": "What to adjust in this copy? (note required)",
    "queue.title": "Working queue — {n} row(s) marked for rewrite.",
    "queue.hint": "The agent rewrites these and the table updates by itself. You can close the browser and check later — rewritten rows come back as pending, marked NEW since your last visit.",
    "queue.rewrite": "rewrite (rejected)",
    "newbadge": "NEW",
    "approvetoast": "Copy approved.", "rejecttoast": "Copy rejected — the agent recreates.",
    "regentoast": "Marked for redo — the agent rewrites with the note.",
    "empty": "No rows in this filter.",
    "p3.title": "Review copy",
    "p3.desc": "Approve/reject/redo row by row. Nothing ships unapproved. Redo requires a note.",
    "p4.title": "Deliver",
    "p4.desc": "Exports only approved copy to the Desktop folder: copy_manifest + overlay (vertical — one text per row, with Concept and Program) and the Meta / Google RSA import files.",
    "p4.hint": "CSV + XLSX. Approve in the vertical sheets; upload with the Meta/Google ones. URL/budget/IDs are left blank for the PPC team.",
    "continue": "Export approved",
    "deliver.locked": "Export is locked — the agent is still working on {n} marked row(s). It unlocks when every change is done.",
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
<div class="callout warn" id="queue" style="display:none"></div>
<div class="filters" id="filters"></div>
<div class="filters" id="dfilters"></div>
<div class="filters" id="pfilters"></div>
<div class="row" style="align-items:center"><span class="meta">{t['concept']}</span><div class="filters" id="cfilters"></div></div>
<div class="row" id="prow" style="align-items:center;display:none"><span class="meta">{t['program']}</span><div class="filters" id="prfilters"></div></div>
<div class="callout" id="strat" style="display:none"></div>
<div class="tablewrap"><table class="copy">
<thead><tr><th>{t['th.status']}</th><th>{t['th.concept']}</th><th>{t['th.program']}</th>
<th>{t['th.platform']}</th><th>{t['th.type']}</th><th>{t['th.text']}</th><th>{t['th.acts']}</th></tr></thead>
<tbody id="tbody"></tbody></table></div></div>
<div class="panel"><h2><span class="n">4</span>{t['p4.title']}</h2>
<p class="desc">{t['p4.desc']}</p>
<div class="row" style="align-items:center"><button class="btn primary" id="exportbtn" onclick="continueBatch()">{t['continue']}</button>
<button class="btn" id="openfolder" onclick="openFolder()" style="display:none">{t['openfolder']}</button>
<span class="meta">{t['p4.hint']}</span></div>
<div class="callout warn" id="lockhint" style="display:none"></div>
<div id="deliver-result"></div></div>
</div>
""" + ui._modal() + ui._JS_UTIL + (
        '<script>const T=' + json.dumps(t, ensure_ascii=False) + ';</script>') + """
<script>
let state=null,filter="working",dest="all",pf="all",cf="all",prf="all",last="",seenBefore=null;
const LBL={working:T["lbl.working"],approved:T["lbl.approved"],pending:T["lbl.pending"],rejected:T["lbl.rejected"],redo:T["lbl.redo"]};
const SING={pending:T["sing.pending"],approved:T["sing.approved"],rejected:T["sing.rejected"],redo:T["sing.redo"]};
const LIM={headline:30,description:90,link_description:40};
const KIND={};for(const k of ["headline","description","primary_text","link_description","cta","hook","kicker","program"])KIND[k]=T["kind."+k]||k;
const PLAT={google:T["pl.google"],meta:T["pl.meta"],both:T["pl.both"]};
const platLbl=r=>r.destination==="ppc"?(PLAT[r.platform||"both"]||T["pl.both"]):T["pl.overlay"];
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
  const pc={google:0,meta:0};
  for(const r of s.rows){if(r.destination!=="ppc")continue;const p=r.platform||"both";
    if(p==="both"){pc.google++;pc.meta++;}else if(pc[p]!==undefined)pc[p]++;}
  document.getElementById("pfilters").innerHTML=["all","google","meta"].map(p=>
    `<button class="${p===pf?'on':''}" onclick="setPf('${p}')">${T["pf."+p]}${p==="all"?"":" ("+pc[p]+")"}</button>`).join("");
  const st=document.getElementById("strat");
  if(s.strategy_note||s.meta_cta){
    st.style.display="";st.className="callout ok";
    st.innerHTML=(s.strategy_note?`<b>${T.stratnote}:</b> ${esc(s.strategy_note)}`:"")+
      (s.meta_cta?`${s.strategy_note?" &middot; ":""}<b>${T.metacta}</b> ${esc(s.meta_cta)}`:"");
  }else{st.style.display="none";}
  if(seenBefore===null&&s.folder){
    const k="ck.lastseen.copy."+s.folder;
    seenBefore=localStorage.getItem(k)||"";
    localStorage.setItem(k,new Date().toISOString());
  }
  const q=s.rows.filter(r=>r.status==="rejected"||r.status==="redo");
  const qel=document.getElementById("queue");
  if(q.length){
    qel.style.display="";
    qel.innerHTML=`<b>${fill(T["queue.title"],{n:q.length})}</b> <span class="hint">${T["queue.hint"]}</span>`+
      `<ul class="queuelist">`+q.map(r=>{
        const what=r.status==="redo"?`↻ ${esc(r.note||"")}`:`✕ ${T["queue.rewrite"]}`;
        const when=r.updated_at?` · ${new Date(r.updated_at).toLocaleString()}`:"";
        const prog=r.program?` · ${esc(r.program)}`:"";
        return `<li><b>${esc(r.id)}</b> — ${esc(r.concept)}${prog} · ${platLbl(r)} · ${esc(KIND[r.kind]||r.kind)} — ${what}<span class="hint">${when}</span></li>`;
      }).join("")+`</ul>`;
  }else qel.style.display="none";
  const eb=document.getElementById("exportbtn"),lh=document.getElementById("lockhint");
  eb.disabled=q.length>0;
  if(q.length){lh.style.display="";lh.textContent=fill(T["deliver.locked"],{n:q.length});}
  else lh.style.display="none";
  const cc={};for(const r of s.rows)cc[r.concept]=(cc[r.concept]||0)+1;
  const concepts=(s.concepts&&s.concepts.length?s.concepts:Object.keys(cc));
  document.getElementById("cfilters").innerHTML=
    `<button class="${cf==='all'?'on':''}" onclick="setConcept('all')">${fill(T.allconcepts,{n:s.rows.length})}</button>`+
    concepts.map(k=>`<button class="${cf===k?'on':''}" onclick="setConcept('${esc(k)}')">${esc(k)} (${cc[k]||0})</button>`).join("");
  const pc2={};for(const r of s.rows){const p=(r.program||"").trim();if(p)pc2[p]=(pc2[p]||0)+1;}
  const progs=Object.keys(pc2).sort();
  const prow=document.getElementById("prow");
  if(progs.length>1){
    prow.style.display="";
    document.getElementById("prfilters").innerHTML=
      `<button class="${prf==='all'?'on':''}" onclick="setProgram('all')">${T.allprograms} (${s.rows.length})</button>`+
      progs.map(p=>`<button class="${prf===p?'on':''}" onclick="setProgram('${esc(p)}')">${esc(p)} (${pc2[p]})</button>`).join("");
  }else{prow.style.display="none";prf="all";}
  draw();
}
function setFilter(f){filter=f;draw();}
function setDest(d){dest=d;draw();}
function setPf(p){pf=p;draw();}
function setConcept(k){cf=k;draw();}
function setProgram(p){prf=p;draw();}
function draw(){
  const items=state.rows.filter(r=>
    (filter==="working"?r.status!=="approved":r.status===filter)&&
    (dest==="all"||r.destination===dest)&&
    (pf==="all"||r.destination!=="ppc"||(r.platform||"both")==="both"||(r.platform||"both")===pf)&&
    (cf==="all"||r.concept===cf)&&
    (prf==="all"||(r.program||"")===prf));
  const tb=document.getElementById("tbody");
  if(!items.length){tb.innerHTML=`<tr><td colspan="7"><div class="empty">${T.empty}</div></td></tr>`;return;}
  tb.innerHTML=items.map(r=>{
    const note=(r.status==="redo"&&r.note)?`<div class="hint">↻ ${esc(r.note)}</div>`:"";
    const n=(r.text||"").length,lim=LIM[r.kind];
    const cnt=lim?` <span class="cnt${n>lim?" over":""}">[${n}/${lim}]</span>`
      :(r.destination==="ppc"?` <span class="cnt">[${n}]</span>`:"");
    const axis=(r.axis&&r.axis!=="default")?`<div class="hint">${T["axis.hint"]}: ${esc(r.axis)}</div>`:"";
    const isnew=(seenBefore&&r.updated_at&&r.updated_at>seenBefore&&r.status==="pending")
      ?` <span class="tag new"><span class="dot"></span>${T.newbadge}</span>`:"";
    return `<tr>
      <td><span class="tag ${r.status}"><span class="dot"></span>${SING[r.status]}</span>${isnew}</td>
      <td><b>${esc(r.concept)}</b>${axis}</td>
      <td>${esc(r.program||"—")}</td>
      <td>${esc(platLbl(r))}</td>
      <td>${esc(KIND[r.kind]||r.kind)}</td>
      <td class="txt">${esc(r.text)}${cnt}${note}</td>
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
  if(j.locked>0){box.innerHTML="";notify(fill(T["deliver.locked"],{n:j.locked}));return;}
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
                    "attachments": copy.attachments(self.root),
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
                payload["strategy_note"] = data.get("strategy_note") or ""
                payload["meta_cta"] = data.get("meta_cta") or ""
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
        raw = self.rfile.read(length) if length else b""
        url = urlparse(self.path)
        if self.mode == "onboard":
            if url.path == "/attach":
                q = parse_qs(url.query)
                slot = q.get("slot", ["examples"])[0]
                name = q.get("name", [""])[0]
                if slot not in ("briefing", "examples") or not os.path.basename(name).strip():
                    return self._send(400, {"error": "bad request"})
                if not raw:
                    return self._send(400, {"error": "empty file"})
                stored = copy.save_attachment(self.root, name, raw)
                return self._send(200, {"ok": True, "name": stored})
            payload = json.loads(raw or b"{}")
            if url.path == "/save":
                with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                    f.write(payload.get("briefing", ""))
                with open(os.path.join(self.root, "examples.txt"), "w", encoding="utf-8") as f:
                    f.write(payload.get("examples", ""))
                return self._send(200, {"ok": True})
            if url.path == "/detach":
                if copy.remove_attachment(self.root, payload.get("name", "")):
                    return self._send(200, {"ok": True})
                return self._send(404, {"error": "not found"})
            return self._send(404, {"error": "not found"})
        payload = json.loads(raw or b"{}")
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