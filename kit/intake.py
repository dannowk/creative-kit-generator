"""Intake: a pasta que o usuário jogou vira uma marca proposta + a lista do que faltou.

O que é inferível com confiança (paleta do logo, centro do sujeito, inventário) é derivado aqui.
O que não é (fonte exata, compliance, canais, voz) vira pergunta em lote — nunca chute silencioso.
"""

import glob
import json
import os
import shutil

import numpy as np
import yaml
from PIL import Image

from . import primitives as P
from .onboard import VID_EXT, requested_concepts

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
FONT_EXT = (".otf", ".ttf", ".ttc")
BRIEF_EXT = (".md", ".txt", ".docx", ".pdf", ".rtf")


def inventory(inbox):
    found = {"logo": None, "refs": [], "fonts": [], "briefs": [],
             "photos": [], "videos": [], "other": []}
    for root, _, files in os.walk(inbox):
        for f in sorted(files):
            if f.startswith("."):
                continue
            p = os.path.join(root, f)
            low = f.lower()
            rel = os.path.relpath(p, inbox)
            top = rel.split(os.sep)[0].lower() if os.sep in rel else ""
            if low.endswith(VID_EXT):
                found["videos"].append(p)
            elif low.endswith(FONT_EXT):
                found["fonts"].append(p)
            elif low.endswith(BRIEF_EXT):
                found["briefs"].append(p)
            elif low.endswith(IMG_EXT):
                if top == "logo" and found["logo"] is None:
                    found["logo"] = p
                elif top == "photos":
                    found["photos"].append(p)
                elif top == "refs":
                    found["refs"].append(p)
                elif "logo" in low and found["logo"] is None:
                    found["logo"] = p
                else:
                    found["refs"].append(p)
            else:
                found["other"].append(p)
    if found["logo"] is None and found["refs"]:
        # sem arquivo chamado logo: o PNG com alfa é o candidato mais provável
        for p in found["refs"]:
            if p.lower().endswith(".png") and Image.open(p).mode in ("RGBA", "LA", "PA"):
                found["logo"] = p
                found["refs"].remove(p)
                break
    return found


def _sat(rgb):
    mx, mn = max(rgb), min(rgb)
    return (mx - mn) / mx if mx else 0


def extract_palette(logo_path):
    """Clusters de cor dos pixels opacos do logo. Proposta, não verdade — o designer confirma."""
    img = Image.open(logo_path).convert("RGBA")
    a = np.asarray(img)
    opaque = a[a[..., 3] > 200][:, :3]
    if len(opaque) == 0:
        return {}
    binned = (opaque // 24 * 24 + 12)
    keys, counts = np.unique(binned, axis=0, return_counts=True)
    order = np.argsort(-counts)
    clusters = [(tuple(int(c) for c in keys[i]), int(counts[i])) for i in order[:10]]
    non_white = [(c, n) for c, n in clusters if not all(v > 235 for v in c)]
    if not non_white:
        return {}
    primary = non_white[0][0]
    saturated = [(c, n) for c, n in non_white if _sat(c) > 0.35 and c != primary]
    accent = max(saturated, key=lambda cn: _sat(cn[0]) * cn[1])[0] if saturated else primary
    ink = min((c for c, _ in non_white), key=sum)
    paper = next((c for c, _ in clusters if all(v > 235 for v in c)), (244, 239, 230))
    dark = tuple(max(4, round(c * 0.10)) for c in primary)
    return {"primary": primary, "accent": accent, "ink": ink, "paper": paper, "dark": dark}


def _hex(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def propose_fonts(font_files):
    """Heurística por nome de arquivo. Se ambígua, o intake reporta e pergunta."""
    def has(name, *words):
        return any(w in name for w in words)

    names = {os.path.basename(p): p for p in font_files}
    accent = next((n for n in names if has(n.lower(), "ita") and has(n.lower(), "black", "extra", "heavy", "bold")), None)
    display = next((n for n in names if has(n.lower(), "bold", "black") and not has(n.lower(), "ita")), None)
    text = next((n for n in names if has(n.lower(), "regular", "medium", "book", "light")), None) \
        or next((n for n in names if has(n.lower(), "bold") and not has(n.lower(), "ita")), None)
    cfg = {}
    if display:
        cfg["display"] = {"file": display}
    if accent:
        cfg["accent"] = {"file": accent}
    if text:
        cfg["text"] = {"file": text}
    return cfg


def subject_map(refs):
    return {os.path.basename(p): round(P.subject_center(Image.open(p).convert("RGB")), 4) for p in refs}


def run(inbox, brand_id, brands_dir):
    """Cria brands/<id>/ com brand.yaml proposto, assets e fontes. Devolve (resumo, gaps)."""
    inv = inventory(inbox)
    root = os.path.join(brands_dir, brand_id)
    os.makedirs(os.path.join(root, "assets"), exist_ok=True)
    gaps = []

    if inv["logo"]:
        shutil.copy(inv["logo"], os.path.join(root, "assets", "logo.png"))
        palette = extract_palette(inv["logo"])
    else:
        palette = {}
        gaps.append({"field": "logo", "question": "Qual arquivo é o logo da marca?",
                     "why": "Sem logo não há paleta nem assinatura nas peças."})

    if inv["fonts"]:
        os.makedirs(os.path.join(root, "fontes"), exist_ok=True)
        for p in inv["fonts"]:
            shutil.copy(p, os.path.join(root, "fontes", os.path.basename(p)))
        type_cfg = propose_fonts(inv["fonts"])
        if not type_cfg.get("display") or not type_cfg.get("accent"):
            gaps.append({"field": "type", "question": "Qual fonte é o título e qual é o destaque (itálico pesado)?",
                         "why": "Não se identifica tipografia com confiança só pelo nome do arquivo."})
    else:
        type_cfg = {}
        gaps.append({"field": "type", "question": "Pode jogar os arquivos de fonte (.otf/.ttf) na pasta? Se não, uso uma substituta do sistema.",
                     "why": "Fonte da marca não é inferível de imagens; sem ela o resultado não é fiel."})

    brand_name = brand_id.replace("-", " ").title()
    data = {
        "id": brand_id,
        "name": brand_name,
        "locale_default": "en",
        "locales": ["en"],
        "palette": {k: _hex(v) for k, v in palette.items()} if palette else {},
        "type": type_cfg,
        "logo": {"file": "assets/logo.png", "scale": 0.30},
        "voice": {"tone": "", "highlight": "[ ]", "language": "en"},
        "axes": [],
        "naming": "{slug}_{concept}_{size}",
        "compliance": [
            {"check": "subject_safe", "tolerance": 0.02},
            {"check": "min_font_size", "scale": 0.018},
            {"check": "contrast_min", "ratio": 3.0},
        ],
    }
    if palette:
        data["compliance"].append({"check": "palette_forbidden", "tolerance": 40, "min_area": 0.005})
        data["palette"]["forbidden"] = []

    gaps.append({"field": "voice", "question": "Qual o tom de voz e o que a marca nunca pode prometer?",
                 "why": "Voz e restrições de copy vêm do briefing, não dos pixels."})
    gaps.append({"field": "compliance", "question": "Há disclaimer obrigatório, cor proibida ou termo que não pode quebrar linha?",
                 "why": "Regra de compliance não é inferível; em educação/saúde/financeiro é onde mora o risco."})
    gaps.append({"field": "channels", "question": "Onde a campanha veicula (Meta, Google, LinkedIn, impresso, web)?",
                 "why": "Os aspect ratios e safe zones dependem do canal."})
    if not inv["photos"] and not inv["videos"]:
        gaps.append({"field": "assets", "question": "Tem fotos próprias para as peças ou gero com o provider? (mostro a estimativa de custo antes)",
                     "why": "Sem foto na pasta, a imagem sai de geração paga — o aviso de ≈ créditos aparece antes de gerar."})

    brief_text = ""
    primary = next((b for b in inv["briefs"] if os.path.basename(b).lower() == "briefing.md"), None) \
        or next((b for b in inv["briefs"] if b.lower().endswith((".md", ".txt"))), None)
    if primary:
        try:
            with open(primary, encoding="utf-8") as f:
                brief_text = f.read()
        except OSError:
            brief_text = ""
    concepts_req = requested_concepts(brief_text)
    if not concepts_req:
        gaps.append({"field": "concepts",
                     "question": "Quantas direções visuais (conceitos) você quer? Liste os nomes — ex.: clean, editorial, cinema.",
                     "why": "Cada conceito vira um template, uma pasta de entrega e um filtro na revisão."})

    with open(os.path.join(root, "brand.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    subjects = subject_map(inv["refs"] + inv["photos"])
    summary = {"brand": brand_id, "root": root, "logo": bool(inv["logo"]),
               "palette": {k: _hex(v) for k, v in palette.items()},
               "refs": inv["refs"], "ref_count": len(inv["refs"]),
               "photos": inv["photos"], "videos": inv["videos"],
               "fonts": len(inv["fonts"]),
               "briefs": inv["briefs"], "subjects": subjects, "gaps": gaps,
               "concepts_requested": concepts_req,
               "reference_analysis": {"composition": "", "mood": "", "type": "",
                                      "texture": "", "layout": "", "must_avoid": ""}}
    with open(os.path.join(root, "intake.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary, gaps