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


def delivery_dir(root):
    """~/Desktop/Copy Kit/<pasta>/ — mesma convenção do visual, fora da pasta de trabalho."""
    from .campaign import desktop_dir, _slug
    name = _slug(os.path.basename(os.path.abspath(root)))
    return os.path.join(desktop_dir(), "Copy Kit", name)


OVERLAY_COLUMNS = ["Concept", "Axis", "Lang", "Hook", "Kicker", "Program", "CTA"]
MANIFEST_COLUMNS = ["ID", "Destination", "Concept", "Axis", "Kind", "Text", "Lang", "Chars"]


def _groups(rows):
    seen, out = set(), []
    for r in rows:
        key = (r.get("concept"), r.get("axis") or "", r.get("lang"))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _texts(rows, concept, axis, lang, kind):
    return [r.get("text") for r in rows
            if r.get("concept") == concept and (r.get("axis") or "") == axis
            and r.get("lang") == lang and r.get("kind") == kind]


def _adset(concept, axis):
    return " | ".join(x for x in [concept, axis] if x)


def _meta_rows(rows, name):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        head = _texts(rows, concept, axis, lang, "headline")
        prim = _texts(rows, concept, axis, lang, "primary_text")
        desc = _texts(rows, concept, axis, lang, "description")
        row = {c: "" for c in ppc.META_COLUMNS}
        row.update({"Campaign Name": name, "Campaign Status": "PAUSED",
                    "Ad Set Name": _adset(concept, axis), "Ad Set Run Status": "PAUSED",
                    "Ad Name": f"{_adset(concept, axis)} ({lang})", "Ad Status": "PAUSED",
                    "Title": ppc._trunc(head[0] if head else "", 40),
                    "Body": ppc._clean(prim[0] if prim else ""),
                    "Link Description": ppc._trunc(desc[0] if desc else "", 30)})
        out.append(row)
    return out


def _rsa_rows(rows, name):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        heads = [ppc._trunc(t, 30) for t in ppc._dedup(_texts(rows, concept, axis, lang, "headline"))]
        descs = [ppc._trunc(t, 90) for t in ppc._dedup(_texts(rows, concept, axis, lang, "description"))]
        row = {c: "" for c in ppc.RSA_COLUMNS}
        row.update({"Campaign": name, "Ad group": _adset(concept, axis),
                    "Ad type": "Responsive search ad", "Status": "Paused"})
        for i, h in enumerate(heads[:15], 1):
            row[f"Headline {i}"] = h
        for i, d in enumerate(descs[:4], 1):
            row[f"Description {i}"] = d
        out.append(row)
    return out


def _overlay_rows(rows):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        def first(kind):
            t = _texts(rows, concept, axis, lang, kind)
            return ppc._clean(t[0]) if t else ""
        out.append({"Concept": concept, "Axis": axis, "Lang": lang,
                    "Hook": first("hook"), "Kicker": first("kicker"),
                    "Program": first("program"), "CTA": first("cta")})
    return out


def _manifest_rows(rows):
    from . import ppc
    return [{"ID": r.get("id"), "Destination": r.get("destination"), "Concept": r.get("concept"),
             "Axis": r.get("axis") or "", "Kind": r.get("kind"), "Text": ppc._clean(r.get("text")),
             "Lang": r.get("lang"), "Chars": len(ppc._clean(r.get("text")))} for r in rows]


_NOTES = {
    "pt": """COPY KIT — COPY APROVADO
========================
Arquivos (cada um em CSV e XLSX):
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk (só texto).
  google_search_rsa  → Google Ads Editor / Bulk actions → Uploads. Responsive Search Ads.
  overlay            → copy sobre a peça: hook / kicker / program / CTA por conceito × eixo.
  copy_manifest      → referência humana: toda linha aprovada (destino, conceito, kind, texto, caracteres).

Só sai copy APROVADO na revisão. URL final, orçamento, targeting e IDs ficam em branco
para o time de PPC. Tudo sai PAUSED/Paused. Limites Google RSA: headline ≤ 30, description ≤ 90
(o export trunca e avisa quais linhas excederam — confira antes de importar).
""",
    "en": """COPY KIT — APPROVED COPY
========================
Files (each as CSV and XLSX):
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk (text only).
  google_search_rsa  → Google Ads Editor / Bulk actions → Uploads. Responsive Search Ads.
  overlay            → copy over the piece: hook / kicker / program / CTA per concept × axis.
  copy_manifest      → human reference: every approved row (destination, concept, kind, text, chars).

Only APPROVED copy ships. Final URL, budget, targeting and IDs are left blank for the PPC
team. Everything ships PAUSED/Paused. Google RSA limits: headline ≤ 30, description ≤ 90
(the export truncates and warns which rows exceeded — check before importing).
""",
}


def export(root, lang="pt"):
    """Exporta só as aprovadas → planilhas (Meta/RSA/overlay/manifest) na pasta Desktop.

    Determinístico; reusa os writers/colunas do ppc visual. Limites RSA viram aviso,
    não porteiro. Devolve resumo (contagens + arquivos + warnings).
    """
    from . import ppc
    rows = [r for r in load(root).get("rows") or [] if r.get("status") == "approved"]
    outdir = delivery_dir(root)
    os.makedirs(outdir, exist_ok=True)
    name = os.path.basename(os.path.abspath(root)).replace("-", " ").title()
    files, warnings = [], []
    counts = {"meta": 0, "google_rsa": 0, "overlay": 0, "manifest": 0}

    def emit(stem, columns, data, title, key):
        if not data:
            return
        ppc._write_csv(os.path.join(outdir, stem + ".csv"), columns, data)
        files.append(stem + ".csv")
        if ppc._write_xlsx(os.path.join(outdir, stem + ".xlsx"), columns, data, title):
            files.append(stem + ".xlsx")
        counts[key] = len(data)

    ppc_rows = [r for r in rows if r.get("destination") == "ppc"]
    ov_rows = [r for r in rows if r.get("destination") == "overlay"]
    for r in ppc_rows:
        limit = {"headline": 30, "description": 90}.get(r.get("kind"))
        n = len(ppc._clean(r.get("text")))
        if limit and n > limit:
            warnings.append({"id": r.get("id"), "kind": r.get("kind"), "chars": n, "limit": limit})

    emit("meta_bulk_import", ppc.META_COLUMNS, _meta_rows(ppc_rows, name), "Meta bulk import", "meta")
    emit("google_search_rsa", ppc.RSA_COLUMNS, _rsa_rows(ppc_rows, name), "Google Search RSA", "google_rsa")
    emit("overlay", OVERLAY_COLUMNS, _overlay_rows(ov_rows), "Overlay", "overlay")
    emit("copy_manifest", MANIFEST_COLUMNS, _manifest_rows(rows), "Copy manifest", "manifest")

    with open(os.path.join(outdir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(_NOTES.get(lang, _NOTES["en"]))
    files.append("README.txt")
    return {"dir": outdir, "files": files, "xlsx": ppc._HAS_XLSX, "warnings": warnings, **counts}


def deliver(root, lang="pt"):
    """O 'Continuar' do copy: exporta as aprovadas para a pasta Desktop + download."""
    empty = {"dir": delivery_dir(root), "files": [], "exported": 0, "xlsx": False,
             "warnings": [], "meta": 0, "google_rsa": 0, "overlay": 0, "manifest": 0}
    if not os.path.isfile(_path(root)):
        return empty
    approved = sum(1 for r in load(root).get("rows") or [] if r.get("status") == "approved")
    if approved == 0:
        return empty
    s = export(root, lang)
    s["exported"] = approved
    return s