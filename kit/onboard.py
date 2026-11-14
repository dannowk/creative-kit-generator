"""Onboarding: prepara a pasta que o usuário joga no agente.

Scaffold com subpastas nomeadas + briefing guiado; status diz o que falta antes do
intake rodar. O que é opcional fica dito como opcional — nunca bloqueia por capricho.
"""

import os
import re

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
FONT_EXT = (".otf", ".ttf", ".ttc")
VID_EXT = (".mp4", ".mov", ".webm", ".m4v")
DOC_EXT = (".pdf", ".docx", ".md", ".txt", ".rtf")
# Documentos de apoio do briefing: copy dos anúncios, regras de layout, safe areas,
# segurança do logo — em texto, PDF/Word, imagem (diagramas) ou planilha (tabela de copy).
BRIEF_DOC_EXT = DOC_EXT + IMG_EXT + (".csv", ".xlsx")
BRIEF_DOCS_DIR = "briefing"

SLOTS = [
    {"key": "logo", "dir": "logo", "label": "Logo", "ext": IMG_EXT, "multiple": False,
     "required": True,
     "hint": "PNG com fundo transparente, de preferência. É dele que sai a paleta proposta."},
    {"key": "refs", "dir": "refs", "label": "Referências de look", "ext": IMG_EXT, "multiple": True,
     "required": False,
     "hint": "2 a 6 imagens de anúncios/posts do look desejado. O agente olha com visão e cruza com o briefing para escrever a direção de arte."},
    {"key": "brandbook", "dir": "brandbook", "label": "Brandbook (manual da marca)",
     "ext": DOC_EXT + IMG_EXT, "multiple": True, "required": False,
     "hint": "Opcional. PDF, imagens ou docx com as regras da marca (cores, tipografia, uso do logo, voz). O agente lê com visão e segue junto com o briefing e as referências."},
    {"key": "fonts", "dir": "fonts", "label": "Fontes da marca", "ext": FONT_EXT, "multiple": True,
     "required": False,
     "hint": ".otf / .ttf. Sem elas, uso substitutas do sistema e aviso exatamente quais."},
    {"key": "photos", "dir": "photos", "label": "Fotos para as peças", "ext": IMG_EXT, "multiple": True,
     "required": False,
     "hint": "Fotos que podem virar peça. Sem elas, o provider gera — e a estimativa de custo aparece antes de gerar."},
    {"key": "videos", "dir": "videos", "label": "Vídeos", "ext": VID_EXT, "multiple": True,
     "required": False,
     "hint": "Clipes fonte ou referência de movimento. Vídeos novos são gerados pelo provider (ex. Magnific via MCP), com estimativa de custo antes de gerar."},
    {"key": "content", "dir": "content", "label": "Conteúdo base (planilha)",
     "ext": (".xlsx", ".csv"), "multiple": False, "required": False,
     "hint": "Opcional. Planilha do time de conteúdo com o copy base (colunas: concept, hook, kicker, program, cta, use). A coluna use roteia: image / ppc / both."},
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

BRIEFING_TEMPLATE_EN = """# Campaign briefing

<!-- Fill in what you know. Anything left blank becomes a single question at the end of onboarding. -->

## 1. Business and product
_fill in: what the company sells, in one sentence._

## 2. Audience
_fill in: who decides the purchase._

## 3. Goal, offer and CTA
_fill in: what the campaign should do and the button text._

## 4. Tone of voice
_fill in: how the brand speaks — and what it can never promise._

## 5. Channels
_fill in: Meta, Google, LinkedIn, print, web…_

## 6. Languages
_fill in: e.g. pt-BR, en._

## 7. Concepts (visual directions)
_fill in: how many different directions you want and the name of each, comma-separated — e.g. clean, editorial, cinema. Each concept becomes a template, a delivery folder and a review filter._

## 8. Visual direction
_fill in: what to copy from the references and what to avoid._

## 9. Compliance
_fill in: mandatory disclaimer, forbidden color, term that must not wrap._

## 10. Existing assets
_fill in: photos and videos you can already use (and whether you hold the rights)._
"""

# Marcadores de seção não preenchida (PT/EN) — o parser de conceitos e o status usam.
_UNFILLED = ("_preencher", "_fill in")

REQUIRED_SECTIONS = ("1.", "2.", "3.")
CONCEPT_SECTION = "7."


def scaffold(inbox, lang="pt"):
    os.makedirs(inbox, exist_ok=True)
    for s in SLOTS:
        os.makedirs(os.path.join(inbox, s["dir"]), exist_ok=True)
    os.makedirs(os.path.join(inbox, BRIEF_DOCS_DIR), exist_ok=True)
    brief = os.path.join(inbox, "briefing.md")
    if not os.path.isfile(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(BRIEFING_TEMPLATE_EN if lang != "pt" else BRIEFING_TEMPLATE)
    return brief


def _sections(text):
    out = []
    for m in re.finditer(r"^## (.+)$", text, re.M):
        start = m.end()
        nxt = re.search(r"^## ", text[start:], re.M)
        body = text[start:start + nxt.start()] if nxt else text[start:]
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
        filled = bool(body) and not any(p in body for p in _UNFILLED)
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
        if not raw or any(p in raw for p in _UNFILLED) or len(raw.split()) > 3:
            continue
        slug = _concept_slug(raw)
        if slug and len(slug) <= 24 and slug not in out:
            out.append(slug)
    return out


def status(inbox, lang="pt"):
    from . import i18n
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
        if lang != "pt":
            slots[s["key"]]["label"] = i18n.t(f"slot.{s['key']}.label", lang)
            slots[s["key"]]["hint"] = i18n.t(f"slot.{s['key']}.hint", lang)
    brief = os.path.join(inbox, "briefing.md")
    text = ""
    if os.path.isfile(brief):
        with open(brief, encoding="utf-8") as f:
            text = f.read()
    # Template intacto → mostra no idioma da UI; conteúdo preenchido nunca é traduzido.
    if text.strip() == BRIEFING_TEMPLATE.strip() and lang != "pt":
        text = BRIEFING_TEMPLATE_EN
    elif text.strip() == BRIEFING_TEMPLATE_EN.strip() and lang == "pt":
        text = BRIEFING_TEMPLATE
    sections = _sections(text)
    missing = [x["title"] for x in sections
               if not x["filled"] and x["title"].startswith(REQUIRED_SECTIONS)]
    docs_dir = os.path.join(inbox, BRIEF_DOCS_DIR)
    docs = []
    if os.path.isdir(docs_dir):
        for f in sorted(os.listdir(docs_dir)):
            if f.startswith(".") or not f.lower().endswith(BRIEF_DOC_EXT):
                continue
            p = os.path.join(docs_dir, f)
            docs.append({"name": f, "size": os.path.getsize(p),
                         "rel": os.path.join(BRIEF_DOCS_DIR, f)})
    link_path = os.path.join(inbox, "content_link.txt")
    content_link = ""
    if os.path.isfile(link_path):
        with open(link_path, encoding="utf-8") as f:
            content_link = f.read().strip()
    return {"inbox": os.path.abspath(inbox), "slots": slots,
            "briefing": {"text": text, "sections": sections, "missing": missing,
                         "concepts": requested_concepts(text)},
            "briefing_docs": docs,
            "content_link": content_link,
            "ready": slots["logo"]["ok"] and not missing}