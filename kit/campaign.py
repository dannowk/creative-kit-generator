"""Campanha: briefing estruturado -> matriz de peças em pastas distintas.

Os eixos (produto, região, público, idioma) substituem o regions×programs chumbado:
o produto cartesiano e o nome do arquivo vêm do brand.yaml, não do código.
"""

import itertools
import json
import os
import glob
import shutil

from PIL import Image

from . import compliance, formats, primitives as P, render
from .brand import load_brand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT, "templates")


def load_campaign(path):
    if os.path.isdir(path):
        path = os.path.join(path, "campaign.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["_root"] = os.path.dirname(os.path.abspath(path))
    return data


def brand_for(campaign, brands_dir=None):
    brands_dir = brands_dir or os.path.join(ROOT, "brands")
    return load_brand(os.path.join(brands_dir, campaign["brand"]))


def expand_axes(brand, campaign):
    """Produto cartesiano dos eixos declarados no briefing (ou os da marca, se omitidos)."""
    declared = campaign.get("axes")
    if declared:
        names = list(declared)
        values = [declared[n] for n in names]
    else:
        specs = brand.axes
        names = [a["name"] for a in specs]
        values = [brand.axis_values(a) for a in specs]
    names = [n for n, v in zip(names, values) if v]
    values = [v for v in values if v]
    if not names:
        return [{}]
    return [dict(zip(names, combo)) for combo in itertools.product(*values)]


def lookup(mapping, combo):
    """Aceita chave pelo combo inteiro ('BC|Course-02'), por valor isolado, ou 'default'."""
    if not mapping:
        return None
    joined = "|".join(str(combo[k]) for k in sorted(combo))
    for key in (joined, *combo.values(), "default"):
        if key in mapping:
            return mapping[key]
    return None


def piece_name(brand, campaign, combo, concept, format_name, n=1):
    fields = {"slug": campaign.get("slug", "campaign"), "concept": concept,
              "size": formats.label(format_name), "format": format_name,
              "n": n, "V": f"V{n}", "brand": brand.id,
              "locale": combo.get("locale", campaign.get("locale", brand.locale_default))}
    fields.update(combo)
    pattern = campaign.get("naming") or brand.naming
    return pattern.format_map(_Safe(fields))


class _Safe(dict):
    def __missing__(self, key):
        return key


def load_subject_overrides(campaign):
    """Substitui a tabela de rostos medidos à mão: o intake/agente grava o centro por arquivo."""
    p = os.path.join(campaign["_root"], "assets", "subject.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def resolve_asset(campaign, combo, overrides):
    rel = lookup(campaign.get("assets"), combo)
    if not rel:
        return None, 0.5, None
    path = rel if os.path.isabs(rel) else os.path.join(campaign["_root"], rel)
    if not os.path.isfile(path):
        matches = glob.glob(path)
        if not matches:
            return None, 0.5, path
        path = sorted(matches)[0]
    base = os.path.basename(path)
    fx = overrides.get(base)
    img = Image.open(path).convert("RGB")
    if fx is None:
        fx = P.subject_center(img)
    return img, fx, path


def available_concepts():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(TEMPLATES_DIR, "*.yaml")))


def _spec_path(campaign, concept):
    """Spec da campanha vence a biblioteca global: a direção de arte vem do briefing
    e das referências desta campanha, não do acervo de outra marca."""
    local = os.path.join(campaign["_root"], "templates", f"{concept}.yaml")
    return local if os.path.isfile(local) else os.path.join(TEMPLATES_DIR, f"{concept}.yaml")


def run(campaign, brand=None, only_concepts=None, only_formats=None, limit=None, dry=False,
        only_ids=None):
    """Renderiza a matriz inteira. Devolve o estado que a UI local consome.

    `only_ids` restringe a peça(s) exata(s) — usado na etapa 6 para o agente recriar só
    as rejeitadas/refazer. As decisões anteriores (aprovadas/entregues) são preservadas
    no merge; peças re-renderizadas voltam a `pending` para nova revisão.
    """
    brand = brand or brand_for(campaign)
    root = campaign["_root"]
    out_dir = os.path.join(root, "out")
    names, unknown = formats.resolve_formats(campaign.get("channels", []), campaign.get("formats", []))
    if unknown:
        raise ValueError(f"Formato/canal desconhecido: {', '.join(unknown)}")
    if only_formats:
        names = [n for n in names if n in only_formats]
    concepts = only_concepts or campaign.get("concepts") or available_concepts()
    specs = {c: render.load_spec(_spec_path(campaign, c)) for c in concepts}

    combos = expand_axes(brand, campaign)
    overrides = load_subject_overrides(campaign)
    logo = Image.open(brand.logo_path).convert("RGBA") if brand.logo_path else None
    copy_map = campaign.get("copy") or {}

    pieces = []
    for combo in combos:
        photo, fx, asset_path = resolve_asset(campaign, combo, overrides)
        copy = lookup(copy_map, combo) or {}
        if isinstance(copy, str):
            copy = {"hook": copy}
        extra = {"program": copy.get("program") or lookup(campaign.get("labels"), combo) or "",
                 "campus": copy.get("campus", campaign.get("campus", "")),
                 "cta": copy.get("cta", campaign.get("cta", "Learn more")),
                 "brand_name": brand.name}
        for concept in concepts:
            spec = specs[concept]
            if spec.get("needs_photo") and photo is None:
                continue
            voice = copy.get(concept)
            merged = {**copy, **voice} if isinstance(voice, dict) else copy
            if not merged.get("hook"):
                print(f"  sem copy.hook para {concept} em {combo or 'campanha'} — conceito pulado")
                continue
            for fmt in names:
                name = piece_name(brand, campaign, combo, concept, fmt)
                if only_ids and name not in only_ids:
                    continue
                geo = formats.geometry(fmt, brand)
                if geo["tight"] and spec.get("needs_photo") and "tight" not in (spec.get("variants") or {}):
                    continue
                trace = {}
                img = render.render(spec, brand, geo, photo=photo, fx=fx, logo=logo,
                                    copy=merged, extra=extra, trace=trace)
                findings = compliance.run(img, trace, brand)
                rel = os.path.join(concept, f"{name}.png")
                entry = {"id": name, "path": rel, "concept": concept, "format": fmt,
                         "axes": combo, "asset": os.path.basename(asset_path) if asset_path else None,
                         "subject_fx": round(fx, 4), "findings": findings,
                         "status": "blocked" if compliance.blocked(findings) else "pending"}
                if not dry:
                    dest = os.path.join(out_dir, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    img.save(dest, "PNG", optimize=True)
                    thumb_dir = os.path.join(root, "review", "thumbs", concept)
                    os.makedirs(thumb_dir, exist_ok=True)
                    img.resize((max(1, round(img.width * 360 / img.height)), 360),
                               P.LANCZOS).save(os.path.join(thumb_dir, f"{name}.png"))
                pieces.append(entry)
                if limit and len(pieces) >= limit:
                    break
            if limit and len(pieces) >= limit:
                break
        if limit and len(pieces) >= limit:
            break

    if not dry:
        pieces = _merge_prior(root, pieces)
        _sheets(root, out_dir, pieces)
    state = {"campaign": campaign.get("slug"), "brand": brand.id, "root": root,
             "formats": names, "concepts": concepts, "pieces": pieces,
             "blocked_count": sum(1 for p in pieces if p.get("status") == "blocked"),
             "font_warnings": {"missing": brand.fonts.missing, "substituted": brand.fonts.substituted}}
    if not dry:
        with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    return state


def _merge_prior(root, pieces):
    """Preserva as decisões da revisão ao re-renderizar (etapa 6).

    Aprovadas/entregues continuam aprovadas; peças fora do conjunto re-renderizado são
    mantidas intactas; as re-renderizadas (rejeitadas/refazer recriadas) voltam a pending
    sem `note`/`queued`, para nova revisão na mesma página.
    """
    prior_path = os.path.join(root, "state.json")
    if not os.path.isfile(prior_path):
        return pieces
    with open(prior_path, encoding="utf-8") as f:
        prior = {p["id"]: p for p in json.load(f).get("pieces", [])}
    rendered = {p["id"] for p in pieces}
    for p in pieces:
        old = prior.get(p["id"])
        if old and old.get("status") == "approved":
            p["status"] = "approved"
            if old.get("delivered"):
                p["delivered"] = True
            if old.get("delivery_path"):
                p["delivery_path"] = old["delivery_path"]
    for pid, old in prior.items():
        if pid not in rendered:
            pieces.append(old)
    return pieces


def deliver(root, lang="pt"):
    """Etapa 6 — o botão Continuar: exporta as aprovadas e enfileira a recriação/refazer.

    Local e imediato: copia as aprovadas de `out/` para `delivery/<conceito>/` e marca
    `delivered`. As rejeitadas (recriar) e refazer (com a nota) viram um lote em
    `requests.json` — a regeneração é do agente (o render é determinístico; a UI não
    chama MCP). O agente recria/refaz, roda `render --ids` e a revisão atualiza sozinha.
    Com as aprovadas exportadas, gera também as planilhas de bulk upload de PPC
    (Meta + Google) em `delivery/ppc/`.
    """
    with open(os.path.join(root, "state.json"), encoding="utf-8") as f:
        state = json.load(f)
    delivery = os.path.join(root, "delivery")
    exported, batch = [], []
    for p in state["pieces"]:
        st = p.get("status")
        if st == "approved":
            src = os.path.join(root, "out", p["path"])
            if os.path.isfile(src):
                dest = os.path.join(delivery, p["concept"], os.path.basename(p["path"]))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                p["delivered"] = True
                p["delivery_path"] = os.path.relpath(dest, root)
                exported.append(p["id"])
        elif st in ("rejected", "redo"):
            p["queued"] = True
            batch.append({"id": p["id"], "concept": p["concept"], "format": p["format"],
                          "axes": p.get("axes", {}), "path": p["path"],
                          "kind": p.get("kind", "image"), "asset": p.get("asset"),
                          "reason": "redo" if st == "redo" else "rejected",
                          "note": p.get("note", "")})
    with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    with open(os.path.join(root, "requests.json"), "w", encoding="utf-8") as f:
        json.dump(batch, f, indent=2, ensure_ascii=False)
    ppc_summary = None
    if exported:
        from . import ppc
        ppc_summary = ppc.export(root, lang=lang)
    return {"exported": len(exported), "regen": len(batch), "exported_ids": exported,
            "delivery_dir": "delivery", "requests_path": "requests.json", "batch": batch,
            "ppc": ppc_summary}


def _sheets(root, out_dir, pieces):
    by_key = {}
    for p in pieces:
        axis = "|".join(str(v) for v in p["axes"].values())
        by_key.setdefault((p["concept"], axis), []).append(p)
    review = os.path.join(root, "review")
    os.makedirs(review, exist_ok=True)
    for (concept, axis), group in by_key.items():
        paths = [os.path.join(out_dir, p["path"]) for p in group
                 if os.path.isfile(os.path.join(out_dir, p["path"]))]
        if paths:
            suffix = f"_{_slug(axis)}" if axis else ""
            P.contact_sheet(paths, os.path.join(review, f"sheet_{_slug(concept)}{suffix}.png"), cols=4)


def _slug(text):
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in str(text)).strip("-")[:80]