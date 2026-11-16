"""Copy Kit — skill independente de copy (só texto: PPC + overlay).

Padrão normalize: o agente gera o copy do briefing + exemplos, o kit valida a forma
e exporta só o aprovado. Independente do kit visual (não toca campaign/render/ppc).
Uma linha = um copy (destino ppc/overlay × conceito × eixo × kind).
"""

import json
import os
from datetime import datetime, timezone

DESTINATIONS = ("ppc", "overlay")
KINDS = {
    "ppc": ("headline", "description", "primary_text"),
    "overlay": ("hook", "kicker", "program", "cta"),
}
STATUSES = ("pending", "approved", "rejected", "redo")
LANGS = ("pt", "en")
ORIGINS = ("agent", "sheet")
USES = ("image", "ppc", "both")


def _path(root):
    return os.path.join(root, "copy.json")


def load(root):
    with open(_path(root), encoding="utf-8") as f:
        return json.load(f)


def save(root, data):
    with open(_path(root), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_id(rows):
    used = {r.get("id") for r in rows}
    n = 1
    while f"k{n:02d}" in used:
        n += 1
    return f"k{n:02d}"


def validate(data):
    """Erros por linha (PT — contrato do agente). Lista vazia = aplicável."""
    errs = []
    concepts = data.get("concepts") or []
    if not isinstance(concepts, list) or any(not str(c).strip() for c in concepts):
        errs.append("concepts: lista de conceitos inválida ou vazia")
    seen = set()
    for i, r in enumerate(data.get("rows") or [], 1):
        rid = r.get("id")
        if not rid:
            errs.append(f"linha {i}: id vazio")
        elif rid in seen:
            errs.append(f"linha {i}: id repetido: {rid}")
        else:
            seen.add(rid)
        dest = r.get("destination")
        if dest not in DESTINATIONS:
            errs.append(f"linha {i}: destination inválido: {dest!r} (ppc/overlay)")
        elif r.get("kind") not in KINDS[dest]:
            errs.append(f"linha {i}: kind inválido p/ {dest}: {r.get('kind')!r} "
                        f"({'/'.join(KINDS[dest])})")
        if not str(r.get("text") or "").strip():
            errs.append(f"linha {i}: text vazio")
        if concepts and r.get("concept") not in concepts:
            errs.append(f"linha {i}: conceito não declarado: {r.get('concept')!r}")
        if r.get("lang") not in LANGS:
            errs.append(f"linha {i}: lang inválido: {r.get('lang')!r} (pt/en)")
        if r.get("status") not in STATUSES:
            errs.append(f"linha {i}: status inválido: {r.get('status')!r}")
        if r.get("origin") not in ORIGINS:
            errs.append(f"linha {i}: origin inválido: {r.get('origin')!r}")
        if r.get("use", "both") not in USES:
            errs.append(f"linha {i}: use inválido: {r.get('use')!r} (image/ppc/both)")
    return errs


def decide(root, row_id, status, note="", who=""):
    """Marca uma linha (intenção). Grava status/note + carimbo. False se id desconhecido.

    redo exige nota. approve/reject limpam a nota. O agente nunca chama approved —
    decisão é do usuário na tabela.
    """
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status}")
    if status == "redo" and not str(note).strip():
        raise ValueError("redo exige uma nota (o que ajustar)")
    data = load(root)
    found = False
    for r in data.get("rows") or []:
        if r.get("id") == row_id:
            r["status"] = status
            if status == "redo":
                r["note"] = note
            else:
                r.pop("note", None)
            r["updated_at"] = now_iso()
            if who:
                r["updated_by"] = who
            found = True
            break
    if found:
        save(root, data)
    return found


def review_payload(root):
    """{rows, counts} para a tabela de revisão, ou None sem copy.json."""
    if not os.path.isfile(_path(root)):
        return None
    rows = load(root).get("rows") or []
    counts = {s: sum(1 for r in rows if r.get("status") == s) for s in STATUSES}
    return {"rows": rows, "counts": counts}


BRIEF_TEMPLATE = {
    "pt": """# Briefing de copy

## 1. Objetivo
(o que a campanha quer alcançar)

## 2. Público
(quem fala, dor/desejo)

## 3. Tom de voz
(como a marca fala — ex.: direto, próximo, técnico)

## 4. Oferta / produto
(o que se anuncia, diferencial, preço se houver)

## 5. Destinos
- PPC (só texto): Meta / Google Search
- Overlay: hook / kicker / program / CTA sobre a peça

## 6. Conceitos
(lista separada por vírgula — ex.: clean, editorial)

## 7. Eixos (opcional)
(variações — ex.: urgencia, beneficio)

## 8. Restrições
- Google RSA: headline ≤ 30 caracteres, description ≤ 90
- CTA: verbo curto
- (outras regras)

## 9. Idiomas
pt / en
""",
    "en": """# Copy briefing

## 1. Objective
(what the campaign wants to achieve)

## 2. Audience
(who you speak to, pain/desire)

## 3. Tone of voice
(how the brand speaks — e.g. direct, warm, technical)

## 4. Offer / product
(what is advertised, differentiator, price if any)

## 5. Destinations
- PPC (text only): Meta / Google Search
- Overlay: hook / kicker / program / CTA over the piece

## 6. Concepts
(comma-separated list — e.g. clean, editorial)

## 7. Axes (optional)
(variations — e.g. urgency, benefit)

## 8. Constraints
- Google RSA: headline ≤ 30 chars, description ≤ 90
- CTA: short verb
- (other rules)

## 9. Languages
pt / en
""",
}

EXAMPLES_HEADER = {
    "pt": "# Cole aqui textos de exemplo (copy que você gosta / quer usar como modelo).\n"
          "# Um por linha ou bloco. O agente usa isto + o briefing para gerar o copy.\n\n",
    "en": "# Paste example texts here (copy you like / want to use as a model).\n"
          "# One per line or block. The agent uses this + the briefing to generate copy.\n\n",
}


def scaffold(folder, lang="pt"):
    """Pasta enxuta de copy: briefing.md + examples.txt (sem logo/brandbook/refs).

    Não sobrescreve arquivos existentes. Retorna o caminho do briefing.
    """
    key = "pt" if lang == "pt" else "en"
    os.makedirs(folder, exist_ok=True)
    brief = os.path.join(folder, "briefing.md")
    if not os.path.isfile(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(BRIEF_TEMPLATE[key])
    examples = os.path.join(folder, "examples.txt")
    if not os.path.isfile(examples):
        with open(examples, "w", encoding="utf-8") as f:
            f.write(EXAMPLES_HEADER[key])
    return brief


def read_text(folder, name):
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()