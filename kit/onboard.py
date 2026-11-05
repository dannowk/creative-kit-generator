"""Onboarding: prepara a pasta que o usuário joga no agente.

Scaffold com subpastas nomeadas + briefing guiado; status diz o que falta antes do
intake rodar. O que é opcional fica dito como opcional — nunca bloqueia por capricho.
"""

import os
import re

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
FONT_EXT = (".otf", ".ttf", ".ttc")
VID_EXT = (".mp4", ".mov", ".webm", ".m4v")

SLOTS = [
    {"key": "logo", "dir": "logo", "label": "Logo", "ext": IMG_EXT, "multiple": False,
     "required": True,
     "hint": "PNG com fundo transparente, de preferência. É dele que sai a paleta proposta."},
    {"key": "refs", "dir": "refs", "label": "Referências de look", "ext": IMG_EXT, "multiple": True,
     "required": False,
     "hint": "2 a 6 imagens do look desejado. O agente olha com visão e escreve a direção de arte a partir delas."},
    {"key": "fonts", "dir": "fonts", "label": "Fontes da marca", "ext": FONT_EXT, "multiple": True,
     "required": False,
     "hint": ".otf / .ttf. Sem elas, uso substitutas do sistema e aviso exatamente quais."},
    {"key": "photos", "dir": "photos", "label": "Fotos para as peças", "ext": IMG_EXT, "multiple": True,
     "required": False,
     "hint": "Fotos que podem virar peça. Sem elas, o provider gera — e a estimativa de custo aparece antes de gerar."},
    {"key": "videos", "dir": "videos", "label": "Vídeos", "ext": VID_EXT, "multiple": True,
     "required": False,
     "hint": "Clipes fonte ou referência de movimento. Vídeos novos são gerados pelo provider (ex. Magnific via MCP), com estimativa de custo antes de gerar."},
]

BRIEFING_TEMPLATE = """# Briefing da campanha

<!-- Preencha o que souber. O que ficar em branco vira uma pergunta única no fim do onboarding. -->

## 1. Negócio e produto
_preencher: o que a empresa vende, em uma frase._

## 2. Público
_preencher: quem decide a compra._

## 3. Objetivo, oferta e CTA
_preencher: o que a campanha deve fazer e o texto do botão._

## 4. Tom de voz
_preencher: como a marca fala — e o que ela nunca pode prometer._

## 5. Canais
_preencher: Meta, Google, LinkedIn, impresso, web…_

## 6. Idiomas
_preencher: ex. pt-BR, en._

## 7. Conceitos (direções visuais)
_preencher: quantas direções diferentes você quer e o nome de cada uma, separados por vírgula — ex.: clean, editorial, cinema. Cada conceito vira um template, uma pasta de entrega e um filtro na revisão._

## 8. Direção visual
_preencher: o que copiar das referências e o que evitar._

## 9. Compliance
_preencher: disclaimer obrigatório, cor proibida, termo que não pode quebrar linha._

## 10. Assets existentes
_preencher: fotos e vídeos que já posso usar (e se há direito de uso)._
"""

REQUIRED_SECTIONS = ("1.", "2.", "3.")
CONCEPT_SECTION = "7."


def scaffold(inbox):
    os.makedirs(inbox, exist_ok=True)
    for s in SLOTS:
        os.makedirs(os.path.join(inbox, s["dir"]), exist_ok=True)
    brief = os.path.join(inbox, "briefing.md")
    if not os.path.isfile(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(BRIEFING_TEMPLATE)
    return brief


def _sections(text):
    out = []
    for m in re.finditer(r"^## (.+)$", text, re.M):
        start = m.end()
        nxt = re.search(r"^## ", text[start:], re.M)
        body = text[start:start + nxt.start()] if nxt else text[start:]
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
        filled = bool(body) and "_preencher" not in body
        out.append({"title": m.group(1).strip(), "filled": filled, "body": body})
    return out


def _concept_slug(raw):
    raw = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw.strip())
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")


def requested_concepts(text):
    """Nomes de conceito pedidos na seção 7 do briefing. Lista separada por vírgula,
    ponto-e-vírgula ou linha; um marcador 'conceitos:' tem precedência. É uma pista para
    o agente no plan, não um contrato rígido — prosa longa é descartada."""
    sec = next((s for s in _sections(text) if s["title"].startswith(CONCEPT_SECTION)), None)
    if not sec or not sec["filled"]:
        return []
    body = sec["body"]
    m = re.search(r"conceitos\s*:\s*(.+)", body, re.I | re.S)
    if m:
        body = m.group(1)
    out = []
    for raw in re.split(r"[,;\n]+|\s+e\s+|\s+and\s+", body):
        raw = raw.strip()
        if not raw or "_preencher" in raw or len(raw.split()) > 3:
            continue
        slug = _concept_slug(raw)
        if slug and len(slug) <= 24 and slug not in out:
            out.append(slug)
    return out


def status(inbox):
    slots = {}
    for s in SLOTS:
        d = os.path.join(inbox, s["dir"])
        files = []
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.startswith(".") or not f.lower().endswith(s["ext"]):
                    continue
                p = os.path.join(d, f)
                files.append({"name": f, "size": os.path.getsize(p),
                              "rel": os.path.join(s["dir"], f)})
        slots[s["key"]] = {**{k: s[k] for k in ("label", "hint", "required", "multiple", "dir")},
                           "ext": list(s["ext"]), "files": files, "ok": bool(files)}
    brief = os.path.join(inbox, "briefing.md")
    text = ""
    if os.path.isfile(brief):
        with open(brief, encoding="utf-8") as f:
            text = f.read()
    sections = _sections(text)
    missing = [x["title"] for x in sections
               if not x["filled"] and x["title"].startswith(REQUIRED_SECTIONS)]
    return {"inbox": os.path.abspath(inbox), "slots": slots,
            "briefing": {"text": text, "sections": sections, "missing": missing,
                         "concepts": requested_concepts(text)},
            "ready": slots["logo"]["ok"] and not missing}