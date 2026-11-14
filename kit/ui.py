"""UI local (onboarding + revisão): http.server da stdlib + páginas claras. Zero npm, zero build.

Sobe em 127.0.0.1. Tema claro com passos numerados e legenda de status para a pessoa se
localizar; onboarding prepara a pasta, revisão deixa aprovar/rejeitar/refazer por clique e
enfileira pedidos de regeneração que o agente executa. Morre quando você fecha.

Bilíngue PT/EN: o toggle no header grava cookie `lang` e recarrega; as páginas são
montadas por idioma (chrome server-side + dicionário T injetado pro JS dinâmico) e os
dados (slots, gaps, achados de compliance) também saem localizados.
"""

import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import yaml

from . import campaign, i18n, intake, onboard

_STYLE = """<style>
:root{color-scheme:light;
 --bg:#f5f6f8;--surface:#ffffff;--line:#dfe3e8;--ink:#182026;--mut:#5a6673;
 --accent:#0b6bcb;--accent-dk:#0957a6;
 --ok:#177245;--ok-bg:#e6f4ec;--ok-line:#bfe3cd;
 --warn:#8a5a00;--warn-bg:#fff6e0;--warn-line:#f0dca8;
 --bad:#b3261e;--bad-bg:#fdecea;--bad-line:#f3c1bd;
 --pend:#5a6673;--pend-bg:#eef1f4;--pend-line:#dfe3e8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{position:sticky;top:0;z-index:10;background:var(--surface);border-bottom:1px solid var(--line);
 padding:12px 24px;display:flex;align-items:center;gap:12px}
header .brand{font-weight:700;font-size:12px;letter-spacing:.04em;color:var(--accent);text-transform:uppercase}
header h1{font-size:17px;margin:0;font-weight:650}
.meta{color:var(--mut);font-size:13px}
.sp{flex:1}
button,.btn{min-height:36px;padding:8px 14px;border-radius:9px;border:1px solid var(--line);
 background:var(--surface);color:var(--ink);font-size:14px;cursor:pointer;
 display:inline-flex;align-items:center;gap:6px}
button:hover,.btn:hover{background:#f2f4f7}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-dk)}
.btn.ok{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.btn.no{background:var(--bad-bg);border-color:var(--bad-line);color:var(--bad)}
a.btn{text-decoration:none}
.langbtn{min-height:30px;padding:3px 10px;font-size:12.5px;font-weight:600}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.banner{max-width:1160px;margin:18px auto 0;padding:0 24px;display:grid;gap:10px}
.stepper{display:flex;align-items:center;flex-wrap:wrap;gap:0}
.step{display:flex;align-items:center;gap:8px;color:var(--mut);font-size:13px}
.step .n{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;
 border:1.5px solid var(--line);background:var(--surface);font-weight:600;font-size:13px}
.step.done .n{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.step.current .n{background:var(--accent);border-color:var(--accent);color:#fff}
.step.current{color:var(--ink);font-weight:600}
.step .bar{width:26px;height:1.5px;background:var(--line);margin:0 8px}
.wrap{max-width:1160px;margin:0 auto;padding:16px 24px 72px;display:grid;gap:20px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;
 display:grid;gap:12px;box-shadow:0 1px 2px rgba(16,24,32,.05)}
.panel>h2{display:flex;align-items:center;gap:10px;font-size:16px;margin:0;font-weight:650}
.panel>h2 .n{width:26px;height:26px;border-radius:8px;background:var(--accent);color:#fff;
 display:grid;place-items:center;font-size:14px;font-weight:700;flex:none}
.panel .desc{color:var(--mut);font-size:13px;margin:-4px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;display:flex;
 flex-direction:column;box-shadow:0 1px 2px rgba(16,24,32,.05);overflow:hidden}
.card.drag{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,107,203,.15)}
.dropzone{border:1.5px dashed var(--line);border-radius:12px;padding:12px 14px;display:flex;
 flex-wrap:wrap;gap:10px;align-items:center;background:#fbfcfd}
.dropzone.drag{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,107,203,.15)}
.card .body{padding:14px 16px;display:flex;flex-direction:column;gap:10px;flex:1}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tag{font-size:12px;font-weight:600;padding:3px 10px;border-radius:99px;border:1px solid var(--pend-line);
 background:var(--pend-bg);color:var(--pend);display:inline-flex;align-items:center;gap:6px}
.tag.approved{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.tag.rejected{background:var(--bad-bg);border-color:var(--bad-line);color:var(--bad)}
.tag.redo{background:#e7f0fb;border-color:#bcd6f2;color:var(--accent)}
.tag.blocked{background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn)}
.tag .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.hint{color:var(--mut);font-size:13px;margin:0}
.files{margin:0;padding:0;list-style:none;font-size:13px;display:grid;gap:4px}
.files li{display:flex;justify-content:space-between;gap:8px;background:var(--pend-bg);border-radius:8px;padding:4px 8px}
.files li .docremove{min-height:22px;padding:0 8px;font-size:12px;line-height:1;border-radius:6px}
.docsblock{display:grid;gap:8px;border-top:1px solid var(--line);padding-top:12px;margin-top:2px}
.files .meta{color:var(--mut)}
textarea{width:100%;min-height:300px;background:#fbfcfd;color:var(--ink);border:1px solid var(--line);
 border-radius:10px;padding:12px;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
input[type=text]{background:#fbfcfd;color:var(--ink);border:1px solid var(--line);border-radius:9px;
 padding:8px 12px;font-size:14px;min-height:36px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.sw{width:26px;height:26px;border-radius:7px;display:inline-block;border:1px solid var(--line);vertical-align:middle}
.gap{display:grid;gap:6px;padding:12px 0;border-top:1px solid var(--line)}
.gap .why{color:var(--mut);font-size:13px}
code{background:var(--pend-bg);border:1px solid var(--pend-line);border-radius:6px;padding:1px 6px;font-size:12.5px}
.callout{border-radius:10px;padding:10px 14px;font-size:14px;display:flex;gap:8px;align-items:center}
.callout.ok{background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-line)}
.callout.warn{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn-line)}
.legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--mut);font-size:12.5px;align-items:center}
.stats{display:flex;gap:10px;flex-wrap:wrap}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px 12px;font-size:13px;color:var(--mut)}
.stat b{font-size:15px;color:var(--ink)}
.rgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.rcard img{width:100%;display:block;cursor:zoom-in;background:#eceff2;aspect-ratio:1/1;object-fit:contain}
.rcard video{width:100%;display:block;background:#eceff2;aspect-ratio:1/1;object-fit:contain}
.rcard .name{font-size:13px;color:var(--mut)}
.findings{margin:0;padding:0;list-style:none;font-size:12.5px;display:grid;gap:4px}
.findings li.fail{color:var(--bad)}
.findings li.warn{color:var(--warn)}
dialog{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:14px;max-width:92vw;padding:8px}
dialog img{max-width:88vw;max-height:82vh;display:block;border-radius:8px}
dialog::backdrop{background:rgba(20,26,32,.55)}
.empty{padding:60px 20px;color:var(--mut);text-align:center}
.filters{display:flex;gap:8px;flex-wrap:wrap}
.filters button.on{background:var(--accent);border-color:var(--accent);color:#fff}
.stylepanel{display:grid;gap:12px;border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0;background:#fbfcfd}
.stylepanel .desc{margin:0}
.stylegrid{display:flex;gap:16px;flex-wrap:wrap}
.stylefield{display:grid;gap:4px}
.stylefield label{font-size:12px;color:var(--mut);text-transform:capitalize}
.stylefield input[type=color]{width:56px;height:34px;padding:2px;border:1px solid var(--line);border-radius:8px;background:#fff;cursor:pointer}
.stylefield input[type=text]{width:200px}
.stylenote{min-height:64px}
.stylelabel{font-size:12.5px;color:var(--mut);font-weight:600}
dialog .msgbody{display:grid;gap:12px;padding:10px 12px;min-width:320px;max-width:480px}
dialog .msgbody p{margin:0;font-size:14px}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:50;
 background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:10px;
 padding:10px 16px;font-size:14px;box-shadow:0 4px 16px rgba(16,24,32,.15);max-width:90vw}
</style>"""

_STEPS = {
    "pt": ["Arquivos", "Briefing", "Marca", "Gerar", "Revisar", "Entregar"],
    "en": ["Files", "Briefing", "Brand", "Generate", "Review", "Deliver"],
}


def _head(title, lang):
    return ('<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>campaign-kit · ' + title + '</title>' + _STYLE + '</head><body>')


def _stepper(current, done, lang):
    steps = _STEPS.get(lang, _STEPS["pt"])
    out = ['<div class="stepper">']
    for i, label in enumerate(steps, 1):
        cls = "done" if i <= done else ("current" if i == current else "")
        mark = "✓" if i <= done else str(i)
        out.append(f'<span class="step {cls}" data-step="{i}"><span class="n">{mark}</span>{label}</span>')
        if i < len(steps):
            out.append('<span class="bar"></span>')
    out.append("</div>")
    return "".join(out)


def _lang_toggle(lang):
    def a(code):
        cls = "btn langbtn primary" if code == lang else "btn langbtn"
        return f'<a class="{cls}" href="/lang?set={code}">{code.upper()}</a>'
    return f'<div class="row" style="gap:4px">{a("pt")}{a("en")}</div>'


def _modal(lang):
    return f"""
<dialog id="msgbox"><div class="msgbody"><p id="msgtext"></p>
<input type="text" id="msginput" hidden>
<div class="row"><span class="sp"></span>
<button class="btn" id="msgcancel">{i18n.t('modal.cancel', lang)}</button>
<button class="btn primary" id="msgok">{i18n.t('modal.ok', lang)}</button></div></div></dialog>
<div id="toast" class="toast" hidden></div>
"""


_JS_UTIL = """<script>
function notify(msg){const t=document.getElementById('toast');t.textContent=msg;t.hidden=false;
  clearTimeout(t._h);t._h=setTimeout(()=>t.hidden=true,3500);}
function tell(msg){return new Promise(res=>{const d=document.getElementById('msgbox');
  document.getElementById('msgtext').textContent=msg;
  const inp=document.getElementById('msginput');inp.hidden=true;
  const ok=document.getElementById('msgok'),cancel=document.getElementById('msgcancel');
  cancel.hidden=true;
  const done=()=>{d.close();ok.onclick=null;cancel.hidden=false;res();};
  ok.onclick=done;d.showModal();});}
function ask(msg){return new Promise(res=>{const d=document.getElementById('msgbox');
  document.getElementById('msgtext').textContent=msg;
  const inp=document.getElementById('msginput');inp.hidden=false;inp.value='';
  const ok=document.getElementById('msgok'),cancel=document.getElementById('msgcancel');
  cancel.hidden=false;
  const done=v=>{d.close();ok.onclick=cancel.onclick=null;res(v);};
  ok.onclick=()=>done(inp.value);cancel.onclick=()=>done(null);
  d.showModal();inp.focus();});}
function confirmBox(msg){return new Promise(res=>{const d=document.getElementById('msgbox');
  document.getElementById('msgtext').textContent=msg;
  const inp=document.getElementById('msginput');inp.hidden=true;
  const ok=document.getElementById('msgok'),cancel=document.getElementById('msgcancel');
  cancel.hidden=false;
  const done=v=>{d.close();ok.onclick=cancel.onclick=null;cancel.hidden=true;res(v);};
  ok.onclick=()=>done(true);cancel.onclick=()=>done(false);
  d.showModal();});}
</script>
"""


def _inject(lang, group):
    """`const LANG` + dicionário `T` com as strings JS do grupo (prefixo no catálogo)."""
    d = i18n.js_dict(lang, group)
    return ('<script>const LANG="' + lang + '";const T='
            + json.dumps(d, ensure_ascii=False) + ';</script>')


def review_page(lang):
    return _head(i18n.t("rv.title", lang), lang) + f"""
<header><span class="brand">campaign-kit</span><h1 id="title">{i18n.t('rv.title', lang)}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
{_lang_toggle(lang)}
<button class="btn primary" onclick="continuar()">{i18n.t('rv.js.continue', lang)}</button>
<button onclick="load()">{i18n.t('btn.refresh', lang)}</button></header>
<div class="banner">
""" + _stepper(5, 4, lang) + f"""
<div class="stats" id="stats"></div>
<div class="legend"><b>{i18n.t('rv.legend', lang)}</b>
<span class="tag approved"><span class="dot"></span>{i18n.t('rv.legend.approved', lang)}</span>
<span class="tag"><span class="dot"></span>{i18n.t('rv.legend.pending', lang)}</span>
<span class="tag rejected"><span class="dot"></span>{i18n.t('rv.legend.rejected', lang)}</span>
<span class="tag redo"><span class="dot"></span>{i18n.t('rv.legend.redo', lang)}</span>
<span class="tag blocked"><span class="dot"></span>{i18n.t('rv.legend.blocked', lang)}</span></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">5</span>{i18n.t('rv.p5.title', lang)}</h2>
<p class="desc">{i18n.t('rv.p5.desc', lang)}</p>
<div class="filters" id="filters"></div>
<div class="row" style="align-items:center"><span class="meta">{i18n.t('rv.concept', lang)}</span><div class="filters" id="cfilters"></div>
<button class="btn" id="stylebtn" onclick="toggleStyle()" style="display:none">{i18n.t('rv.adjust', lang)}</button></div>
<div id="stylepanel" class="stylepanel" hidden>
<p class="desc" id="styledesc"></p>
<div><div class="stylelabel">{i18n.t('rv.js.style.colors', lang)}</div><div class="stylegrid" id="stylecolors"></div></div>
<div><div class="stylelabel">{i18n.t('rv.js.style.fonts', lang)}</div><div class="stylegrid" id="stylefonts"></div></div>
<datalist id="fontlist"></datalist>
<div><label class="stylelabel" for="stylenote">{i18n.t('rv.stylenote', lang)}</label>
<textarea id="stylenote" class="stylenote" rows="2"></textarea></div>
<div class="row"><button class="btn primary" onclick="applyStyle()">{i18n.t('rv.applystyle', lang)}</button>
<span class="meta" id="stylemsg"></span></div>
</div>
<div class="rgrid" id="grid"></div></div>
<div class="panel"><h2><span class="n">6</span>{i18n.t('rv.p6.title', lang)}</h2>
<p class="desc">{i18n.t('rv.p6.desc', lang)}</p>
<div class="stats" id="deliver-summary"></div>
<div class="row" style="align-items:center"><button class="btn primary" onclick="continuar()">{i18n.t('rv.js.continue', lang)}</button>
<button class="btn" id="opendelivery" onclick="openDelivery()" style="display:none">{i18n.t('rv.js.openfolder', lang)}</button>
<span class="meta">{i18n.t('rv.p6.hint', lang)}</span></div>
<div id="deliver-result"></div></div>
</div>
<dialog id="zoom" onclick="this.close()"><img id="zoomimg" alt=""></dialog>
""" + _modal(lang) + _JS_UTIL + _inject(lang, "rv.js") + """
<script>
let state=null, filter="working", cfilter="all", lastState="", styleOpen=false, styleConcept=null;
const LBL={working:T["lbl.working"],approved:T["lbl.approved"],pending:T["lbl.pending"],rejected:T["lbl.rejected"],redo:T["lbl.redo"],blocked:T["lbl.blocked"]};
const SING={pending:T["sing.pending"],approved:T["sing.approved"],rejected:T["sing.rejected"],redo:T["sing.redo"],blocked:T["sing.blocked"]};
const fmsg=f=>(LANG==="en"&&f.message_en)?f.message_en:f.message;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
async function load(){applyState(await (await fetch("/state")).json());}
function applyState(s){
  state=s; lastState=JSON.stringify(s);
  document.getElementById("title").textContent = state.campaign + " · " + state.brand;
  document.getElementById("meta").textContent = T.meta.replace("{origin}",location.origin);
  const c=st=>state.pieces.filter(p=>p.status===st).length;
  const working=state.pieces.filter(p=>p.status!=="approved").length;
  const delivered=state.pieces.filter(p=>p.delivered).length;
  document.getElementById("stats").innerHTML = fill(T.stats,
    {total:state.pieces.length,approved:c("approved"),pending:c("pending"),blocked:state.blocked_count,delivered});
  const counts={working,approved:c("approved"),pending:c("pending"),rejected:c("rejected"),redo:c("redo"),blocked:c("blocked")};
  document.getElementById("filters").innerHTML = Object.entries(counts)
    .map(([k,v])=>`<button class="${k===filter?'on':''}" onclick="setFilter('${k}')">${LBL[k]} (${v})</button>`).join("");
  const cc={}; for(const p of state.pieces) cc[p.concept]=(cc[p.concept]||0)+1;
  const concepts=(state.concepts&&state.concepts.length?state.concepts:Object.keys(cc));
  document.getElementById("cfilters").innerHTML =
    `<button class="${cfilter==='all'?'on':''}" onclick="setConcept('all')">${fill(T.allconcepts,{n:state.pieces.length})}</button>`+
    concepts.map(k=>`<button class="${cfilter===k?'on':''}" onclick="setConcept('${k}')">${k} (${cc[k]||0})</button>`).join("");
  document.getElementById("stylebtn").style.display = cfilter==="all" ? "none" : "";
  document.getElementById("deliver-summary").innerHTML = fill(T["deliver.summary"],
    {approved:c("approved"),regen:c("rejected")+c("redo")});
  document.getElementById("opendelivery").style.display = delivered>0 ? "" : "none";
  if(delivered>0) setStep(6);
  draw();
}
function setFilter(f){filter=f;draw();}
function setConcept(k){cfilter=k;draw();
  document.getElementById("stylebtn").style.display = k==="all" ? "none" : "";
  if(k==="all") closeStyle();
  else if(styleOpen) openStyle(k);}
function closeStyle(){styleOpen=false;document.getElementById("stylepanel").hidden=true;}
async function toggleStyle(){
  if(styleOpen){closeStyle();return;}
  await openStyle(cfilter);}
async function openStyle(concept){
  const r=await fetch("/style?concept="+encodeURIComponent(concept));
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  styleConcept=concept;styleOpen=true;
  document.getElementById("styledesc").textContent=fill(T["style.desc"],{concept});
  const ov=j.override||{}, pal=Object.assign({},j.palette,ov.palette||{});
  document.getElementById("stylecolors").innerHTML=Object.keys(j.palette).map(role=>
    `<div class="stylefield"><label>${esc(role)}</label><input type="color" data-role="${esc(role)}" value="${esc(pal[role]||"#000000")}"></div>`).join("");
  const typ=Object.assign({},j.type,ov.type||{});
  document.getElementById("stylefonts").innerHTML=Object.keys(j.type).map(role=>{
    const v=typ[role], file=typeof v==="string"?v:((v&&v.file)||"");
    return `<div class="stylefield"><label>${esc(role)}</label><input type="text" data-font="${esc(role)}" list="fontlist" value="${esc(file)}" placeholder="${esc(T["style.fontph"])}"></div>`;}).join("");
  document.getElementById("fontlist").innerHTML=(j.fonts||[]).map(f=>`<option value="${esc(f)}">`).join("");
  document.getElementById("stylenote").value=ov.note||"";
  document.getElementById("stylemsg").textContent="";
  document.getElementById("stylepanel").hidden=false;}
async function applyStyle(){
  const palette={};document.querySelectorAll("#stylecolors input[type=color]").forEach(i=>palette[i.dataset.role]=i.value);
  const type={};document.querySelectorAll("#stylefonts input[type=text]").forEach(i=>{if(i.value.trim())type[i.dataset.font]=i.value.trim();});
  const note=document.getElementById("stylenote").value.trim();
  const n=state.pieces.filter(p=>p.concept===styleConcept).length;
  if(!await confirmBox(fill(T["style.confirm"],{n,concept:styleConcept})))return;
  const r=await fetch("/concept-style",{method:"POST",body:JSON.stringify({concept:styleConcept,palette,type,note})});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  await load();
  notify(fill(T["style.applied"],{n:j.count,concept:styleConcept}));
  closeStyle();}
function setStep(n){document.querySelectorAll(".stepper .step").forEach(el=>{
  const i=+el.dataset.step;el.classList.toggle("done",i<n);el.classList.toggle("current",i===n);
  const d=el.querySelector(".n");if(d)d.textContent=i<n?"✓":String(i);});}
function draw(){
  const items=state.pieces
    .filter(p=>(filter==="working"?p.status!=="approved":p.status===filter)&&(cfilter==="all"||p.concept===cfilter))
    .sort((a,b)=>a.concept.localeCompare(b.concept)||a.format.localeCompare(b.format));
  const g=document.getElementById("grid");
  if(!items.length){g.innerHTML=`<div class="empty">${T.empty}</div>`;return;}
  g.innerHTML=items.map(p=>{
    const finds=(p.findings||[]).filter(f=>f.level!=="info")
      .map(f=>`<li class="${f.level==="fail"?"fail":"warn"}">${f.level==="fail"?T.block:T.warn}${fmsg(f)}</li>`).join("");
    const isVid=p.kind==="video";
    const media=isVid
      ? `<video controls preload="metadata" poster="/img?path=${encodeURIComponent("review/thumbs/"+p.path.replace(/\\.\\w+$/,".video.png"))}"
           src="/img?path=${encodeURIComponent("out/"+p.path)}"></video>`
      : `<img loading="lazy" src="/img?path=${encodeURIComponent("review/thumbs/"+p.path)}"
           onclick="zoom('${encodeURIComponent(p.path)}')" alt="${p.id}">`;
    const badges=(p.delivered?`<span class="tag approved"><span class="dot"></span>${T.delivered}</span>`:"")
      +(p.queued?`<span class="tag"><span class="dot"></span>${T.queued}</span>`:"");
    const note=(p.status==="redo"&&p.note)?`<p class="hint">↻ ${esc(p.note)}</p>`:"";
    return `<div class="card rcard">
      ${media}
      <div class="body">
        <div class="row"><span class="tag ${p.status}"><span class="dot"></span>${SING[p.status]}</span>
          ${isVid?`<span class="tag">${T.video}</span>`:""}${badges}</div>
        <div class="name">${p.concept} · ${p.format}${isVid?" · "+Math.round(p.duration||0)+"s":""}</div>
        ${note}
        <div class="row">
          <button class="btn ok" onclick="decide('${p.id}','approved')">${T.approve}</button>
          <button class="btn no" onclick="decide('${p.id}','rejected')">${T.reject}</button>
          <button class="btn" onclick="regen('${p.id}')">${T.redo}</button></div>
        ${finds?`<ul class="findings">${finds}</ul>`:""}
      </div></div>`;
  }).join("");
}
function zoom(path){document.getElementById("zoomimg").src="/img?path="+path;
  document.getElementById("zoom").showModal();}
async function decide(id,status){
  await fetch("/decision",{method:"POST",body:JSON.stringify({id,status})});
  await load();
  notify(status==="approved"?T.approvetoast:T.rejecttoast);
}
async function regen(id){
  const note=await ask(T.regenask);
  if(note===null||note.trim()==="") return;
  await fetch("/regen",{method:"POST",body:JSON.stringify({id,note})});
  await load();
  notify(T.regentoast);
}
async function continuar(){
  const r=await fetch("/continue",{method:"POST",body:"{}"});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  await load();
  const box=document.getElementById("deliver-result");
  if(j.exported===0&&j.regen===0){box.innerHTML="";notify(T["continue.empty"]);return;}
  box.innerHTML=`<div class="callout ok">${fill(T["continue.done"],{n:j.exported,dir:j.delivery_dir,m:j.regen,req:j.requests_path})}</div>`;
  if(j.ppc&&j.ppc.files&&j.ppc.files.length){
    box.innerHTML+=`<div class="callout">${fill(T["continue.ppc"],{dir:j.ppc.dir,n:j.ppc.files.length,meta:j.ppc.meta,display:j.ppc.google_display,rsa:j.ppc.google_rsa})}</div>`;
  }
  notify(fill(T["continue.toast"],{n:j.exported,m:j.regen}));
  setStep(6);
}
async function openDelivery(){
  const r=await fetch("/open-delivery",{method:"POST",body:"{}"});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  notify(fill(T["openfolder.toast"],{dir:j.path}));
}
async function poll(){
  if(document.querySelector("dialog[open]")) return;
  const s=await (await fetch("/state")).json();
  if(JSON.stringify(s)!==lastState) applyState(s);
}
load();
setInterval(poll,4000);
</script></body></html>"""


def onboard_page(lang):
    return _head(i18n.t("ob.title", lang), lang) + f"""
<header><span class="brand">campaign-kit</span><h1>{i18n.t('ob.title', lang)}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
{_lang_toggle(lang)}
<button onclick="load()">{i18n.t('btn.refresh', lang)}</button></header>
<div class="banner">
""" + _stepper(1, 0, lang) + f"""
<span class="meta">{i18n.t('ob.meta.steps', lang)}</span>
<div class="callout warn" id="ready"></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">1</span>{i18n.t('ob.p1.title', lang)}</h2>
<p class="desc">{i18n.t('ob.p1.desc', lang)}</p>
<span class="meta" id="slotprog"></span>
<div class="grid" id="slots"></div></div>
<div class="panel"><h2><span class="n">2</span>{i18n.t('ob.p2.title', lang)}</h2>
<p class="desc">{i18n.t('ob.p2.desc', lang)}</p>
<div class="dropzone" id="briefdrop">
<label class="btn">{i18n.t('ob.p2.upload', lang)}<input type="file"
  accept=".md,.txt,.rtf,.pdf,.docx" hidden onchange="uploadBrief(this.files)"></label>
<span class="meta">{i18n.t('ob.p2.drop', lang)}</span>
<span class="meta" id="brieffile">{i18n.t('ob.p2.filenote', lang)}</span></div>
<div class="chips" id="sections"></div>
<div class="chips" id="concepts"></div>
<textarea id="brief"></textarea>
<div class="row"><button class="btn primary" onclick="saveBrief()">{i18n.t('ob.p2.save', lang)}</button>
<span class="meta">{i18n.t('ob.p2.legend', lang)}</span></div>
<div class="docsblock">
<p class="desc"><b>{i18n.t('ob.p2.docs.title', lang)}</b> — {i18n.t('ob.p2.docs.desc', lang)}</p>
<div class="dropzone" id="docsdrop">
<label class="btn">{i18n.t('ob.p2.docs.upload', lang)}<input type="file"
  accept="{','.join(onboard.BRIEF_DOC_EXT)}" multiple hidden onchange="uploadDocs(this.files)"></label>
<span class="meta">{i18n.t('ob.p2.docs.drop', lang)}</span>
<span class="meta" id="docscount"></span></div>
<ul class="files" id="docslist"></ul>
</div></div>
<div class="panel"><h2><span class="n">3</span>{i18n.t('ob.p3.title', lang)}</h2>
<p class="desc">{i18n.t('ob.p3.desc', lang)}</p>
<div class="row"><input type="text" id="bid" placeholder="{i18n.t('ob.p3.idph', lang)}">
<button class="btn primary" onclick="derivar()">{i18n.t('ob.p3.run', lang)}</button></div>
<div id="result"></div></div>
<div class="panel"><h2><span class="n">4</span>{i18n.t('ob.p4.title', lang)}</h2>
<p class="desc">{i18n.t('ob.p4.desc', lang)}</p>
<span class="meta">{i18n.t('ob.p4.pipe', lang)}</span>
<p class="desc" style="margin-top:10px">{i18n.t('ob.p4.paste', lang)}</p>
<div class="row"><input type="text" id="agentline" readonly>
<button class="btn primary" onclick="copyAgent()">{i18n.t('ob.p4.copy', lang)}</button></div></div>
</div>
""" + _modal(lang) + _JS_UTIL + _inject(lang, "ob.js") + """
<script>
let S=null, INT=null;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=n=>n>1048576?(n/1048576).toFixed(1)+" MB":Math.max(1,Math.round(n/1024))+" KB";
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
async function load(){
  S = await (await fetch("/state")).json();
  document.getElementById("agentline").value = fill(T.agentline,{inbox:S.inbox});
  document.getElementById("meta").textContent = S.inbox;
  const slotsOk=Object.values(S.slots).filter(s=>s.ok).length;
  const secOk=S.briefing.sections.filter(x=>x.filled).length;
  document.getElementById("slotprog").textContent =
    fill(T.slotprog,{n:slotsOk,total:Object.keys(S.slots).length,sec:secOk,sectotal:S.briefing.sections.length});
  const missing=[];
  for(const s of Object.values(S.slots)) if(s.required&&!s.ok) missing.push(s.label);
  for(const t of S.briefing.missing) missing.push(fill(T.missingbrief,{title:t}));
  const r=document.getElementById("ready");
  if(S.ready){r.className="callout ok";r.textContent=T.ready;}
  else{r.className="callout warn";r.textContent=fill(T.missing,{items:missing.join(" · ")});}
  document.getElementById("slots").innerHTML = Object.entries(S.slots).map(([k,s])=>`
    <div class="card slot" data-slot="${k}"><div class="body">
      <div class="row"><b>${s.label}</b><span class="sp"></span>
        <span class="tag ${s.ok?"approved":(s.required?"blocked":"")}"><span class="dot"></span>${s.ok?T.tagok:(s.required?T.tagmissing:T.tagoptional)}</span></div>
      <p class="hint">${s.hint}</p>
      <ul class="files">${s.files.map(f=>`<li><span>${esc(f.name)}</span><span class="row"><span class="meta">${fmt(f.size)}</span>
        <button class="btn docremove" title="${T["docs.remove"]}" onclick="removeSlotFile('${k}','${esc(f.name)}')">✕</button></span></li>`).join("")||`<li><span class="meta">${T.empty}</span></li>`}</ul>
      <div class="row"><label class="btn">${T.add}<input type="file" ${s.multiple?"multiple":""}
        accept="${s.ext.join(",")}" hidden onchange="upload('${k}',this.files)"></label>
      <span class="meta">${T.drag}</span></div>
    </div></div>`).join("");
  document.querySelectorAll(".slot").forEach(c=>{
    c.addEventListener("dragover",e=>{e.preventDefault();c.classList.add("drag");});
    c.addEventListener("dragleave",()=>c.classList.remove("drag"));
    c.addEventListener("drop",e=>{e.preventDefault();c.classList.remove("drag");upload(c.dataset.slot,e.dataTransfer.files);});
  });
  const ta=document.getElementById("brief");
  if(document.activeElement!==ta) ta.value=S.briefing.text;
  document.getElementById("sections").innerHTML = S.briefing.sections
    .map(x=>`<span class="tag ${x.filled?"approved":""}">${x.filled?"✓":"•"} ${esc(x.title)}</span>`).join("");
  const cs=S.briefing.concepts||[];
  document.getElementById("concepts").innerHTML = cs.length
    ? `<span class="meta">${T["concepts.ok"]}</span>`+cs.map(c=>`<span class="tag approved">${esc(c)}</span>`).join("")
    : `<span class="meta">${T["concepts.none"]}</span>`;
  const docs=S.briefing_docs||[];
  document.getElementById("docscount").textContent = docs.length?fill(T["docs.count"],{n:docs.length}):"";
  document.getElementById("docslist").innerHTML = docs.length
    ? docs.map(f=>`<li><span>${esc(f.name)}</span><span class="row"><span class="meta">${fmt(f.size)}</span>
        <button class="btn docremove" title="${T["docs.remove"]}" onclick="removeDoc('${esc(f.name)}')">✕</button></span></li>`).join("")
    : `<li><span class="meta">${T["docs.empty"]}</span></li>`;
}
async function upload(slot,files){
  for(const f of files){
    const r=await fetch(`/upload?slot=${slot}&name=${encodeURIComponent(f.name)}`,{method:"POST",body:f});
    if(!r.ok) await tell((await r.json()).error);
  }
  await load();
}
async function saveBrief(){
  await fetch("/briefing",{method:"POST",body:JSON.stringify({text:document.getElementById("brief").value})});
  await load();
}
async function uploadBrief(files){
  for(const f of files){
    const r=await fetch(`/briefing-file?name=${encodeURIComponent(f.name)}`,{method:"POST",body:f});
    const j=await r.json();
    if(!r.ok){await tell(j.error);continue;}
    const note=document.getElementById("brieffile");
    if(j.kind==="binary"){
      note.textContent=fill(T["brief.binary"],{name:j.name});
      notify(fill(T["brief.binarytoast"],{name:j.name}));
    }else{
      note.textContent=fill(T["brief.text"],{name:f.name});
      notify(T["brief.texttoast"]);
    }
  }
  await load();
}
async function uploadDocs(files){
  let n=0;
  for(const f of files){
    const r=await fetch(`/brief-docs?name=${encodeURIComponent(f.name)}`,{method:"POST",body:f});
    if(!r.ok){await tell((await r.json()).error);continue;}
    n++;
  }
  await load();
  if(n) notify(fill(T["docs.added"],{n}));
}
async function removeDoc(name){
  const r=await fetch(`/brief-docs-delete?name=${encodeURIComponent(name)}`,{method:"POST",body:"{}"});
  if(!r.ok){await tell((await r.json()).error);return;}
  await load();
  notify(fill(T["docs.removed"],{name}));
}
async function removeSlotFile(slot,name){
  const r=await fetch(`/upload-delete?slot=${slot}&name=${encodeURIComponent(name)}`,{method:"POST",body:"{}"});
  if(!r.ok){await tell((await r.json()).error);return;}
  await load();
  notify(fill(T["docs.removed"],{name}));
}
async function copyAgent(){
  await navigator.clipboard.writeText(document.getElementById("agentline").value);
  notify(T.copied);
}
async function derivar(){
  const id=document.getElementById("bid").value.trim();
  if(!id){await tell(T.needid);return;}
  const r=await fetch("/intake?lang="+LANG,{method:"POST",body:JSON.stringify({brand_id:id})});
  if(!r.ok){await tell((await r.json()).error);return;}
  INT=await r.json(); drawResult();
}
function drawResult(){
  const s=INT.summary;
  document.getElementById("result").innerHTML = `
    <div class="row"><span class="meta">${T.palette}</span>
      ${Object.entries(s.palette||{}).map(([k,v])=>`<span class="sw" style="background:${v}" title="${k} ${v}"></span>`).join("")||`<span class="meta">${T.nologo}</span>`}
      <span class="meta">${fill(T.counts,{refs:s.ref_count,photos:s.photos.length,videos:s.videos.length,fonts:s.fonts})}</span></div>
    <div class="row"><span class="meta">${T.conceptsreq}</span>
      ${(s.concepts_requested||[]).map(c=>`<span class="tag approved">${esc(c)}</span>`).join("")||`<span class="meta">${T.noconcepts}</span>`}</div>
    ${INT.gaps.map(g=>`<div class="gap"><b>${esc(g.question)}</b>
      <span class="why">${esc(g.why)}</span>
      <input type="text" id="gap-${g.field}" placeholder="${T.answerph}"></div>`).join("")}
    <div class="row"><button class="btn primary" onclick="saveAnswers()">${T.saveanswers}</button>
      <span class="meta">${T.oneround}</span></div>`;
}
async function saveAnswers(){
  const answers={};
  for(const g of INT.gaps) answers[g.field]=document.getElementById("gap-"+g.field).value;
  await fetch("/answers",{method:"POST",body:JSON.stringify({brand_id:INT.summary.brand,answers})});
  notify(fill(T.saved,{brand:INT.summary.brand}));
}
const bd=document.getElementById("briefdrop");
bd.addEventListener("dragover",e=>{e.preventDefault();bd.classList.add("drag");});
bd.addEventListener("dragleave",()=>bd.classList.remove("drag"));
bd.addEventListener("drop",e=>{e.preventDefault();bd.classList.remove("drag");uploadBrief(e.dataTransfer.files);});
const dd=document.getElementById("docsdrop");
dd.addEventListener("dragover",e=>{e.preventDefault();dd.classList.add("drag");});
dd.addEventListener("dragleave",()=>dd.classList.remove("drag"));
dd.addEventListener("drop",e=>{e.preventDefault();dd.classList.remove("drag");uploadDocs(e.dataTransfer.files);});
load();
</script></body></html>"""


def _open_folder(path):
    """Abre a pasta no gerenciador de arquivos do SO (Finder/Explorer/xdg). Servidor local."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


class Handler(BaseHTTPRequestHandler):
    root = None
    mode = "review"
    brands = None

    def log_message(self, *args):
        pass

    def _cookie_lang(self):
        m = re.search(r"(?:^|;\s*)lang=(pt|en)", self.headers.get("Cookie", ""))
        return m.group(1) if m else None

    def _lang(self):
        q = parse_qs(urlparse(self.path).query).get("lang", [None])[0]
        if q in ("pt", "en"):
            return q
        return self._cookie_lang() or i18n.resolve_lang()

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _safe(self, rel):
        path = os.path.realpath(os.path.join(self.root, rel))
        if not path.startswith(os.path.realpath(self.root) + os.sep):
            return None
        return path if os.path.isfile(path) else None

    def _onboard_post(self, length):
        lang = self._lang()
        url = urlparse(self.path)
        if url.path == "/upload":
            q = parse_qs(url.query)
            slot = q.get("slot", [""])[0]
            name = os.path.basename(q.get("name", [""])[0])
            spec = next((s for s in onboard.SLOTS if s["key"] == slot), None)
            if not spec or not name or name.startswith("."):
                return self._send(400, {"error": i18n.t("ob.err.slot", lang)})
            if not name.lower().endswith(spec["ext"]):
                return self._send(400, {"error": i18n.t(
                    "ob.err.ext", lang,
                    label=i18n.t(f"slot.{slot}.label", lang), exts=", ".join(spec["ext"]))})
            if length > 300 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.big", lang)})
            data = self.rfile.read(length)
            d = os.path.join(self.root, spec["dir"])
            os.makedirs(d, exist_ok=True)
            if not spec["multiple"]:
                for f in os.listdir(d):
                    os.remove(os.path.join(d, f))
            with open(os.path.join(d, name), "wb") as f:
                f.write(data)
            return self._send(200, {"ok": True})
        if url.path == "/upload-delete":
            q = parse_qs(url.query)
            slot = q.get("slot", [""])[0]
            name = os.path.basename(q.get("name", [""])[0])
            spec = next((s for s in onboard.SLOTS if s["key"] == slot), None)
            self.rfile.read(length)
            if not spec or not name or name.startswith("."):
                return self._send(400, {"error": i18n.t("ob.err.slot", lang)})
            p = os.path.join(self.root, spec["dir"], name)
            if os.path.isfile(p):
                os.remove(p)
            return self._send(200, {"ok": True})
        if url.path == "/briefing-file":
            q = parse_qs(url.query)
            name = os.path.basename(q.get("name", [""])[0])
            if not name or name.startswith(".") or not name.lower().endswith(intake.BRIEF_EXT):
                return self._send(400, {"error": i18n.t("ob.err.briefext", lang)})
            if length > 20 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.briefbig", lang)})
            data = self.rfile.read(length)
            if name.lower().endswith((".md", ".txt", ".rtf")):
                text = data.decode("utf-8", errors="replace")
                with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                    f.write(text)
                return self._send(200, {"ok": True, "kind": "text", "text": text})
            with open(os.path.join(self.root, name), "wb") as f:
                f.write(data)
            return self._send(200, {"ok": True, "kind": "binary", "name": name})
        if url.path == "/brief-docs":
            q = parse_qs(url.query)
            name = os.path.basename(q.get("name", [""])[0])
            if not name or name.startswith(".") or not name.lower().endswith(onboard.BRIEF_DOC_EXT):
                return self._send(400, {"error": i18n.t(
                    "ob.err.docext", lang, exts=", ".join(onboard.BRIEF_DOC_EXT))})
            if length > 20 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.docbig", lang)})
            data = self.rfile.read(length)
            d = os.path.join(self.root, onboard.BRIEF_DOCS_DIR)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, name), "wb") as f:
                f.write(data)
            return self._send(200, {"ok": True, "name": name})
        if url.path == "/brief-docs-delete":
            q = parse_qs(url.query)
            name = os.path.basename(q.get("name", [""])[0])
            self.rfile.read(length)
            if not name or name.startswith("."):
                return self._send(400, {"error": i18n.t("ob.err.slot", lang)})
            p = os.path.join(self.root, onboard.BRIEF_DOCS_DIR, name)
            if os.path.isfile(p):
                os.remove(p)
            return self._send(200, {"ok": True})
        payload = json.loads(self.rfile.read(length) or b"{}")
        if url.path == "/briefing":
            with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                f.write(payload.get("text", ""))
            return self._send(200, {"ok": True})
        if url.path == "/intake":
            bid = payload.get("brand_id", "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", bid):
                return self._send(400, {"error": i18n.t("ob.err.brandid", lang)})
            summary, gaps = intake.run(self.root, bid, self.brands, lang)
            return self._send(200, {"summary": summary, "gaps": gaps})
        if url.path == "/answers":
            bid = os.path.basename(payload.get("brand_id", ""))
            path = os.path.join(self.brands, bid, "answers.json")
            if not os.path.isdir(os.path.dirname(path)):
                return self._send(400, {"error": i18n.t("ob.err.intakefirst", lang)})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload.get("answers", {}), f, indent=2, ensure_ascii=False)
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/lang":
            setl = parse_qs(url.query).get("set", ["pt"])[0]
            if setl not in ("pt", "en"):
                setl = "pt"
            self.send_response(302)
            self.send_header("Set-Cookie", f"lang={setl}; Path=/; Max-Age=31536000; SameSite=Lax")
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        lang = self._lang()
        if url.path == "/":
            page = onboard_page(lang) if self.mode == "onboard" else review_page(lang)
            self._send(200, page.encode(), "text/html; charset=utf-8")
        elif url.path == "/state":
            if self.mode == "onboard":
                return self._send(200, onboard.status(self.root, lang))
            with open(os.path.join(self.root, "state.json"), encoding="utf-8") as f:
                self._send(200, json.load(f))
        elif url.path == "/img":
            rel = parse_qs(url.query).get("path", [""])[0]
            path = self._safe(rel)
            if not path:
                return self._send(404, {"error": "not found"})
            ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"
                     }.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
            with open(path, "rb") as f:
                self._send(200, f.read(), ctype)
        elif url.path == "/style":
            from .brand import rgb_hex, font_dirs
            import glob as _glob
            concept = parse_qs(url.query).get("concept", [""])[0]
            camp = campaign.load_campaign(self.root)
            brand = campaign.brand_for(camp)
            palette = {r: rgb_hex(brand.palette[r])
                       for r in ("primary", "accent", "ink", "paper", "dark") if r in brand.palette}
            type_cfg = {}
            for r in ("display", "text", "accent"):
                e = brand.fonts.cfg.get(r)
                type_cfg[r] = e if isinstance(e, str) else (e or {}).get("file", "")
            dirs = font_dirs([brand.assets_dir, os.path.join(brand.root, "fontes")])
            fonts = sorted({os.path.basename(p) for d in dirs
                            for p in _glob.glob(os.path.join(d, "*"))
                            if p.lower().endswith((".ttf", ".otf", ".ttc"))})
            self._send(200, {"concept": concept, "palette": palette, "type": type_cfg,
                             "fonts": fonts, "override": campaign.load_style(self.root, concept)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if self.mode == "onboard":
            return self._onboard_post(length)
        payload = json.loads(self.rfile.read(length) or b"{}")
        state_path = os.path.join(self.root, "state.json")
        if self.path in ("/decision", "/regen"):
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            redo = self.path == "/regen"
            for p in state["pieces"]:
                if p["id"] == payload.get("id"):
                    p["status"] = "redo" if redo else payload.get("status", "pending")
                    if redo:
                        p["note"] = payload.get("note", "")
                    else:
                        p.pop("note", None)
                    if p["status"] != "approved":
                        p.pop("delivered", None)
                        p.pop("delivery_path", None)
                    p.pop("queued", None)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            self._send(200, {"ok": True})
        elif self.path == "/concept-style":
            lang = self._lang()
            concept = payload.get("concept", "")
            camp = campaign.load_campaign(self.root)
            known = set(campaign.available_concepts()) | set(camp.get("concepts") or [])
            if not re.fullmatch(r"[A-Za-z0-9_-]+", concept) or concept not in known:
                return self._send(400, {"error": i18n.t("rv.err.concept", lang)})
            pal = {}
            for r, v in (payload.get("palette") or {}).items():
                if r in ("primary", "accent", "ink", "paper", "dark") and \
                        isinstance(v, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", v):
                    pal[r] = v if v.startswith("#") else "#" + v
            typ = {}
            for r, v in (payload.get("type") or {}).items():
                if r in ("display", "text", "accent") and isinstance(v, str) and v.strip():
                    typ[r] = v.strip()
            note = (payload.get("note") or "").strip()
            style = {}
            if pal:
                style["palette"] = pal
            if typ:
                style["type"] = typ
            if note:
                style["note"] = note
            sp = campaign.style_path(self.root, concept)
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, "w", encoding="utf-8") as f:
                yaml.safe_dump(style, f, allow_unicode=True, sort_keys=False)
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            rnote = note or i18n.t("rv.restyle.defaultnote", lang)
            count = 0
            for p in state["pieces"]:
                if p["concept"] == concept:
                    p["status"] = "redo"
                    p["note"] = rnote
                    p["restyle"] = True
                    p.pop("delivered", None)
                    p.pop("delivery_path", None)
                    p.pop("queued", None)
                    count += 1
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            self._send(200, {"ok": True, "concept": concept, "count": count})
        elif self.path == "/continue":
            if not os.path.isfile(state_path):
                return self._send(400, {"error": i18n.t("rv.err.nostate", self._lang())})
            self._send(200, campaign.deliver(self.root, lang=self._lang()))
        elif self.path == "/open-delivery":
            dest = campaign.delivery_dir(self.root)
            if not os.path.isdir(dest):
                return self._send(400, {"error": i18n.t("rv.js.openfolder.empty", self._lang())})
            _open_folder(dest)
            self._send(200, {"ok": True, "path": dest})
        else:
            self._send(404, {"error": "not found"})


def _serve(root, port, open_browser=True, shortcut_name="ABRIR-REVISAO.html", lang="pt"):
    """Sobe a UI em 127.0.0.1, grava atalho clicável na pasta e abre o navegador.

    Porta ocupada → tenta as próximas: cada campanha ganha a sua, sem conflito.
    """
    server = None
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError(f"nenhuma porta livre em {port}..{port + 19}")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shortcut = os.path.join(root, shortcut_name)
    with open(shortcut, "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="' + lang + '"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0;url={url}">'
                '<title>campaign-kit</title></head>'
                '<body style="font-family:system-ui,sans-serif;padding:40px">'
                f'<p>{i18n.t("cli.shortcut.opening", lang, url=url)} <a href="{url}">{url}</a></p>'
                f'<p>{i18n.t("cli.shortcut.manual", lang)}</p>'
                '</body></html>\n')
    print(f"\n  ➜  {url}\n  ({i18n.t('cli.serve.shortcut', lang, name=shortcut_name)})\n", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server, url


def serve(campaign_root, port=8765, open_browser=True, lang=None):
    lang = lang or i18n.resolve_lang()
    Handler.mode = "review"
    Handler.root = os.path.abspath(campaign_root)
    return _serve(os.path.abspath(campaign_root), port, open_browser, lang=lang)


def serve_onboard(inbox, brands_dir, port=8766, open_browser=True, lang=None):
    lang = lang or i18n.resolve_lang()
    inbox = os.path.abspath(os.path.expanduser(inbox))
    onboard.scaffold(inbox)
    Handler.mode = "onboard"
    Handler.root = inbox
    Handler.brands = os.path.abspath(brands_dir)
    return _serve(inbox, port, open_browser, shortcut_name="ABRIR-ONBOARDING.html", lang=lang)
