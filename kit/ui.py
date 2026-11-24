"""Local UI (onboarding + review): stdlib http.server + clear pages. Zero npm, zero build.

Runs on 127.0.0.1. Light theme with numbered steps and a status legend so people can
orient themselves; onboarding prepares the folder, review lets you approve/reject/redo
by click and queues regeneration requests that the agent executes. Dies when you close it.

English-only: pages are assembled server-side plus a T dictionary injected for the
dynamic JS; data (slots, gaps, compliance findings) is English too.
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

from . import assets, campaign, i18n, intake, onboard, rules

# ThreadingHTTPServer serves concurrently: without this, two fast review clicks
# read-modify-write state.json in parallel and the second clobbers the first.
_STATE_LOCK = threading.Lock()

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
.modeswitch{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}
.modeswitch button{border:0;border-radius:0;min-height:32px;padding:4px 12px;font-size:13px;background:var(--surface)}
.modeswitch button:hover:not(:disabled):not(.on){background:#f2f4f7}
.modeswitch button+button{border-left:1px solid var(--line)}
.modeswitch button.on{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.modeswitch button:disabled{color:var(--mut);cursor:not-allowed}
button,.btn{min-height:36px;padding:8px 14px;border-radius:9px;border:1px solid var(--line);
 background:var(--surface);color:var(--ink);font-size:14px;cursor:pointer;
 display:inline-flex;align-items:center;gap:6px}
button:hover,.btn:hover{background:#f2f4f7}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-dk)}
.btn.ok{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.btn.no{background:var(--bad-bg);border-color:var(--bad-line);color:var(--bad)}
a.btn{text-decoration:none}
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
.tag.new{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.queuelist{margin:8px 0 0;padding-left:18px}
.queuelist li{margin:3px 0}
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
.media{position:relative}
.card.busy{border-color:var(--accent);box-shadow:0 0 0 3px rgba(11,107,203,.12)}
.media .processing{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:8px;padding:12px;text-align:center;color:#fff;background:rgba(20,25,31,.66)}
.media .processing b{font-size:13px}
.media .processing small{font-size:11.5px;opacity:.85}
.spin{width:26px;height:26px;border-radius:50%;border:3px solid rgba(255,255,255,.35);
  border-top-color:#fff;animation:spin .9s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.findings{margin:0;padding:0;list-style:none;font-size:12.5px;display:grid;gap:4px}
.findings li.fail{color:var(--bad)}
.findings li.warn{color:var(--warn)}
dialog{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:14px;max-width:92vw;padding:8px}
dialog img{max-width:88vw;max-height:82vh;display:block;border-radius:8px}
dialog#rulealarm{max-width:min(720px,94vw);padding:0;border:2px solid var(--accent);
 box-shadow:0 18px 60px rgba(12,34,68,.3)}
.rulebody{padding:18px 20px 16px}
.rulebody h3{margin:0;font-size:17px}
.rulemeta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:12px 0 4px}
.rulecmp{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0}
.rulecmp pre{margin:4px 0 0;padding:10px;border-radius:10px;background:var(--bg);
 border:1px solid var(--line);font-size:12.5px;white-space:pre-wrap;word-break:break-word;
 max-height:190px;overflow:auto}
.rulecmp .new pre{border-color:var(--accent);background:#eef5ff}
.rulewhy{margin:6px 0 14px;font-size:13.5px}
.rulebadge{cursor:pointer;background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn)}
.rulehist{margin-top:12px;font-size:12px;color:var(--mut);display:grid;gap:3px}
@media (max-width:640px){.rulecmp{grid-template-columns:1fr}}
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
.stylepanel.drag{outline:2px dashed var(--accent);outline-offset:3px}
.stylerefs{display:flex;gap:6px;flex-wrap:wrap}
.stylerefs .chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);
  background:#fff;border-radius:999px;padding:3px 6px 3px 10px;font-size:12px;color:var(--ink)}
.stylerefs .chip button{border:0;background:var(--line);color:var(--ink);border-radius:50%;
  width:16px;height:16px;line-height:14px;cursor:pointer;font-size:11px}
.stylelabel{font-size:12.5px;color:var(--mut);font-weight:600}
dialog .msgbody{display:grid;gap:12px;padding:10px 12px;min-width:320px;max-width:480px}
dialog .msgbody p{margin:0;font-size:14px}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:50;
 background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:10px;
 padding:10px 16px;font-size:14px;box-shadow:0 4px 16px rgba(16,24,32,.15);max-width:90vw}
</style>"""

_STEPS = ["Files", "Briefing", "Brand", "Generate", "Assets", "Review", "Deliver"]


def _head(title):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>campaign-kit · ' + title + '</title>' + _STYLE + '</head><body>')


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


def _modal():
    return f"""
<dialog id="msgbox"><div class="msgbody"><p id="msgtext"></p>
<input type="text" id="msginput" hidden>
<div class="row"><span class="sp"></span>
<button class="btn" id="msgcancel">{i18n.t('modal.cancel')}</button>
<button class="btn primary" id="msgok">{i18n.t('modal.ok')}</button></div></div></dialog>
<div id="toast" class="toast" hidden></div>
"""


def _rule_alarm(group):
    """The blocking alarm: a rule change is the user's call, so it cannot be dismissed.

    `group` is the page's i18n prefix ("rv.js" / "as.js") — the same keys both sides.
    """
    t = lambda k: i18n.t(f"{group}.rule.{k}")
    return f"""
<dialog id="rulealarm"><div class="rulebody">
<h3>{t('title')}</h3>
<p class="desc">{t('desc')}</p>
<div class="rulemeta" id="rulemeta"></div>
<div class="rulecmp"><div><div class="stylelabel">{t('now')}</div><pre id="rulenow"></pre></div>
<div class="new"><div class="stylelabel">{t('proposed')}</div><pre id="rulenew"></pre></div></div>
<div class="rulewhy"><b>{t('why')}:</b> <span id="rulewhy"></span></div>
<div class="row"><span class="sp"></span>
<button class="btn" onclick="decideRule(false)">{t('keep')}</button>
<button class="btn primary" onclick="decideRule(true)">{t('agree')}</button></div>
<div class="rulehist" id="rulehist"></div>
</div></dialog>
"""


_RULE_JS = """<script>
let ruleOpen=null, ruleSeen=0;
const rulePend=()=>((state&&state.rule_proposals)||{}).pending||[];
const ruleVal=v=>v==null||v===""?"—":(typeof v==="string"?v:JSON.stringify(v,null,1));
function syncRules(){
  const pend=rulePend(), hist=((state&&state.rule_proposals)||{}).decided||[];
  const b=document.getElementById("rulebadge");
  b.hidden=!pend.length;
  b.textContent=fill(T["rule.badge"],{n:pend.length});
  if(pend.length>ruleSeen){ruleSeen=pend.length;desktopNotify(T["rule.notify"]);}
  if(!pend.length&&ruleSeen===0) ruleSeen=0;
  const h=document.getElementById("rulehist");
  h.innerHTML=hist.slice(-4).map(p=>fill(T["rule.history"],
    {target:esc(p.target),status:T["rule.status."+p.status]||p.status})).join("");
  const d=document.getElementById("rulealarm");
  if(!pend.length){if(d.open)d.close();ruleOpen=null;return 0;}
  const cur=pend.find(p=>p.id===ruleOpen)||pend[0];
  if(ruleOpen!==cur.id||!d.open){
    ruleOpen=cur.id;
    document.getElementById("rulemeta").innerHTML=
      `<span class="tag">${esc(T["rule.scope."+cur.scope]||cur.scope)}</span>`+
      `<span class="tag">${esc(cur.target)}</span>`+
      (cur.affected!=null&&cur.total!=null
        ?`<span class="hint">${fill(T["rule.affected"],{affected:cur.affected,total:cur.total})}</span>`:"")+
      (pend.length>1?`<span class="hint">${esc(cur.id)} · ${pend.length}</span>`:"");
    document.getElementById("rulenow").textContent=ruleVal(cur.current);
    document.getElementById("rulenew").textContent=ruleVal(cur.value);
    document.getElementById("rulewhy").textContent=cur.reason||"—";
    if(!d.open) d.showModal();
  }
  return pend.length;
}
async function decideRule(agree){
  const id=ruleOpen; if(!id) return;
  const d=document.getElementById("rulealarm");
  d.close(); ruleOpen=null; ruleSeen=Math.max(0,ruleSeen-1);
  const {ok,j}=await pj("/rule-decision",{method:"POST",body:JSON.stringify({id:id,agree:agree})});
  if(!ok){await tell(j.error||T.failed);await load();return;}
  notify(fill(T[agree?"rule.agreed":"rule.kept"],{target:j.target||id}));
  await load();
}
function desktopNotify(msg){
  if(!("Notification" in window)) return;
  if(Notification.permission==="granted"){try{new Notification("campaign-kit",{body:msg});}catch(e){}}
  else if(Notification.permission!=="denied"){try{Notification.requestPermission();}catch(e){}}
}
</script>
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
async function pj(url,opts){try{const r=await fetch(url,opts);let j={};
  try{j=await r.json();}catch(e){}
  return {ok:r.ok,j:j};}catch(e){return {ok:false,j:{}};}}
</script>
"""


def _inject(group):
    """`T` dictionary with the group's JS strings (prefix in the catalog)."""
    d = i18n.js_dict(group)
    return '<script>const T=' + json.dumps(d, ensure_ascii=False) + ';</script>'


def _mode_switch(kit):
    """Visual | Copy control in the header. The other side is discovered at runtime (/ping),
    so the button is only live when that server is actually running."""
    other = "copy" if kit == "visual" else "visual"
    return (f'<span class="modeswitch" title="{i18n.t("mode.title", kit=i18n.t("mode." + kit))}">'
            f'<button type="button" class="on">{i18n.t("mode." + kit)}</button>'
            f'<button type="button" id="mode-other" disabled onclick="switchMode()">'
            f'{i18n.t("mode." + other)}</button></span>'
            f'<span class="meta" id="modehint"></span>')


# The kits are separate servers on separate folders: probe the local port range for the other
# wizard instead of guessing a port, and save the form before navigating so nothing typed is lost.
def _mode_js(kit):
    return """
const KIT="%s";
let OTHER=null;
async function findOther(){
  const want=KIT==="visual"?"copy":"visual", probes=[];
  for(let p=8760;p<=8790;p++) probes.push(fetch("http://127.0.0.1:"+p+"/ping")
    .then(r=>r.json())
    .then(j=>(j&&j.kit===want&&j.mode==="onboard"?{url:"http://127.0.0.1:"+p,root:j.root}:null))
    .catch(()=>null));
  return (await Promise.all(probes)).find(Boolean)||null;
}
async function initModeSwitch(){
  const b=document.getElementById("mode-other"), h=document.getElementById("modehint");
  if(!b) return;
  OTHER=await findOther();
  if(OTHER){b.disabled=false;b.title=OTHER.root;h.textContent=T["mode.hint"];}
  else h.textContent=T["mode.off"];
}
async function switchMode(){
  if(!OTHER) return;
  if(typeof saveAll==="function") await saveAll();
  location.href=OTHER.url;
}
initModeSwitch();
""" % kit


def review_page():
    return _head(i18n.t("rv.title")) + f"""
<header><span class="brand">campaign-kit</span><h1 id="title">{i18n.t('rv.title')}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button class="btn rulebadge" id="rulebadge" hidden onclick="ruleOpen=null;syncRules()"></button>
<button class="btn primary contbtn" onclick="continueBatch()">{i18n.t('rv.js.continue')}</button>
<button onclick="load()">{i18n.t('btn.refresh')}</button></header>
<div class="banner">
""" + _stepper(6, 5) + f"""
<div class="stats" id="stats"></div>
<div class="legend"><b>{i18n.t('rv.legend')}</b>
<span class="tag approved"><span class="dot"></span>{i18n.t('rv.legend.approved')}</span>
<span class="tag"><span class="dot"></span>{i18n.t('rv.legend.pending')}</span>
<span class="tag rejected"><span class="dot"></span>{i18n.t('rv.legend.rejected')}</span>
<span class="tag redo"><span class="dot"></span>{i18n.t('rv.legend.redo')}</span>
<span class="tag blocked"><span class="dot"></span>{i18n.t('rv.legend.blocked')}</span></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">6</span>{i18n.t('rv.p6.title')}</h2>
<p class="desc">{i18n.t('rv.p6.desc')}</p>
<div class="callout warn" id="queue" style="display:none"></div>
<div class="callout" id="handoff" style="display:none"></div>
<div class="filters" id="filters"></div>
<div class="row" style="align-items:center"><span class="meta">{i18n.t('rv.concept')}</span><div class="filters" id="cfilters"></div>
<button class="btn" id="stylebtn" onclick="toggleStyle()" style="display:none">{i18n.t('rv.adjust')}</button></div>
<div id="stylepanel" class="stylepanel" hidden>
<p class="desc" id="styledesc"></p>
<div><div class="stylelabel">{i18n.t('rv.js.style.colors')}</div><div class="stylegrid" id="stylecolors"></div></div>
<div><div class="stylelabel">{i18n.t('rv.js.style.fonts')}</div><div class="stylegrid" id="stylefonts"></div></div>
<datalist id="fontlist"></datalist>
<div><label class="stylelabel" for="stylenote">{i18n.t('rv.stylenote')}</label>
<textarea id="stylenote" class="stylenote" rows="2"></textarea></div>
<div class="row"><button class="btn" onclick="pickRefs()">{i18n.t('rv.js.style.attach')}</button>
<input type="file" id="reffile" multiple hidden accept=".png,.jpg,.jpeg,.webp,.gif,.pdf">
<span class="meta">{i18n.t('rv.js.style.drophint')}</span></div>
<div class="stylerefs" id="stylerefs"></div>
<div class="row"><button class="btn primary" onclick="applyStyle()">{i18n.t('rv.applystyle')}</button>
<span class="meta" id="stylemsg"></span></div>
</div>
<div class="rgrid" id="grid"></div></div>
<div class="panel"><h2><span class="n">7</span>{i18n.t('rv.p7.title')}</h2>
<p class="desc">{i18n.t('rv.p7.desc')}</p>
<div class="stats" id="deliver-summary"></div>
<div class="row" style="align-items:center"><button class="btn primary contbtn" onclick="continueBatch()">{i18n.t('rv.js.continue')}</button>
<button class="btn" id="opendelivery" onclick="openDelivery()" style="display:none">{i18n.t('rv.js.openfolder')}</button>
<span class="meta">{i18n.t('rv.p7.hint')}</span></div>
<div class="callout warn" id="lockhint" style="display:none"></div>
<div id="deliver-result"></div></div>
</div>
<dialog id="zoom" onclick="this.close()"><img id="zoomimg" alt=""></dialog>
""" + _modal() + _rule_alarm("rv.js") + _JS_UTIL + _inject("rv.js") + _RULE_JS + """
<script>
let state=null, filter="working", cfilter="all", lastState="", styleOpen=false, styleConcept=null, seenBefore=null;
let busyAt={}, timer=null, pollMs=0;
const isBusy=p=>p.status==="rejected"||p.status==="redo";
const LBL={all:T["lbl.all"],working:T["lbl.working"],approved:T["lbl.approved"],pending:T["lbl.pending"],rejected:T["lbl.rejected"],redo:T["lbl.redo"],blocked:T["lbl.blocked"]};
const SING={pending:T["sing.pending"],approved:T["sing.approved"],rejected:T["sing.rejected"],redo:T["sing.redo"],blocked:T["sing.blocked"]};
const fmsg=f=>f.message;
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
  const counts={all:state.pieces.length,working,approved:c("approved"),pending:c("pending"),rejected:c("rejected"),redo:c("redo"),blocked:c("blocked")};
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
  if(delivered>0) setStep(7);
  if(seenBefore===null&&state.campaign){
    const k="ck.lastseen."+state.campaign;
    seenBefore=localStorage.getItem(k)||new Date().toISOString();
    localStorage.setItem(k,seenBefore);
  }
  const q=state.pieces.filter(isBusy);
  const now={}; for(const p of q) now[p.id]=p.updated_at||"";
  const arrived=Object.keys(busyAt).filter(id=>!(id in now)&&
    state.pieces.some(p=>p.id===id&&(p.updated_at||"")!==busyAt[id]));
  busyAt=now;
  if(arrived.length) notify(fill(T["proc.arrived"],{n:arrived.length}));
  const qel=document.getElementById("queue");
  if(q.length){
    qel.style.display="";
    qel.innerHTML=`<b>${fill(T["queue.title"],{n:q.length})}</b> <span class="hint">${T["queue.hint"]}</span>`+
      `<ul class="queuelist">`+q.map(p=>{
        const what=p.status==="redo"?`↻ ${esc(p.note||"")}`:`✕ ${T["queue.recreate"]}`;
        const when=p.decided_at?` · ${new Date(p.decided_at).toLocaleString()}`:"";
        const st=p.queued?T.queued:T["queue.waiting"];
        return `<li><b>${esc(p.id)}</b> — ${esc(p.concept)} · ${esc(p.format)} — ${what} <span class="hint">[${st}${when}]</span></li>`;
      }).join("")+`</ul>`;
  } else qel.style.display="none";
  const inprog=q.length, rulewait=syncRules();
  document.querySelectorAll(".contbtn").forEach(b=>b.disabled=inprog>0||rulewait>0);
  const lh=document.getElementById("lockhint");
  if(rulewait>0){lh.style.display="";lh.textContent=fill(T["rule.locked"],{n:rulewait});}
  else if(inprog>0){lh.style.display="";lh.textContent=fill(T["continue.locked"],{n:inprog});}
  else lh.style.display="none";
  const ho=document.getElementById("handoff");
  if(inprog>0&&state.root){
    ho.style.display="";
    const line=fill(T["handoff.line"],{req:state.root+"/requests.json",root:state.root,
      ids:q.map(p=>p.id).join(" ")});
    ho.innerHTML=`<b>${fill(T["handoff.title"],{n:inprog})}</b> <span class="hint">${T["handoff.hint"]}</span>`+
      `<div class="row" style="align-items:center;margin-top:8px">`+
      `<input type="text" id="handoffline" readonly style="flex:1" value="${esc(line)}">`+
      `<button class="btn" onclick="copyHandoff()">${T["handoff.copy"]}</button></div>`;
  } else ho.style.display="none";
  schedule();
  draw();
}
async function copyHandoff(){
  await navigator.clipboard.writeText(document.getElementById("handoffline").value);
  notify(T["handoff.copied"]);
}
function setFilter(f){filter=f;applyState(state);}
function setConcept(k){cfilter=k;applyState(state);
  if(k==="all") closeStyle();
  else if(styleOpen) openStyle(k);}
function closeStyle(){styleOpen=false;document.getElementById("stylepanel").hidden=true;}
async function toggleStyle(){
  if(styleOpen){closeStyle();return;}
  await openStyle(cfilter);}
async function openStyle(concept){
  const r=await fetch("/style?concept="+encodeURIComponent(concept));
  const j=await r.json();
  if(!r.ok){await tell(j.error||"error");return;}
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
  drawRefs(ov.refs||[]);
  document.getElementById("stylemsg").textContent="";
  document.getElementById("stylepanel").hidden=false;}
async function applyStyle(){
  const palette={};document.querySelectorAll("#stylecolors input[type=color]").forEach(i=>palette[i.dataset.role]=i.value);
  const type={};document.querySelectorAll("#stylefonts input[type=text]").forEach(i=>{if(i.value.trim())type[i.dataset.font]=i.value.trim();});
  const note=document.getElementById("stylenote").value.trim();
  const n=state.pieces.filter(p=>p.concept===styleConcept).length;
  if(!await confirmBox(fill(T["style.confirm"],{n,concept:styleConcept})))return;
  const {ok,j}=await pj("/concept-style",{method:"POST",body:JSON.stringify({concept:styleConcept,palette,type,note})});
  if(!ok){await tell(j.error||T.failed);return;}
  await load();
  notify(fill(T["style.applied"],{n:j.count,concept:styleConcept}));
  closeStyle();}
function drawRefs(refs){document.getElementById("stylerefs").innerHTML=(refs||[]).map(n=>
  `<span class="chip">${esc(n)}<button title="${esc(T["style.refdel"])}" `+
  `onclick="delRef('${esc(n)}')">×</button></span>`).join("");}
function pickRefs(){document.getElementById("reffile").click();}
async function uploadRefs(files){
  for(const f of files){
    const {ok,j}=await pj("/style-ref?concept="+encodeURIComponent(styleConcept)+
      "&name="+encodeURIComponent(f.name),{method:"POST",body:f});
    if(!ok){await tell(j.error||T.failed);continue;}
    drawRefs(j.refs);
  }}
async function delRef(name){
  const {ok,j}=await pj("/style-ref-delete?concept="+encodeURIComponent(styleConcept)+
    "&name="+encodeURIComponent(name));
  if(!ok){await tell(j.error||T.failed);return;}
  drawRefs(j.refs);}
function setStep(n){document.querySelectorAll(".stepper .step").forEach(el=>{
  const i=+el.dataset.step;el.classList.toggle("done",i<n);el.classList.toggle("current",i===n);
  const d=el.querySelector(".n");if(d)d.textContent=i<n?"✓":String(i);});}
function draw(){
  const items=state.pieces
    .filter(p=>(filter==="all"||(filter==="working"?p.status!=="approved":p.status===filter))&&(cfilter==="all"||p.concept===cfilter))
    .sort((a,b)=>a.concept.localeCompare(b.concept)||a.format.localeCompare(b.format));
  const g=document.getElementById("grid");
  if(!items.length){g.innerHTML=`<div class="empty">${T.empty}</div>`;return;}
  g.innerHTML=items.map(p=>{
    const finds=(p.findings||[]).filter(f=>f.level!=="info")
      .map(f=>`<li class="${f.level==="fail"?"fail":"warn"}">${f.level==="fail"?T.block:T.warn}${fmsg(f)}</li>`).join("");
    const isVid=p.kind==="video";
    const v=encodeURIComponent(p.updated_at||"");
    const src=rel=>"/img?path="+encodeURIComponent(rel)+(v?"&v="+v:"");
    const media=isVid
      ? `<video controls preload="metadata" poster="${src("review/thumbs/"+p.path.replace(/\\.\\w+$/,".video.png"))}"
           src="${src("out/"+p.path)}"></video>`
      : `<img loading="lazy" src="${src("review/thumbs/"+p.path)}"
           onclick="zoom('${src("out/"+p.path)}')" alt="${p.id}">`;
    const busy=isBusy(p);
    const since=p.decided_at?` · ${new Date(p.decided_at).toLocaleString()}`:"";
    const wrap=`<div class="media">${media}`+(busy
      ? `<div class="processing"><span class="spin"></span><b>${T["proc.label"]}</b>`+
        `<small>${p.queued?T.queued:T["queue.waiting"]}${since}</small></div>`
      : "")+`</div>`;
    const badges=(p.delivered?`<span class="tag approved"><span class="dot"></span>${T.delivered}</span>`:"")
      +(p.queued?`<span class="tag"><span class="dot"></span>${T.queued}</span>`:"")
      +(seenBefore&&p.updated_at&&p.updated_at>seenBefore&&p.status==="pending"
        ?`<span class="tag new"><span class="dot"></span>${T.newbadge}</span>`:"");
    const note=(p.status==="redo"&&p.note)?`<p class="hint">↻ ${esc(p.note)}</p>`:"";
    return `<div class="card rcard${busy?" busy":""}">
      ${wrap}
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
function zoom(u){const i=document.getElementById("zoomimg");
  i.onerror=()=>{document.getElementById("zoom").close();notify(T.zoomfail);};
  i.src=u;document.getElementById("zoom").showModal();}
async function decide(id,status){
  const {ok}=await pj("/decision",{method:"POST",body:JSON.stringify({id,status})});
  if(!ok){await tell(T.failed);return;}
  await load();
  notify(status==="approved"?T.approvetoast:T.rejecttoast);
}
async function regen(id){
  const note=await ask(T.regenask);
  if(note===null||note.trim()==="") return;
  const {ok}=await pj("/regen",{method:"POST",body:JSON.stringify({id,note})});
  if(!ok){await tell(T.failed);return;}
  await load();
  notify(T.regentoast);
}
async function continueBatch(){
  const {ok,j}=await pj("/continue",{method:"POST",body:"{}"});
  if(!ok){await tell(j.error||T.failed);return;}
  await load();
  const box=document.getElementById("deliver-result");
  if(j.locked>0){box.innerHTML="";notify(fill(T["continue.locked"],{n:j.locked}));return;}
  if(j.exported===0&&j.regen===0){box.innerHTML="";notify(T["continue.empty"]);return;}
  const queued=j.regen>0?fill(T["continue.queued"],{m:j.regen,req:j.requests_path}):"";
  box.innerHTML=`<div class="callout ok">${fill(T["continue.done"],{n:j.exported,dir:j.delivery_dir,queued})}</div>`;
  if(j.ppc&&j.ppc.files&&j.ppc.files.length){
    const platforms=[[j.ppc.meta,T["ppc.meta"]],[j.ppc.google_display,T["ppc.display"]],
                     [j.ppc.google_rsa,T["ppc.rsa"]]].filter(p=>p[0]>0).map(p=>`${p[0]} ${p[1]}`).join(" · ");
    box.innerHTML+=`<div class="callout">${fill(T["continue.ppc"],{dir:j.ppc.dir,n:j.ppc.files.length,platforms})}</div>`;
    const w=j.ppc.warnings||[];
    if(w.length){
      const list=w.slice(0,6).map(x=>`${esc(x.id)} ${esc(x.field)} ${x.chars}&gt;${x.limit}`).join(", ")
        +(w.length>6?` (+${w.length-6})`:"");
      box.innerHTML+=`<div class="callout warn">${fill(T["continue.trunc"],{n:w.length,list})}</div>`;
    }
  }
  notify(fill(T["continue.toast"],{n:j.exported,
    queued:j.regen>0?fill(T["continue.toastqueued"],{m:j.regen}):""}));
  setStep(7);
}
async function openDelivery(){
  const {ok,j}=await pj("/open-delivery",{method:"POST",body:"{}"});
  if(!ok){await tell(j.error||T.failed);return;}
  notify(fill(T["openfolder.toast"],{dir:j.path}));
}
async function poll(){
  if(document.querySelector("dialog[open]")) return;
  let s;
  try{s=await (await fetch("/state")).json();}catch(e){return;}
  if(JSON.stringify(s)!==lastState) applyState(s);
}
function schedule(){
  const ms=(state&&state.pieces.filter(isBusy).length)?1500:6000;
  if(ms===pollMs) return;
  pollMs=ms; if(timer) clearInterval(timer); timer=setInterval(poll,ms);
}
document.addEventListener("visibilitychange",()=>{if(!document.hidden)poll();});
window.addEventListener("focus",poll);
document.getElementById("reffile").addEventListener("change",e=>{uploadRefs([...e.target.files]);e.target.value="";});
const sp=document.getElementById("stylepanel");
sp.addEventListener("dragover",e=>{e.preventDefault();sp.classList.add("drag");});
sp.addEventListener("dragleave",()=>sp.classList.remove("drag"));
sp.addEventListener("drop",e=>{e.preventDefault();sp.classList.remove("drag");
  if(e.dataTransfer.files.length)uploadRefs([...e.dataTransfer.files]);});
load();
schedule();
</script></body></html>"""


def assets_page():
    return _head(i18n.t("as.title")) + f"""
<header><span class="brand">campaign-kit</span><h1 id="title">{i18n.t('as.title')}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button class="btn rulebadge" id="rulebadge" hidden onclick="ruleOpen=null;syncRules()"></button>
<button class="btn primary nextbtn" onclick="nextStep()" disabled>{i18n.t('as.js.next')}</button>
<button onclick="load()">{i18n.t('btn.refresh')}</button></header>
<div class="banner">
""" + _stepper(5, 4) + f"""
<div class="stats" id="stats"></div>
<div class="legend"><b>{i18n.t('as.legend')}</b>
<span class="tag approved"><span class="dot"></span>{i18n.t('as.legend.approved')}</span>
<span class="tag"><span class="dot"></span>{i18n.t('as.legend.pending')}</span>
<span class="tag rejected"><span class="dot"></span>{i18n.t('as.legend.rejected')}</span>
<span class="tag redo"><span class="dot"></span>{i18n.t('as.legend.redo')}</span></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">5</span>{i18n.t('as.p5.title')}</h2>
<p class="desc">{i18n.t('as.p5.desc')}</p>
<div class="callout warn" id="queue" style="display:none"></div>
<div class="callout" id="handoff" style="display:none"></div>
<div class="filters" id="filters"></div>
<div class="rgrid" id="grid"></div></div>
<div class="panel"><h2><span class="n">6</span>{i18n.t('as.p6.title')}</h2>
<p class="desc">{i18n.t('as.p6.desc')}</p>
<div class="row" style="align-items:center"><button class="btn primary nextbtn" onclick="nextStep()" disabled>{i18n.t('as.js.next')}</button>
<button class="btn" onclick="openAssets()">{i18n.t('as.openfolder')}</button>
<span class="meta">{i18n.t('as.p6.hint')}</span></div>
<div class="callout warn" id="gate" style="display:none"></div>
<div id="next-result"></div></div>
</div>
<dialog id="zoom" onclick="this.close()"><img id="zoomimg" alt=""></dialog>
""" + _modal() + _rule_alarm("as.js") + _JS_UTIL + _inject("as.js") + _RULE_JS + """
<script>
let state=null, filter="working", lastState="", seenBefore=null;
let busyAt={}, timer=null, pollMs=0;
const isBusy=a=>a.status==="rejected"||a.status==="redo";
const LBL={all:T["lbl.all"],working:T["lbl.working"],approved:T["lbl.approved"],pending:T["lbl.pending"],rejected:T["lbl.rejected"],redo:T["lbl.redo"]};
const SING={pending:T["sing.pending"],approved:T["sing.approved"],rejected:T["sing.rejected"],redo:T["sing.redo"]};
const esc=s=>String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fill=(s,o)=>s.replace(/\\{(\\w+)\\}/g,(m,k)=>(k in o?o[k]:m));
async function load(){applyState(await (await fetch("/state")).json());}
function applyState(s){
  state=s; lastState=JSON.stringify(s);
  document.getElementById("title").textContent = (s.campaign||T.title||"assets") + " · " + (s.brand||"");
  document.getElementById("meta").textContent = fill(T.meta,{origin:location.origin});
  const A=s.assets||[], c=st=>A.filter(a=>a.status===st).length;
  const working=A.filter(a=>a.status!=="approved").length;
  const credits=A.reduce((t,a)=>t+(+a.credits||0),0);
  document.getElementById("stats").innerHTML = fill(T.stats,
    {total:A.length,approved:c("approved"),pending:c("pending"),
     marks:c("rejected")+c("redo"),credits:Math.round(credits*100)/100});
  const counts={all:A.length,working,approved:c("approved"),pending:c("pending"),rejected:c("rejected"),redo:c("redo")};
  document.getElementById("filters").innerHTML = Object.entries(counts)
    .map(([k,v])=>`<button class="${k===filter?'on':''}" onclick="setFilter('${k}')">${LBL[k]} (${v})</button>`).join("");
  if(seenBefore===null&&s.campaign){
    const k="ck.lastseen.assets."+s.campaign;
    seenBefore=localStorage.getItem(k)||new Date().toISOString();
    localStorage.setItem(k,seenBefore);
  }
  const q=(s.batch||[]);
  const qel=document.getElementById("queue");
  if(q.length){
    qel.style.display="";
    qel.innerHTML=`<b>${fill(T["queue.title"],{n:q.length})}</b> <span class="hint">${T["queue.hint"]}</span>`+
      `<ul class="queuelist">`+q.map(b=>{
        const what=b.reason==="redo"?`↻ ${esc(b.note||"")}`:`✕ ${T["queue.regenerate"]}`;
        const when=b.marked_at?` · ${new Date(b.marked_at).toLocaleString()}`:"";
        return `<li><b>${esc(b.file||b.id)}</b> — ${esc(b.prompt||"").slice(0,90)} — ${what} <span class="hint">[${T["queue.waiting"]}${when}]</span></li>`;
      }).join("")+`</ul>`;
  } else qel.style.display="none";
  const ho=document.getElementById("handoff");
  if(q.length&&s.root){
    ho.style.display="";
    const line=fill(T["handoff.line"],{req:s.root+"/"+s.requests_path,root:s.root,
      jobs:(s.jobs||[]).join(" ")});
    ho.innerHTML=`<b>${fill(T["handoff.title"],{n:q.length})}</b> <span class="hint">${T["handoff.hint"]}</span>`+
      `<div class="row" style="align-items:center;margin-top:8px">`+
      `<input type="text" id="handoffline" readonly style="flex:1" value="${esc(line)}">`+
      `<button class="btn" onclick="copyHandoff()">${T["handoff.copy"]}</button></div>`;
  } else ho.style.display="none";
  const rulewait=syncRules();
  const ready=A.length>0&&working===0&&rulewait===0;
  document.querySelectorAll(".nextbtn").forEach(b=>b.disabled=!ready);
  const g=document.getElementById("gate");
  if(rulewait>0){g.style.display="";g.textContent=fill(T["rule.locked"],{n:rulewait});}
  else if(A.length&&!ready){g.style.display="";g.textContent=fill(T["next.locked"],{n:working});}
  else g.style.display="none";
  if(ready) setStep(6);
  const now={}; for(const a of A) if(isBusy(a)) now[a.path]=a.sha||a.updated_at||"";
  const arrived=Object.keys(busyAt).filter(p=>!(p in now)&&
    A.some(a=>a.path===p&&(a.sha||a.updated_at||"")!==busyAt[p]));
  busyAt=now;
  if(arrived.length) notify(fill(T["proc.arrived"],{n:arrived.length}));
  schedule();
  draw();
}
async function copyHandoff(){
  await navigator.clipboard.writeText(document.getElementById("handoffline").value);
  notify(T["handoff.copied"]);
}
function setFilter(f){filter=f;applyState(state);}
function setStep(n){document.querySelectorAll(".stepper .step").forEach(el=>{
  const i=+el.dataset.step;el.classList.toggle("done",i<n);el.classList.toggle("current",i===n);
  const d=el.querySelector(".n");if(d)d.textContent=i<n?"✓":String(i);});}
function draw(){
  const A=(state.assets||[]).filter(a=>filter==="all"||(filter==="working"?a.status!=="approved":a.status===filter));
  const g=document.getElementById("grid");
  if(!(state.assets||[]).length){g.innerHTML=`<div class="empty">${T.none}</div>`;return;}
  if(!A.length){g.innerHTML=`<div class="empty">${T.empty}</div>`;return;}
  g.innerHTML=A.map(a=>{
    const isVid=a.kind==="video";
    const v=encodeURIComponent(a.sha||a.updated_at||"");
    const src="/img?path="+encodeURIComponent(a.path)+(v?"&v="+v:"");
    const media=isVid
      ? `<video controls preload="metadata" src="${src}"></video>`
      : `<img loading="lazy" src="${src}" onclick="zoom('${src}')" alt="${esc(a.file)}">`;
    const busy=isBusy(a);
    const since=a.decided_at?` · ${new Date(a.decided_at).toLocaleString()}`:"";
    const wrap=`<div class="media">${media}`+(busy
      ? `<div class="processing"><span class="spin"></span><b>${T["proc.label"]}</b>`+
        `<small>${T["queue.waiting"]}${since}</small></div>`
      : "")+`</div>`;
    const isNew=seenBefore&&a.updated_at&&a.updated_at>seenBefore&&a.status==="pending";
    const badges=(a.queued?`<span class="tag"><span class="dot"></span>${T["queue.queued"]}</span>`:"")
      +(isNew?`<span class="tag new"><span class="dot"></span>${T.newbadge}</span>`:"");
    const note=(a.status==="redo"&&a.note)?`<p class="hint">↻ ${esc(a.note)}</p>`:"";
    return `<div class="card rcard${busy?" busy":""}">
      ${wrap}
      <div class="body">
        <div class="row"><span class="tag ${a.status}"><span class="dot"></span>${SING[a.status]||a.status}</span>
          ${isVid?`<span class="tag">${T.video}</span>`:""}${badges}</div>
        <div class="name">${esc(a.file)} <span class="hint">· ${T.job} ${esc(a.job||"—")}</span></div>
        ${a.prompt?`<p class="hint">${T.prompt} ${esc(a.prompt).slice(0,180)}</p>`:""}
        ${note}
        <div class="row">
          <button class="btn ok" onclick="decide('${esc(a.path)}','approved')">${T.approve}</button>
          <button class="btn no" onclick="decide('${esc(a.path)}','rejected')">${T.reject}</button>
          <button class="btn" onclick="regen('${esc(a.path)}')">${T.redo}</button></div>
      </div></div>`;
  }).join("");
}
function zoom(u){const i=document.getElementById("zoomimg");
  i.onerror=()=>{document.getElementById("zoom").close();notify(T.zoomfail);};
  i.src=u;document.getElementById("zoom").showModal();}
async function decide(path,status){
  const {ok,j}=await pj("/decision",{method:"POST",body:JSON.stringify({path,status})});
  if(!ok){await tell(j.error||T.failed);return;}
  await load();
  notify(status==="approved"?T.approvetoast:T.rejecttoast);
}
async function regen(path){
  const note=await ask(T.regenask);
  if(note===null||note.trim()==="") return;
  const {ok,j}=await pj("/regen",{method:"POST",body:JSON.stringify({path,note})});
  if(!ok){await tell(j.error||T.failed);return;}
  await load();
  notify(T.regentoast);
}
async function nextStep(){
  const {ok,j}=await pj("/next",{method:"POST",body:"{}"});
  const box=document.getElementById("next-result");
  if(!ok){box.innerHTML="";await tell(j.error||T.failed);return;}
  if(j.waiting>0){
    box.innerHTML="";
    notify(fill(T["next.busy"],{n:j.waiting||0}));
    return;
  }
  box.innerHTML=`<div class="callout ok">${fill(T["next.ready"],{n:j.total})}<br>`+
    `<span class="hint">${esc(j.command)}</span></div>`;
  notify(T["next.toast"]);
  setStep(6);
}
async function openAssets(){
  const {ok,j}=await pj("/open-assets",{method:"POST",body:"{}"});
  if(!ok){await tell(j.error||T.failed);return;}
  notify(fill(T["openfolder.toast"],{dir:j.path}));
}
async function poll(){
  if(document.querySelector("dialog[open]")) return;
  let s;
  try{s=await (await fetch("/state")).json();}catch(e){return;}
  if(JSON.stringify(s)!==lastState) applyState(s);
}
function schedule(){
  const ms=(state&&(state.assets||[]).filter(isBusy).length)?1500:6000;
  if(ms===pollMs) return;
  pollMs=ms; if(timer) clearInterval(timer); timer=setInterval(poll,ms);
}
document.addEventListener("visibilitychange",()=>{if(!document.hidden)poll();});
window.addEventListener("focus",poll);
load();
schedule();
</script></body></html>"""


def onboard_page():
    return _head(i18n.t("ob.title")) + f"""
<header><span class="brand">campaign-kit</span><h1>{i18n.t('ob.title')}</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
""" + _mode_switch("visual") + f"""
<button onclick="load()">{i18n.t('btn.refresh')}</button></header>
<div class="banner">
""" + _stepper(1, 0) + f"""
<span class="meta">{i18n.t('ob.meta.steps')}</span>
<div class="callout warn" id="ready"></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">1</span>{i18n.t('ob.p1.title')}</h2>
<p class="desc">{i18n.t('ob.p1.desc')}</p>
<span class="meta" id="slotprog"></span>
<div class="grid" id="slots"></div></div>
<div class="panel"><h2><span class="n">2</span>{i18n.t('ob.p2.title')}</h2>
<p class="desc">{i18n.t('ob.p2.desc')}</p>
<div class="dropzone" id="briefdrop">
<label class="btn">{i18n.t('ob.p2.upload')}<input type="file"
  accept=".md,.txt,.rtf,.pdf,.docx" hidden onchange="uploadBrief(this.files)"></label>
<span class="meta">{i18n.t('ob.p2.drop')}</span>
<span class="meta" id="brieffile">{i18n.t('ob.p2.filenote')}</span></div>
<div class="chips" id="sections"></div>
<div class="chips" id="concepts"></div>
<textarea id="brief"></textarea>
<p class="desc" style="margin:16px 0 6px"><b>{i18n.t('ob.p2.dir.title')}</b> — {i18n.t('ob.p2.dir.desc')}</p>
<textarea id="direction" style="min-height:130px" placeholder="{i18n.t('ob.p2.dir.ph')}"></textarea>
<div class="row"><button class="btn primary" onclick="saveBrief()">{i18n.t('ob.p2.save')}</button>
<span class="meta">{i18n.t('ob.p2.legend')}</span></div>
<div class="docsblock">
<p class="desc"><b>{i18n.t('ob.p2.docs.title')}</b> — {i18n.t('ob.p2.docs.desc')}</p>
<div class="dropzone" id="docsdrop">
<label class="btn">{i18n.t('ob.p2.docs.upload')}<input type="file"
  accept="{','.join(onboard.BRIEF_DOC_EXT)}" multiple hidden onchange="uploadDocs(this.files)"></label>
<span class="meta">{i18n.t('ob.p2.docs.drop')}</span>
<span class="meta" id="docscount"></span></div>
<ul class="files" id="docslist"></ul>
</div></div>
<div class="panel"><h2><span class="n">3</span>{i18n.t('ob.p3.title')}</h2>
<p class="desc">{i18n.t('ob.p3.desc')}</p>
<div class="row"><input type="text" id="bid" placeholder="{i18n.t('ob.p3.idph')}">
<button class="btn primary" onclick="derive()">{i18n.t('ob.p3.run')}</button></div>
<div id="result"></div></div>
<div class="panel"><h2><span class="n">4</span>{i18n.t('ob.p4.title')}</h2>
<p class="desc">{i18n.t('ob.p4.desc')}</p>
<span class="meta">{i18n.t('ob.p4.pipe')}</span>
<p class="desc" style="margin-top:10px">{i18n.t('ob.p4.paste')}</p>
<div class="row"><input type="text" id="agentline" readonly>
<button class="btn primary" onclick="copyAgent()">{i18n.t('ob.p4.copy')}</button></div></div>
</div>
""" + _modal() + _JS_UTIL + _inject("ob.js") + """
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
  const ta=document.getElementById("brief"), dir=document.getElementById("direction");
  if(document.activeElement!==ta) ta.value=S.briefing.text;
  if(document.activeElement!==dir) dir.value=S.direction||"";
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
async function saveBrief(quiet){
  await fetch("/briefing",{method:"POST",body:JSON.stringify({
    text:document.getElementById("brief").value,
    direction:document.getElementById("direction").value})});
  await load();
  if(!quiet) notify(T.dirsaved);
}
const saveAll=()=>saveBrief(true);
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
async function derive(){
  const id=document.getElementById("bid").value.trim();
  if(!id){await tell(T.needid);return;}
  const r=await fetch("/intake",{method:"POST",body:JSON.stringify({brand_id:id})});
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
""" + _mode_js("visual") + """
</script></body></html>"""


def _open_folder(path):
    """Open the folder in the OS file manager (Finder/Explorer/xdg). Local server."""
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

    def _send(self, code, body, ctype="application/json", cors=False):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if cors:
            # Only /ping uses it: the mode switch probes the other kit's server, which is another
            # port on this same machine. Read-only, localhost, no credentials.
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _safe(self, rel):
        path = os.path.realpath(os.path.join(self.root, rel))
        if not path.startswith(os.path.realpath(self.root) + os.sep):
            return None
        return path if os.path.isfile(path) else None

    def _onboard_post(self, length):
        url = urlparse(self.path)
        if url.path == "/upload":
            q = parse_qs(url.query)
            slot = q.get("slot", [""])[0]
            name = os.path.basename(q.get("name", [""])[0])
            spec = next((s for s in onboard.SLOTS if s["key"] == slot), None)
            if not spec or not name or name.startswith("."):
                return self._send(400, {"error": i18n.t("ob.err.slot")})
            if not name.lower().endswith(spec["ext"]):
                return self._send(400, {"error": i18n.t(
                    "ob.err.ext",
                    label=i18n.t(f"slot.{slot}.label"), exts=", ".join(spec["ext"]))})
            if length > 300 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.big")})
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
                return self._send(400, {"error": i18n.t("ob.err.slot")})
            p = os.path.join(self.root, spec["dir"], name)
            if os.path.isfile(p):
                os.remove(p)
            return self._send(200, {"ok": True})
        if url.path == "/briefing-file":
            q = parse_qs(url.query)
            name = os.path.basename(q.get("name", [""])[0])
            if not name or name.startswith(".") or not name.lower().endswith(intake.BRIEF_EXT):
                return self._send(400, {"error": i18n.t("ob.err.briefext")})
            if length > 20 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.briefbig")})
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
                    "ob.err.docext", exts=", ".join(onboard.BRIEF_DOC_EXT))})
            if length > 20 * 1024 * 1024:
                return self._send(413, {"error": i18n.t("ob.err.docbig")})
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
                return self._send(400, {"error": i18n.t("ob.err.slot")})
            p = os.path.join(self.root, onboard.BRIEF_DOCS_DIR, name)
            if os.path.isfile(p):
                os.remove(p)
            return self._send(200, {"ok": True})
        payload = json.loads(self.rfile.read(length) or b"{}")
        if url.path == "/briefing":
            with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                f.write(payload.get("text", ""))
            if "direction" in payload:
                onboard.save_direction(self.root, payload["direction"])
            return self._send(200, {"ok": True})
        if url.path == "/intake":
            bid = payload.get("brand_id", "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", bid):
                return self._send(400, {"error": i18n.t("ob.err.brandid")})
            summary, gaps = intake.run(self.root, bid, self.brands)
            return self._send(200, {"summary": summary, "gaps": gaps})
        if url.path == "/answers":
            bid = os.path.basename(payload.get("brand_id", ""))
            path = os.path.join(self.brands, bid, "answers.json")
            if not os.path.isdir(os.path.dirname(path)):
                return self._send(400, {"error": i18n.t("ob.err.intakefirst")})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload.get("answers", {}), f, indent=2, ensure_ascii=False)
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/ping":
            return self._send(200, {"kit": "visual", "mode": self.mode, "root": self.root}, cors=True)
        if url.path == "/":
            page = (onboard_page() if self.mode == "onboard"
                    else assets_page() if self.mode == "assets" else review_page())
            self._send(200, page.encode(), "text/html; charset=utf-8")
        elif url.path == "/state":
            if self.mode == "onboard":
                return self._send(200, onboard.status(self.root))
            if self.mode == "assets":
                return self._send(200, self._assets_payload())
            with open(os.path.join(self.root, "state.json"), encoding="utf-8") as f:
                state = json.load(f)
            campaign.sync_requests(self.root, state)
            state["rule_proposals"] = rules.payload(self.root)
            self._send(200, state)
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
            dirs = font_dirs([brand.assets_dir, os.path.join(brand.root, "fonts")])
            fonts = sorted({os.path.basename(p) for d in dirs
                            for p in _glob.glob(os.path.join(d, "*"))
                            if p.lower().endswith((".ttf", ".otf", ".ttc"))})
            self._send(200, {"concept": concept, "palette": palette, "type": type_cfg,
                             "fonts": fonts, "override": campaign.load_style(self.root, concept)})
        else:
            self._send(404, {"error": "not found"})

    def _style_ref(self, length):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        concept = q.get("concept", [""])[0]
        camp = campaign.load_campaign(self.root)
        known = set(campaign.available_concepts()) | set(camp.get("concepts") or [])
        if not re.fullmatch(r"[A-Za-z0-9_-]+", concept) or concept not in known:
            return self._send(400, {"error": i18n.t("rv.err.concept")})
        name = q.get("name", [""])[0]
        if url.path == "/style-ref-delete":
            if not campaign.drop_ref(self.root, concept, name):
                return self._send(400, {"error": i18n.t("rv.js.style.refgone")})
            return self._send(200, {"ok": True, "refs": campaign.list_refs(self.root, concept)})
        if length > campaign.MAX_REF:
            self.rfile.read(length)
            return self._send(413, {"error": i18n.t("rv.js.style.big")})
        try:
            saved = campaign.add_ref(self.root, concept, name, self.rfile.read(length))
        except ValueError:
            return self._send(400, {"error": i18n.t("rv.js.style.badtype")})
        return self._send(200, {"ok": True, "name": saved,
                                "refs": campaign.list_refs(self.root, concept)})

    def _assets_payload(self):
        payload = assets.payload(self.root)
        camp = {}
        cpath = os.path.join(self.root, "campaign.json")
        if os.path.isfile(cpath):
            with open(cpath, encoding="utf-8") as f:
                camp = json.load(f)
        payload["campaign"] = camp.get("name") or camp.get("slug") or os.path.basename(self.root)
        payload["brand"] = camp.get("brand", "")
        payload["rule_proposals"] = rules.payload(self.root)
        return payload

    def _assets_post(self, path, payload):
        if path in ("/decision", "/regen"):
            target = payload.get("path") or payload.get("id") or ""
            if not target:
                return self._send(400, {"error": i18n.t("as.err.unknown")})
            redo = path == "/regen"
            ok = assets.decide(self.root, target, "redo" if redo else payload.get("status", "pending"),
                               payload.get("note", "") if redo else "", who="user")
            if not ok:
                return self._send(400, {"error": i18n.t("as.err.unknown")})
            return self._send(200, {"ok": True, "queued": len(assets.sync_requests(self.root))})
        if path == "/next":
            ok, total = assets.all_approved(self.root)
            return self._send(200, {"ok": ok, "total": total,
                                    "waiting": len(assets.unapproved(self.root)),
                                    "command": i18n.t("as.js.next.cmd", root=self.root)})
        if path == "/open-assets":
            d = os.path.join(self.root, assets.DIR)
            if not os.path.isdir(d):
                return self._send(400, {"error": i18n.t("as.err.none")})
            _open_folder(d)
            return self._send(200, {"ok": True, "path": d})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if self.mode == "onboard":
            return self._onboard_post(length)
        if self.path.startswith("/style-ref"):
            return self._style_ref(length)
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/rule-decision":
            prop = rules.decide(self.root, payload.get("id", ""), bool(payload.get("agree")), who="user")
            if prop is None:
                return self._send(400, {"error": i18n.t("cli.rules.err.unknown",
                                                        id=payload.get("id", ""))})
            return self._send(200, {"ok": True, "status": prop["status"], "target": prop["target"]})
        if self.mode == "assets":
            return self._assets_post(self.path, payload)
        state_path = os.path.join(self.root, "state.json")
        if self.path in ("/decision", "/regen"):
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with _STATE_LOCK:
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
                        if p["status"] in ("rejected", "redo"):
                            p["decided_at"] = now
                            p["queued"] = True
                        else:
                            p.pop("decided_at", None)
                            p.pop("queued", None)
                        if p["status"] != "approved":
                            p.pop("delivered", None)
                            p.pop("delivery_path", None)
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                batch = campaign.sync_requests(self.root, state)
            self._send(200, {"ok": True, "queued": len(batch)})
        elif self.path == "/concept-style":
            concept = payload.get("concept", "")
            camp = campaign.load_campaign(self.root)
            known = set(campaign.available_concepts()) | set(camp.get("concepts") or [])
            if not re.fullmatch(r"[A-Za-z0-9_-]+", concept) or concept not in known:
                return self._send(400, {"error": i18n.t("rv.err.concept")})
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
            style = campaign.load_style(self.root, concept)
            if pal:
                style["palette"] = pal
            else:
                style.pop("palette", None)
            if typ:
                style["type"] = typ
            else:
                style.pop("type", None)
            if note:
                style["note"] = note
            else:
                style.pop("note", None)
            sp = campaign.style_path(self.root, concept)
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, "w", encoding="utf-8") as f:
                yaml.safe_dump(style, f, allow_unicode=True, sort_keys=False)
            rnote = note or i18n.t("rv.restyle.defaultnote")
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            count = 0
            with _STATE_LOCK:
                with open(state_path, encoding="utf-8") as f:
                    state = json.load(f)
                for p in state["pieces"]:
                    if p["concept"] == concept:
                        p["status"] = "redo"
                        p["note"] = rnote
                        p["restyle"] = True
                        p["decided_at"] = now
                        p["queued"] = True
                        p.pop("delivered", None)
                        p.pop("delivery_path", None)
                        count += 1
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                batch = campaign.sync_requests(self.root, state)
            self._send(200, {"ok": True, "concept": concept, "count": count,
                             "queued": len(batch)})
        elif self.path == "/continue":
            if not os.path.isfile(state_path):
                return self._send(400, {"error": i18n.t("rv.err.nostate")})
            self._send(200, campaign.deliver(self.root))
        elif self.path == "/open-delivery":
            dest = campaign.delivery_dir(self.root)
            if not os.path.isdir(dest):
                return self._send(400, {"error": i18n.t("rv.js.openfolder.empty")})
            _open_folder(dest)
            self._send(200, {"ok": True, "path": dest})
        else:
            self._send(404, {"error": "not found"})


def _serve(root, port, open_browser=True, shortcut_name="OPEN-REVIEW.html"):
    """Start the UI on 127.0.0.1, write a clickable shortcut in the folder and open the browser.

    Port busy → try the next ones: each campaign gets its own, no conflict.
    """
    server = None
    for p in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError(f"no free port in {port}..{port + 19}")
    url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    shortcut = os.path.join(root, shortcut_name)
    with open(shortcut, "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0;url={url}">'
                '<title>campaign-kit</title></head>'
                '<body style="font-family:system-ui,sans-serif;padding:40px">'
                f'<p>{i18n.t("cli.shortcut.opening", url=url)} <a href="{url}">{url}</a></p>'
                f'<p>{i18n.t("cli.shortcut.manual")}</p>'
                '</body></html>\n')
    print(f"\n  ➜  {url}\n  ({i18n.t('cli.serve.shortcut', name=shortcut_name)})\n", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server, url


def serve(campaign_root, port=8765, open_browser=True):
    Handler.mode = "review"
    Handler.root = os.path.abspath(campaign_root)
    return _serve(os.path.abspath(campaign_root), port, open_browser)


def serve_assets(campaign_root, port=8769, open_browser=True):
    """Stage 5: approve the generated images before anything is composited on them."""
    Handler.mode = "assets"
    Handler.root = os.path.abspath(campaign_root)
    return _serve(os.path.abspath(campaign_root), port, open_browser,
                  shortcut_name="OPEN-ASSETS.html")


def serve_onboard(inbox, brands_dir, port=8766, open_browser=True):
    inbox = os.path.abspath(os.path.expanduser(inbox))
    onboard.scaffold(inbox)
    Handler.mode = "onboard"
    Handler.root = inbox
    Handler.brands = os.path.abspath(brands_dir)
    return _serve(inbox, port, open_browser, shortcut_name="OPEN-ONBOARDING.html")