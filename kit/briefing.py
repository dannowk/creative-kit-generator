"""Briefing canônico: schema -> validate -> apply.

O briefing.schema.yaml é a fonte única: daqui saem as perguntas de gap (rodada
única, como no intake), os erros estruturais e o template markdown. O apply é
determinístico: escreve brands/<id>/brand.yaml e campaigns/<marca>-<slug>/campaign.json
(bloco video incluso) e copia os assets declarados. Nada de inferência silenciosa:
o que não é derivável com confiança (paleta do logo) é marcado como proposta.
"""

import json
import os
import re
import shutil

import yaml

from . import formats
from .intake import extract_palette

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "briefing.schema.yaml")
HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load(path):
    with open(path, encoding="utf-8") as f:
        if path.lower().endswith(".json"):
            return json.load(f)
        return yaml.safe_load(f) or {}


def _slug(text, limit=40):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:limit]


def _get(struct, dotted):
    cur = struct
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _empty(v):
    return v is None or v == "" or v == [] or v == {} or (isinstance(v, str) and not v.strip())


def _hex(v):
    return "#" + str(v).lstrip("#").upper()


def _fields(schema):
    for sec, body in schema["secoes"].items():
        for key, meta in body["campos"].items():
            yield f"{sec}.{key}", meta


def validate(struct, base_dir=None):
    """Gaps (required/optional, rodada única) + erros estruturais. ok = aplicável."""
    schema = load_schema()
    gaps, errors = [], []

    def err(field, msg):
        errors.append({"field": field, "message": msg})

    if not isinstance(struct, dict):
        return {"ok": False, "gaps": [], "errors": [{"field": "$", "message": "briefing não é um mapa YAML/JSON"}]}

    for sec in struct:
        if sec not in schema["secoes"]:
            err(sec, f"seção desconhecida (válidas: {', '.join(schema['secoes'])})")

    concepts_raw = _get(struct, "campanha.conceitos") or []
    concepts = [_slug(c, 24) for c in concepts_raw if not _empty(c)]
    copy = _get(struct, "campanha.copy") or {}
    copy_keys = {_slug(k, 24): v for k, v in copy.items()} if isinstance(copy, dict) else {}

    for field, meta in _fields(schema):
        v = _get(struct, field)
        tipo = meta["tipo"]
        if _empty(v):
            if meta.get("obrigatorio"):
                gaps.append({"field": field, "question": meta["pergunta"],
                             "why": meta["porque"], "required": True})
            elif meta.get("perguntar_se_ausente"):
                gaps.append({"field": field, "question": meta["pergunta"],
                             "why": meta["porque"], "required": False})
            continue

        if tipo == "texto" and not isinstance(v, str):
            err(field, "esperava texto")
        elif tipo == "numero":
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                err(field, "esperava número")
            elif field == "compliance.tolerancia_rosto" and not 0 <= v <= 1:
                err(field, "tolerância deve estar entre 0 e 1")
        elif tipo == "enum":
            if v not in meta["valores"]:
                err(field, f"valor '{v}' inválido (use: {', '.join(meta['valores'])})")
        elif tipo in ("lista", "lista_hex", "lista_arquivos"):
            if not isinstance(v, list):
                err(field, "esperava lista")
            elif tipo == "lista_hex":
                for c in v:
                    if not HEX_RE.match(str(c)):
                        err(field, f"cor inválida: {c} (use #RRGGBB)")
        elif tipo == "mapa_hex":
            if not isinstance(v, dict):
                err(field, "esperava mapa de cores")
            else:
                for k, c in v.items():
                    if k not in meta["chaves"]:
                        err(field, f"chave de cor desconhecida: {k} (use: {', '.join(meta['chaves'])})")
                    elif not HEX_RE.match(str(c)):
                        err(field, f"cor inválida em {k}: {c}")
        elif tipo == "mapa_arquivos":
            if not isinstance(v, dict):
                err(field, "esperava mapa papel -> arquivo")
            else:
                for k in v:
                    if k not in meta["chaves"]:
                        err(field, f"papel de fonte desconhecido: {k} (use: {', '.join(meta['chaves'])})")
        elif tipo == "mapa_listas":
            if not isinstance(v, dict) or any(not isinstance(x, list) or not x for x in v.values()):
                err(field, "esperava mapa de listas não-vazias (ex.: produto: [A, B])")
        elif tipo == "mapa_duracoes":
            if not isinstance(v, dict):
                err(field, "esperava mapa formato -> segundos")
            else:
                for k, s in v.items():
                    if k != "default" and k not in formats.FORMATS:
                        err(field, f"formato desconhecido em duracoes: {k}")
                    elif not isinstance(s, (int, float)) or s <= 0:
                        err(field, f"duração inválida em {k}: {s}")
        elif tipo == "copy_por_conceito":
            if not isinstance(v, dict):
                err(field, "esperava mapa conceito -> {hook, kicker}")
            else:
                for k in v:
                    if _slug(k, 24) not in concepts and concepts:
                        err(field, f"copy para conceito não declarado: {k}")
        elif tipo == "lista_segmentos":
            if not isinstance(v, list):
                err(field, "esperava lista de segmentos")
            else:
                for s in v:
                    if not isinstance(s, dict) or not all(k in s for k in ("start", "end", "text")):
                        err(field, "segmento precisa de start, end e text")
                        break

        if tipo in ("arquivo", "lista_arquivos", "mapa_arquivos") and base_dir:
            paths = [v] if tipo == "arquivo" else (v if tipo == "lista_arquivos" else list(v.values()))
            for p in paths:
                if isinstance(p, str) and not os.path.isfile(os.path.join(base_dir, os.path.expanduser(p))):
                    err(field, f"arquivo não encontrado: {p}")

    canais = _get(struct, "campanha.canais") or []
    if isinstance(canais, list):
        for c in canais:
            if c not in formats.BUNDLES and c not in formats.FORMATS:
                err("campanha.canais", f"canal/formato desconhecido: {c}")

    for c in concepts:
        entry = copy_keys.get(c) or {}
        if not isinstance(entry, dict) or _empty(entry.get("hook")):
            gaps.append({"field": f"campanha.copy.{c}.hook",
                         "question": f"Qual o hook (chamada) do conceito '{c}'?",
                         "why": "Sem copy.hook por conceito o render pula o conceito.",
                         "required": True})

    video_present = any(not _empty(_get(struct, f"video.{k}"))
                        for k in ("fonte", "concat", "duracoes", "legendas", "segmentos", "formatos"))
    if video_present and _empty(_get(struct, "video.fonte")) and _empty(_get(struct, "video.concat")):
        gaps.append({"field": "video.fonte",
                     "question": "A seção vídeo foi preenchida mas sem fonte: qual arquivo (ou concat) edito?",
                     "why": "Trim/reframe/overlay precisam de um vídeo-fonte local.", "required": True})
    if _get(struct, "video.legendas") == "manual" and _empty(_get(struct, "video.segmentos")):
        gaps.append({"field": "video.segmentos",
                     "question": "Legendas manuais: quais os segmentos ({start, end, text})?",
                     "why": "Não invento texto falado; legenda manual precisa das janelas de tempo.",
                     "required": True})
    if _get(struct, "provider.nome") == "http" and _empty(_get(struct, "provider.api_url")):
        gaps.append({"field": "provider.api_url",
                     "question": "Provider http: qual a URL da API?",
                     "why": "Sem URL não há contrato de geração.", "required": True})

    return {"ok": not errors and not any(g["required"] for g in gaps),
            "gaps": gaps, "errors": errors}


def _copy_file(src, base_dir, dest_dir, name=None):
    src = os.path.join(base_dir, os.path.expanduser(src))
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name or os.path.basename(src))
    if os.path.abspath(src) != os.path.abspath(dest):
        shutil.copy(src, dest)
    return os.path.basename(dest)


def apply(struct, base_dir, root=ROOT):
    """Escreve brand.yaml + campaign.json (e o briefing de proveniência). Determinístico."""
    v = validate(struct, base_dir)
    if not v["ok"]:
        raise ValueError("briefing não aplicável: " +
                         "; ".join([f"[{e['field']}] {e['message']}" for e in v["errors"]] +
                                   [f"[{g['field']}] {g['question']}" for g in v["gaps"] if g["required"]]))

    marca, camp = struct["marca"], struct["campanha"]
    brand_id = _slug(marca["nome"])
    brand_root = os.path.join(root, "brands", brand_id)
    assets_dir = os.path.join(brand_root, "assets")

    logo_name = _copy_file(marca["logo"], base_dir, assets_dir, "logo.png")
    declared = marca.get("paleta") or {}
    palette = {k: _hex(c) for k, c in declared.items()}
    proposed = False
    if not palette:
        palette = {k: "#%02X%02X%02X" % tuple(rgb)
                   for k, rgb in extract_palette(os.path.join(assets_dir, logo_name)).items()}
        proposed = True
    forbidden = [_hex(c) for c in (struct.get("compliance") or {}).get("cores_proibidas") or []]
    if palette:
        palette["forbidden"] = forbidden

    type_cfg = {}
    for role, path in (marca.get("fontes") or {}).items():
        fname = _copy_file(path, base_dir, os.path.join(brand_root, "fontes"))
        type_cfg[role] = {"file": fname}

    idiomas = marca.get("idiomas") or ["en"]
    comp = struct.get("compliance") or {}
    checks = [
        {"check": "subject_safe", "tolerance": comp.get("tolerancia_rosto", 0.02)},
        {"check": "min_font_size", "scale": 0.018},
        {"check": "contrast_min", "ratio": 3.0},
    ]
    if comp.get("disclaimer"):
        checks.append({"check": "disclaimer_required", "text": comp["disclaimer"]})
    if comp.get("nobreak"):
        checks.append({"check": "nobreak", "text": comp["nobreak"]})
    if palette and forbidden:
        checks.append({"check": "palette_forbidden", "tolerance": 40, "min_area": 0.005})

    voice = marca.get("voz") or {}
    brand = {
        "id": brand_id, "name": marca["nome"],
        "locale_default": idiomas[0], "locales": idiomas,
        "palette": palette, "type": type_cfg,
        "logo": {"file": f"assets/{logo_name}", "scale": 0.30},
        "voice": {"tone": voice.get("tom", ""), "highlight": "[ ]",
                  "language": idiomas[0].split("-")[0],
                  "never_promise": voice.get("nunca_prometer") or []},
        "axes": [], "naming": "{slug}_{concept}_{size}",
        "compliance": checks,
    }
    os.makedirs(brand_root, exist_ok=True)
    with open(os.path.join(brand_root, "brand.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(brand, f, sort_keys=False, allow_unicode=True)

    slug = _slug(camp.get("slug") or camp["objetivo"]) or "campanha"
    camp_id = f"{brand_id}-{slug}"
    camp_root = os.path.join(root, "campaigns", camp_id)
    cassets = os.path.join(camp_root, "assets")

    concepts = [_slug(c, 24) for c in camp["conceitos"]]
    copy_in = {_slug(k, 24): v for k, v in (camp.get("copy") or {}).items()}
    default_copy = {}
    for c in concepts:
        entry = dict(copy_in.get(c) or {})
        default_copy[c] = entry
        default_copy.setdefault("hook", entry.get("hook"))
        if entry.get("kicker"):
            default_copy.setdefault("kicker", entry["kicker"])
    if camp.get("oferta"):
        default_copy.setdefault("kicker", camp["oferta"])

    channels = [c for c in camp["canais"] if c in formats.BUNDLES]
    explicit = [c for c in camp["canais"] if c in formats.FORMATS]
    assets_map = {}
    fotos = (struct.get("assets") or {}).get("fotos") or []
    copied_fotos = [_copy_file(p, base_dir, cassets) for p in fotos]
    if copied_fotos:
        assets_map["default"] = f"assets/{copied_fotos[0]}"
    for p in (struct.get("assets") or {}).get("refs") or []:
        _copy_file(p, base_dir, os.path.join(camp_root, "refs"))
    copied_videos = [_copy_file(p, base_dir, cassets) for p in (struct.get("assets") or {}).get("videos") or []]

    campaign = {
        "brand": brand_id, "slug": slug,
        "channels": channels, "concepts": concepts,
        "cta": camp["cta"], "copy": {"default": default_copy},
        "objetivo": camp["objetivo"],
    }
    if explicit:
        campaign["formats"] = explicit
    if camp.get("eixos"):
        campaign["axes"] = camp["eixos"]
    if assets_map:
        campaign["assets"] = assets_map

    vid = struct.get("video") or {}
    video_copies = 0
    if vid.get("fonte") or vid.get("concat"):
        block = {}
        if vid.get("concat"):
            names = [_copy_file(p, base_dir, cassets) for p in vid["concat"]]
            block["concat"] = [f"assets/{n}" for n in names]
            video_copies = len(names)
        else:
            src = vid["fonte"]
            name = os.path.basename(src)
            if name not in copied_videos:
                name = _copy_file(src, base_dir, cassets)
                video_copies = 1
            block["source"] = f"assets/{name}"
        if vid.get("duracoes"):
            block["durations"] = vid["duracoes"]
        legendas = vid.get("legendas", "off")
        block["captions"] = vid.get("segmentos") if legendas == "manual" else legendas
        block["language"] = idiomas[0].split("-")[0]
        if vid.get("formatos"):
            block["formats"] = vid["formatos"]
        campaign["video"] = block

    prov = struct.get("provider") or {}
    pcfg = {"name": prov.get("nome", "manual"),
            "credits_per_image": prov.get("creditos_imagem", 0),
            "credits_per_video": prov.get("creditos_video", 0)}
    if prov.get("drop_dir"):
        pcfg["drop_dir"] = prov["drop_dir"]
    if prov.get("api_url"):
        pcfg["api_url"] = prov["api_url"]
    if prov.get("api_key_env"):
        pcfg["api_key_env"] = prov["api_key_env"]
    campaign["provider"] = pcfg

    os.makedirs(camp_root, exist_ok=True)
    with open(os.path.join(camp_root, "campaign.json"), "w", encoding="utf-8") as f:
        json.dump(campaign, f, indent=2, ensure_ascii=False)
    with open(os.path.join(camp_root, "briefing.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(struct, f, sort_keys=False, allow_unicode=True)

    names, _ = formats.resolve_formats(channels, explicit)
    return {"brand": brand_id, "brand_root": brand_root,
            "campaign": camp_id, "campaign_root": camp_root,
            "concepts": concepts, "formats": names,
            "palette": palette, "palette_proposed": proposed,
            "video": bool(campaign.get("video")),
            "fonts": list(type_cfg), "fotos": len(copied_fotos),
            "videos": len(copied_videos) + video_copies}


def template_md():
    """Template markdown gerado do schema — preencha ou peça ao agente para adaptar."""
    schema = load_schema()
    lines = ["# Briefing — modelo campaign-kit",
             "",
             "Preencha os campos abaixo (ou peça ao agente para adaptar um briefing existente a este modelo).",
             "Obrigatórios bloqueiam o apply; opcionais têm default ou viram pergunta em rodada única.",
             "Caminhos de arquivo são relativos a este briefing.", ""]
    for i, (sec, body) in enumerate(schema["secoes"].items(), 1):
        lines.append(f"## {i}. {body['titulo']}")
        lines.append("")
        for key, meta in body["campos"].items():
            req = "obrigatório" if meta.get("obrigatorio") else "opcional"
            extra = []
            if "valores" in meta:
                extra.append("valores: " + ", ".join(str(v) for v in meta["valores"]))
            if "padrao" in meta:
                extra.append(f"default: {meta['padrao']}")
            if "chaves" in meta:
                extra.append("chaves: " + ", ".join(meta["chaves"]))
            suffix = f" ({'; '.join(extra)})" if extra else ""
            lines.append(f"- **{sec}.{key}** [{req}] — {meta['pergunta']}{suffix}")
            lines.append(f"  - {meta['porque']}")
            lines.append(f"  - resposta: _preencher_")
        lines.append("")
    return "\n".join(lines)


TEXT_EXT = (".md", ".txt", ".rtf")
_MAP_TYPES = ("mapa_hex", "mapa_arquivos", "mapa_listas", "mapa_duracoes", "copy_por_conceito")
_LIST_TYPES = ("lista", "lista_hex", "lista_arquivos", "lista_segmentos")


def _placeholder(tipo):
    if tipo in _LIST_TYPES:
        return []
    if tipo in _MAP_TYPES:
        return {}
    return None


def _yaml_val(v):
    if v is None:
        return "null"
    if v == []:
        return "[]"
    return "{}"


def skeleton_yaml():
    """YAML do schema com valores vazios e a pergunta de cada campo em comentário.

    Vazio de propósito: o que o agente não souber preencher fica null/[]/{} e vira
    gap na rodada única do validate — nunca um chute silencioso.
    """
    schema = load_schema()
    lines = ["# Briefing canônico — skeleton gerado do schema (normalize).",
             "# O agente preenche a partir do briefing-fonte; o que não souber fica vazio",
             "# (vira pergunta na rodada única do validate). Nunca chute.",
             "# Caminhos de arquivo são relativos a este arquivo.", ""]
    for sec, body in schema["secoes"].items():
        lines.append(f"{sec}:  # {body['titulo']}")
        opened = set()
        for field, meta in body["campos"].items():
            req = "obrigatório" if meta.get("obrigatorio") else "opcional"
            comment = f"# [{req}] {meta['pergunta']}"
            val = _yaml_val(_placeholder(meta["tipo"]))
            parts = field.split(".")
            if len(parts) == 1:
                lines.append(f"  {comment}")
                lines.append(f"  {field}: {val}")
            else:
                top, sub = parts
                if top not in opened:
                    lines.append(f"  {top}:")
                    opened.add(top)
                lines.append(f"    {comment}")
                lines.append(f"    {sub}: {val}")
        lines.append("")
    return "\n".join(lines)


def normalize_prepare(source, out_path, root=ROOT):
    """Prepara a normalização de um briefing livre para o schema canônico.

    O Python só emite o skeleton + o contrato; quem lê a prosa (ou extrai PDF/docx
    com visão) e preenche o YAML é o AGENTE. A garantia determinística continua
    sendo validate (rodada única de gaps) + apply. Devolve o resumo do handoff.
    """
    source = os.path.abspath(os.path.expanduser(source))
    out_path = os.path.abspath(os.path.expanduser(out_path))
    if not os.path.isfile(source):
        raise ValueError(f"briefing-fonte não encontrado: {source}")
    if os.path.exists(out_path):
        raise ValueError(f"já existe {out_path} — escolha outro --out para não sobrescrever")

    low = source.lower()
    is_text = low.endswith(TEXT_EXT)
    raw = ""
    if is_text:
        try:
            with open(source, encoding="utf-8") as f:
                raw = f.read()
        except (OSError, UnicodeDecodeError):
            is_text = False

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(skeleton_yaml())

    contract = out_path + ".normalize.md"
    base_dir = os.path.dirname(out_path)
    lines = [f"# Normalizar briefing → schema canônico",
             "",
             f"- **fonte:** `{source}`",
             f"- **alvo (preencha este YAML):** `{out_path}`",
             f"- **base dos caminhos de arquivo:** `{base_dir}` (paths no YAML são relativos a ele)",
             ""]
    if is_text and raw.strip():
        lines += ["## Conteúdo da fonte (texto)", "", "```", raw.rstrip(), "```", ""]
    else:
        lines += ["## Extração (arquivo binário)", "",
                  "A fonte é PDF/docx/imagem: **extraia o conteúdo com a sua ferramenta**",
                  "(visão para PDF/imagem, leitor de docx) antes de mapear para os campos.", ""]
    lines += ["## Regras (invioláveis)", "",
              "1. Mapeie a prosa para os campos do skeleton; cada comentário é a pergunta do campo.",
              "2. **Não souber → deixe vazio** (null/[]/{}). Vazio vira pergunta na rodada única",
              "   do `validate`; nunca invente valor, cor, canal, conceito ou copy.",
              "3. Respeite os enums e as chaves de mapa indicadas no schema (briefing.schema.yaml).",
              "4. `campanha.conceitos` + um `campanha.copy.<conceito>.hook` por conceito.",
              "5. Caminhos de logo/fontes/fotos/vídeos/refs relativos à base acima.",
              "", "## Depois de preencher", "",
              f"```bash\npython3 -m kit.cli brief {out_path}          # valida (gaps + erros)\n"
              f"python3 -m kit.cli brief {out_path} --apply   # escreve brand.yaml + campaign.json\n```", ""]
    with open(contract, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"source": source, "kind": "text" if is_text else "binary",
            "needs_extraction": not is_text, "skeleton": out_path,
            "contract": contract, "base_dir": base_dir}