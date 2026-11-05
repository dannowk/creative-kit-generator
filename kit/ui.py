"""UI local (onboarding + revisão): http.server da stdlib + páginas claras. Zero npm, zero build.

Sobe em 127.0.0.1. Tema claro com passos numerados e legenda de status para a pessoa se
localizar; onboarding prepara a pasta, revisão deixa aprovar/rejeitar/refazer por clique e
enfileira pedidos de regeneração que o agente executa. Morre quando você fecha.
"""

import json
import os
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import intake, onboard

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
.card .body{padding:14px 16px;display:flex;flex-direction:column;gap:10px;flex:1}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tag{font-size:12px;font-weight:600;padding:3px 10px;border-radius:99px;border:1px solid var(--pend-line);
 background:var(--pend-bg);color:var(--pend);display:inline-flex;align-items:center;gap:6px}
.tag.approved{background:var(--ok-bg);border-color:var(--ok-line);color:var(--ok)}
.tag.rejected{background:var(--bad-bg);border-color:var(--bad-line);color:var(--bad)}
.tag.blocked{background:var(--warn-bg);border-color:var(--warn-line);color:var(--warn)}
.tag .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
.hint{color:var(--mut);font-size:13px;margin:0}
.files{margin:0;padding:0;list-style:none;font-size:13px;display:grid;gap:4px}
.files li{display:flex;justify-content:space-between;gap:8px;background:var(--pend-bg);border-radius:8px;padding:4px 8px}
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
dialog .msgbody{display:grid;gap:12px;padding:10px 12px;min-width:320px;max-width:480px}
dialog .msgbody p{margin:0;font-size:14px}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:50;
 background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:10px;
 padding:10px 16px;font-size:14px;box-shadow:0 4px 16px rgba(16,24,32,.15);max-width:90vw}
</style>"""

_STEPS = ["Arquivos", "Briefing", "Marca", "Gerar", "Revisar"]


def _head(title):
    return ('<!doctype html><html lang="pt"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>campaign-kit · ' + title + '</title>' + _STYLE + '</head><body>')


def _stepper(current, done=0):
    out = ['<div class="stepper">']
    for i, label in enumerate(_STEPS, 1):
        cls = "done" if i <= done else ("current" if i == current else "")
        mark = "✓" if i <= done else str(i)
        out.append(f'<span class="step {cls}"><span class="n">{mark}</span>{label}</span>')
        if i < len(_STEPS):
            out.append('<span class="bar"></span>')
    out.append("</div>")
    return "".join(out)


_MODAL = """
<dialog id="msgbox"><div class="msgbody"><p id="msgtext"></p>
<input type="text" id="msginput" hidden>
<div class="row"><span class="sp"></span>
<button class="btn" id="msgcancel">cancelar</button>
<button class="btn primary" id="msgok">ok</button></div></div></dialog>
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
</script>
"""


PAGE = _head("revisão") + """
<header><span class="brand">campaign-kit</span><h1 id="title">Revisão</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button onclick="load()">↻ atualizar</button></header>
<div class="banner">
""" + _stepper(5, 4) + """
<div class="stats" id="stats"></div>
<div class="legend"><b>Legenda:</b>
<span class="tag approved"><span class="dot"></span>aprovada = vai ao ar</span>
<span class="tag"><span class="dot"></span>pendente = aguarda você</span>
<span class="tag rejected"><span class="dot"></span>rejeitada = descartada</span>
<span class="tag blocked"><span class="dot"></span>bloqueada = regra de compliance violada</span></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">5</span>Revisar peças</h2>
<p class="desc">Clique numa peça para ampliar. Aprove, rejeite ou peça refazer; bloqueios de compliance aparecem no card.
Perdeu o endereço? Ele fica no topo desta tela e no arquivo <b>ABRIR-REVISAO.html</b> da pasta da campanha.</p>
<div class="filters" id="filters"></div>
<div class="row" style="align-items:center"><span class="meta">Conceito:</span><div class="filters" id="cfilters"></div></div>
<div class="rgrid" id="grid"></div></div>
</div>
<dialog id="zoom" onclick="this.close()"><img id="zoomimg" alt=""></dialog>
""" + _MODAL + _JS_UTIL + """
<script>
let state=null, filter="all", cfilter="all";
const LBL={all:"Todas",pending:"Pendentes",approved:"Aprovadas",rejected:"Rejeitadas",blocked:"Bloqueadas"};
const SING={pending:"Pendente",approved:"Aprovada",rejected:"Rejeitada",blocked:"Bloqueada"};
async function load(){
  state = await (await fetch("/state")).json();
  document.getElementById("title").textContent = state.campaign + " · " + state.brand;
  document.getElementById("meta").textContent = "etapa 5 de 5 · revisar · " + location.origin;
  const c=s=>state.pieces.filter(p=>p.status===s).length;
  document.getElementById("stats").innerHTML =
    `<span class="stat"><b>${state.pieces.length}</b> peças</span>`+
    `<span class="stat"><b>${c("approved")}</b> aprovadas</span>`+
    `<span class="stat"><b>${c("pending")}</b> pendentes</span>`+
    `<span class="stat"><b>${state.blocked_count}</b> bloqueadas</span>`;
  const counts={all:state.pieces.length};
  for(const s of ["pending","approved","rejected","blocked"]) counts[s]=c(s);
  document.getElementById("filters").innerHTML = Object.entries(counts)
    .map(([k,v])=>`<button class="${k===filter?'on':''}" onclick="setFilter('${k}')">${LBL[k]} (${v})</button>`).join("");
  const cc={}; for(const p of state.pieces) cc[p.concept]=(cc[p.concept]||0)+1;
  const concepts=(state.concepts&&state.concepts.length?state.concepts:Object.keys(cc));
  document.getElementById("cfilters").innerHTML =
    `<button class="${cfilter==='all'?'on':''}" onclick="setConcept('all')">Todos (${state.pieces.length})</button>`+
    concepts.map(k=>`<button class="${cfilter===k?'on':''}" onclick="setConcept('${k}')">${k} (${cc[k]||0})</button>`).join("");
  draw();
}
function setFilter(f){filter=f;load();}
function setConcept(k){cfilter=k;load();}
function draw(){
  const items=state.pieces
    .filter(p=>(filter==="all"||p.status===filter)&&(cfilter==="all"||p.concept===cfilter))
    .sort((a,b)=>a.concept.localeCompare(b.concept)||a.format.localeCompare(b.format));
  const g=document.getElementById("grid");
  if(!items.length){g.innerHTML='<div class="empty">Nenhuma peça neste filtro.</div>';return;}
  g.innerHTML=items.map(p=>{
    const finds=(p.findings||[]).filter(f=>f.level!=="info")
      .map(f=>`<li class="${f.level==="fail"?"fail":"warn"}">${f.level==="fail"?"Bloqueio: ":"Atenção: "}${f.message}</li>`).join("");
    const isVid=p.kind==="video";
    const media=isVid
      ? `<video controls preload="metadata" poster="/img?path=${encodeURIComponent("review/thumbs/"+p.path.replace(/\\.\\w+$/,".video.png"))}"
           src="/img?path=${encodeURIComponent("out/"+p.path)}"></video>`
      : `<img loading="lazy" src="/img?path=${encodeURIComponent("review/thumbs/"+p.path)}"
           onclick="zoom('${encodeURIComponent(p.path)}')" alt="${p.id}">`;
    return `<div class="card rcard">
      ${media}
      <div class="body">
        <div class="row"><span class="tag ${p.status}"><span class="dot"></span>${SING[p.status]}</span>
          ${isVid?'<span class="tag">vídeo</span>':""}</div>
        <div class="name">${p.concept} · ${p.format}${isVid?" · "+Math.round(p.duration||0)+"s":""}</div>
        <div class="row">
          <button class="btn ok" onclick="decide('${p.id}','approved')">✓ aprovar</button>
          <button class="btn no" onclick="decide('${p.id}','rejected')">✕ rejeitar</button>
          <button class="btn" onclick="regen('${p.id}')">↻ refazer</button></div>
        ${finds?`<ul class="findings">${finds}</ul>`:""}
      </div></div>`;
  }).join("");
}
function zoom(path){document.getElementById("zoomimg").src="/img?path="+path;
  document.getElementById("zoom").showModal();}
async function decide(id,status){
  await fetch("/decision",{method:"POST",body:JSON.stringify({id,status})});
  await load();
}
async function regen(id){
  const note=await ask("O que mudar nesta peça? (o agente executa)");
  if(note===null||note.trim()==="") return;
  await fetch("/regen",{method:"POST",body:JSON.stringify({id,note})});
  notify("Pedido enfileirado em requests.json — o agente executa.");
}
load();
</script></body></html>"""


ONBOARD_PAGE = _head("onboarding") + """
<header><span class="brand">campaign-kit</span><h1>Preparar campanha</h1>
<span class="meta" id="meta"></span><span class="sp"></span>
<button onclick="load()">↻ atualizar</button></header>
<div class="banner">
""" + _stepper(1, 0) + """
<span class="meta">etapas 1–3 nesta tela · 4 e 5 o agente continua depois</span>
<div class="callout warn" id="ready"></div>
</div>
<div class="wrap">
<div class="panel"><h2><span class="n">1</span>Arquivos da marca</h2>
<p class="desc">Solte os arquivos em cada slot (clique em adicionar ou arraste). Só o logo é obrigatório; o resto melhora o resultado.</p>
<span class="meta" id="slotprog"></span>
<div class="grid" id="slots"></div></div>
<div class="panel"><h2><span class="n">2</span>Briefing</h2>
<p class="desc">Preencha o que souber. O que ficar em branco vira uma pergunta única na etapa 3.</p>
<div class="chips" id="sections"></div>
<div class="chips" id="concepts"></div>
<textarea id="brief"></textarea>
<div class="row"><button class="btn primary" onclick="saveBrief()">salvar briefing</button>
<span class="meta">✓ = seção preenchida · • = ainda em branco</span></div></div>
<div class="panel"><h2><span class="n">3</span>Derivar marca</h2>
<p class="desc">Gera a paleta a partir do logo e abre a rodada única de perguntas.</p>
<div class="row"><input type="text" id="bid" placeholder="id da marca (ex. acme)">
<button class="btn primary" onclick="derivar()">rodar intake</button></div>
<div id="result"></div></div>
<div class="panel"><h2><span class="n">4</span>Próximas etapas (o agente continua)</h2>
<p class="desc">Depois da marca, o agente roda:</p>
<span class="meta"><code>plan</code> direção de arte a partir do briefing + refs →
<code>assets</code> gera imagem/vídeo com aviso de ≈ custo →
<code>render</code> monta as peças →
<code>review</code> você aprova / rejeita / refaz (etapa 5).</span>
<p class="desc" style="margin-top:10px">Cole isto no seu agente (Claude, Codex, Qoder…) aberto na pasta do kit:</p>
<div class="row"><input type="text" id="agentline" readonly>
<button class="btn primary" onclick="copyAgent()">copiar frase</button></div></div>
</div>
""" + _MODAL + _JS_UTIL + """
<script>
let S=null, INT=null;
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmt=n=>n>1048576?(n/1048576).toFixed(1)+" MB":Math.max(1,Math.round(n/1024))+" KB";
async function load(){
  S = await (await fetch("/state")).json();
  document.getElementById("agentline").value = "leia o AGENTS.md e rode a campanha de " + S.inbox;
  document.getElementById("meta").textContent = S.inbox;
  const slotsOk=Object.values(S.slots).filter(s=>s.ok).length;
  const secOk=S.briefing.sections.filter(x=>x.filled).length;
  document.getElementById("slotprog").textContent =
    slotsOk+"/"+Object.keys(S.slots).length+" slots com arquivo · briefing "+secOk+"/"+S.briefing.sections.length+" seções";
  const missing=[];
  for(const s of Object.values(S.slots)) if(s.required&&!s.ok) missing.push(s.label);
  for(const t of S.briefing.missing) missing.push("briefing: "+t);
  const r=document.getElementById("ready");
  if(S.ready){r.className="callout ok";r.textContent="✓ Pronto para derivar a marca (etapa 3).";}
  else{r.className="callout warn";r.textContent="Faltam: "+missing.join(" · ");}
  document.getElementById("slots").innerHTML = Object.entries(S.slots).map(([k,s])=>`
    <div class="card slot" data-slot="${k}"><div class="body">
      <div class="row"><b>${s.label}</b><span class="sp"></span>
        <span class="tag ${s.ok?"approved":(s.required?"blocked":"")}"><span class="dot"></span>${s.ok?"ok":(s.required?"faltando":"opcional")}</span></div>
      <p class="hint">${s.hint}</p>
      <ul class="files">${s.files.map(f=>`<li>${esc(f.name)}<span class="meta">${fmt(f.size)}</span></li>`).join("")||'<li><span class="meta">vazio</span></li>'}</ul>
      <div class="row"><label class="btn">+ adicionar<input type="file" ${s.multiple?"multiple":""}
        accept="${s.ext.join(",")}" hidden onchange="upload('${k}',this.files)"></label>
      <span class="meta">ou arraste aqui</span></div>
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
    ? '<span class="meta">Conceitos reconhecidos:</span>'+cs.map(c=>`<span class="tag approved">${esc(c)}</span>`).join("")
    : '<span class="meta">Liste os conceitos na seção 7 (ex.: clean, editorial, cinema) — cada um vira uma entrega e um filtro na revisão.</span>';
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
async function copyAgent(){
  await navigator.clipboard.writeText(document.getElementById("agentline").value);
  notify("Frase copiada — cole no agente aberto na pasta do kit.");
}
async function derivar(){
  const id=document.getElementById("bid").value.trim();
  if(!id){await tell("Dá um id pra marca (ex. acme)");return;}
  const r=await fetch("/intake",{method:"POST",body:JSON.stringify({brand_id:id})});
  if(!r.ok){await tell((await r.json()).error);return;}
  INT=await r.json(); drawResult();
}
function drawResult(){
  const s=INT.summary;
  document.getElementById("result").innerHTML = `
    <div class="row"><span class="meta">paleta proposta:</span>
      ${Object.entries(s.palette||{}).map(([k,v])=>`<span class="sw" style="background:${v}" title="${k} ${v}"></span>`).join("")||'<span class="meta">sem logo</span>'}
      <span class="meta">· ${s.ref_count} refs · ${s.photos.length} fotos · ${s.videos.length} vídeos · ${s.fonts} fontes</span></div>
    <div class="row"><span class="meta">conceitos pedidos:</span>
      ${(s.concepts_requested||[]).map(c=>`<span class="tag approved">${esc(c)}</span>`).join("")||'<span class="meta">nenhum — responda abaixo</span>'}</div>
    ${INT.gaps.map(g=>`<div class="gap"><b>${esc(g.question)}</b>
      <span class="why">${esc(g.why)}</span>
      <input type="text" id="gap-${g.field}" placeholder="sua resposta"></div>`).join("")}
    <div class="row"><button class="btn primary" onclick="saveAnswers()">salvar respostas</button>
      <span class="meta">uma rodada só; o agente aplica no brand.yaml</span></div>`;
}
async function saveAnswers(){
  const answers={};
  for(const g of INT.gaps) answers[g.field]=document.getElementById("gap-"+g.field).value;
  await fetch("/answers",{method:"POST",body:JSON.stringify({brand_id:INT.summary.brand,answers})});
  notify("Respostas salvas em brands/"+INT.summary.brand+"/answers.json — o agente aplica em uma rodada.");
}
load();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    root = None
    mode = "review"
    brands = None

    def log_message(self, *args):
        pass

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
        url = urlparse(self.path)
        if url.path == "/upload":
            q = parse_qs(url.query)
            slot = q.get("slot", [""])[0]
            name = os.path.basename(q.get("name", [""])[0])
            spec = next((s for s in onboard.SLOTS if s["key"] == slot), None)
            if not spec or not name or name.startswith("."):
                return self._send(400, {"error": "slot ou nome inválido"})
            if not name.lower().endswith(spec["ext"]):
                return self._send(400, {"error": f"{spec['label']} aceita {', '.join(spec['ext'])}"})
            if length > 300 * 1024 * 1024:
                return self._send(413, {"error": "arquivo > 300 MB: solte direto na pasta pelo Finder"})
            data = self.rfile.read(length)
            d = os.path.join(self.root, spec["dir"])
            os.makedirs(d, exist_ok=True)
            if not spec["multiple"]:
                for f in os.listdir(d):
                    os.remove(os.path.join(d, f))
            with open(os.path.join(d, name), "wb") as f:
                f.write(data)
            return self._send(200, {"ok": True})
        payload = json.loads(self.rfile.read(length) or b"{}")
        if url.path == "/briefing":
            with open(os.path.join(self.root, "briefing.md"), "w", encoding="utf-8") as f:
                f.write(payload.get("text", ""))
            return self._send(200, {"ok": True})
        if url.path == "/intake":
            bid = payload.get("brand_id", "").strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", bid):
                return self._send(400, {"error": "id da marca: letras minúsculas, números e hífen"})
            summary, gaps = intake.run(self.root, bid, self.brands)
            return self._send(200, {"summary": summary, "gaps": gaps})
        if url.path == "/answers":
            bid = os.path.basename(payload.get("brand_id", ""))
            path = os.path.join(self.brands, bid, "answers.json")
            if not os.path.isdir(os.path.dirname(path)):
                return self._send(400, {"error": "rode o intake primeiro"})
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload.get("answers", {}), f, indent=2, ensure_ascii=False)
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            page = ONBOARD_PAGE if self.mode == "onboard" else PAGE
            self._send(200, page.encode(), "text/html; charset=utf-8")
        elif url.path == "/state":
            if self.mode == "onboard":
                return self._send(200, onboard.status(self.root))
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
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if self.mode == "onboard":
            return self._onboard_post(length)
        payload = json.loads(self.rfile.read(length) or b"{}")
        state_path = os.path.join(self.root, "state.json")
        if self.path == "/decision":
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            for p in state["pieces"]:
                if p["id"] == payload.get("id"):
                    p["status"] = payload.get("status", "pending")
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            self._send(200, {"ok": True})
        elif self.path == "/regen":
            req_path = os.path.join(self.root, "requests.json")
            reqs = []
            if os.path.isfile(req_path):
                with open(req_path, encoding="utf-8") as f:
                    reqs = json.load(f)
            reqs.append(payload)
            with open(req_path, "w", encoding="utf-8") as f:
                json.dump(reqs, f, indent=2, ensure_ascii=False)
            self._send(200, {"ok": True, "queued": len(reqs)})
        else:
            self._send(404, {"error": "not found"})


def _serve(root, port, open_browser=True, shortcut_name="ABRIR-REVISAO.html"):
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
        f.write('<!doctype html><html lang="pt"><head><meta charset="utf-8">'
                f'<meta http-equiv="refresh" content="0;url={url}">'
                '<title>abrir revisão</title></head>'
                '<body style="font-family:system-ui,sans-serif;padding:40px">'
                f'<p>Abrindo <a href="{url}">{url}</a> …</p>'
                '<p>Se o navegador não abrir sozinho, clique no link.</p>'
                '</body></html>\n')
    print(f"\n  ➜  {url}\n  (atalho: {shortcut_name} na pasta da campanha)\n", flush=True)
    if open_browser:
        webbrowser.open(url)
    return server, url


def serve(campaign_root, port=8765, open_browser=True):
    Handler.mode = "review"
    Handler.root = os.path.abspath(campaign_root)
    return _serve(os.path.abspath(campaign_root), port, open_browser)


def serve_onboard(inbox, brands_dir, port=8766, open_browser=True):
    inbox = os.path.abspath(os.path.expanduser(inbox))
    onboard.scaffold(inbox)
    Handler.mode = "onboard"
    Handler.root = inbox
    Handler.brands = os.path.abspath(brands_dir)
    return _serve(inbox, port, open_browser, shortcut_name="ABRIR-ONBOARDING.html")