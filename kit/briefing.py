"""Canonical briefing: schema -> validate -> apply.

briefing.schema.yaml is the single source: gap questions (single round, like intake),
structural errors and the markdown template all come from it. apply is deterministic:
writes brands/<id>/brand.yaml and campaigns/<brand>-<slug>/campaign.json (video block
included) and copies the declared assets. No silent inference: what can't be derived
with confidence (palette from the logo) is marked as a proposal.
"""

import json
import os
import re
import shutil

import yaml

from . import formats, i18n
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
    """Gaps (required/optional, single round) + structural errors. ok = appliable.
    Gap questions come from the schema; structural errors are EN (agent contract)."""
    schema = load_schema()
    gaps, errors = [], []

    def err(field, msg):
        errors.append({"field": field, "message": msg})

    if not isinstance(struct, dict):
        return {"ok": False, "gaps": [], "errors": [{"field": "$", "message": "briefing is not a YAML/JSON map"}]}

    for sec in struct:
        if sec not in schema["secoes"]:
            err(sec, f"unknown section (valid: {', '.join(schema['secoes'])})")

    concepts_raw = _get(struct, "campanha.conceitos") or []
    concepts = [_slug(c, 24) for c in concepts_raw if not _empty(c)]
    copy = _get(struct, "campanha.copy") or {}
    copy_keys = {_slug(k, 24): v for k, v in copy.items()} if isinstance(copy, dict) else {}

    for field, meta in _fields(schema):
        v = _get(struct, field)
        tipo = meta["tipo"]
        if _empty(v):
            q, w = meta["pergunta"], meta["porque"]
            if meta.get("obrigatorio"):
                gaps.append({"field": field, "question": q, "why": w, "required": True})
            elif meta.get("perguntar_se_ausente"):
                gaps.append({"field": field, "question": q, "why": w, "required": False})
            continue

        if tipo == "texto" and not isinstance(v, str):
            err(field, "expected text")
        elif tipo == "numero":
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                err(field, "expected number")
            elif field == "compliance.tolerancia_rosto" and not 0 <= v <= 1:
                err(field, "tolerance must be between 0 and 1")
        elif tipo == "enum":
            if v not in meta["valores"]:
                err(field, f"invalid value '{v}' (use: {', '.join(meta['valores'])})")
        elif tipo in ("lista", "lista_hex", "lista_arquivos"):
            if not isinstance(v, list):
                err(field, "expected list")
            elif tipo == "lista_hex":
                for c in v:
                    if not HEX_RE.match(str(c)):
                        err(field, f"invalid color: {c} (use #RRGGBB)")
        elif tipo == "mapa_hex":
            if not isinstance(v, dict):
                err(field, "expected color map")
            else:
                for k, c in v.items():
                    if k not in meta["chaves"]:
                        err(field, f"unknown color key: {k} (use: {', '.join(meta['chaves'])})")
                    elif not HEX_RE.match(str(c)):
                        err(field, f"invalid color in {k}: {c}")
        elif tipo == "mapa_arquivos":
            if not isinstance(v, dict):
                err(field, "expected role -> file map")
            else:
                for k in v:
                    if k not in meta["chaves"]:
                        err(field, f"unknown font role: {k} (use: {', '.join(meta['chaves'])})")
        elif tipo == "mapa_listas":
            if not isinstance(v, dict) or any(not isinstance(x, list) or not x for x in v.values()):
                err(field, "expected map of non-empty lists (e.g. product: [A, B])")
        elif tipo == "mapa_duracoes":
            if not isinstance(v, dict):
                err(field, "expected format -> seconds map")
            else:
                for k, s in v.items():
                    if k != "default" and k not in formats.FORMATS:
                        err(field, f"unknown format in duracoes: {k}")
                    elif not isinstance(s, (int, float)) or s <= 0:
                        err(field, f"invalid duration in {k}: {s}")
        elif tipo == "copy_por_conceito":
            if not isinstance(v, dict):
                err(field, "expected concept -> {hook, kicker} map")
            else:
                for k in v:
                    if _slug(k, 24) not in concepts and concepts:
                        err(field, f"copy for undeclared concept: {k}")
        elif tipo == "lista_segmentos":
            if not isinstance(v, list):
                err(field, "expected segment list")
            else:
                for s in v:
                    if not isinstance(s, dict) or not all(k in s for k in ("start", "end", "text")):
                        err(field, "segment needs start, end and text")
                        break

        if tipo in ("arquivo", "lista_arquivos", "mapa_arquivos") and base_dir:
            paths = [v] if tipo == "arquivo" else (v if tipo == "lista_arquivos" else list(v.values()))
            for p in paths:
                if isinstance(p, str) and not os.path.isfile(os.path.join(base_dir, os.path.expanduser(p))):
                    err(field, f"file not found: {p}")

    canais = _get(struct, "campanha.canais") or []
    if isinstance(canais, list):
        for c in canais:
            if c not in formats.BUNDLES and c not in formats.FORMATS:
                err("campanha.canais", f"unknown channel/format: {c}")

    for c in concepts:
        entry = copy_keys.get(c) or {}
        if not isinstance(entry, dict) or _empty(entry.get("hook")):
            gaps.append({"field": f"campanha.copy.{c}.hook",
                         "question": i18n.t("gap.brief.hook.q", c=c),
                         "why": i18n.t("gap.brief.hook.w"),
                         "required": True})

    video_present = any(not _empty(_get(struct, f"video.{k}"))
                        for k in ("fonte", "concat", "duracoes", "legendas", "segmentos", "formatos"))
    if video_present and _empty(_get(struct, "video.fonte")) and _empty(_get(struct, "video.concat")):
        gaps.append({"field": "video.fonte",
                     "question": i18n.t("gap.brief.videosource.q"),
                     "why": i18n.t("gap.brief.videosource.w"), "required": True})
    if _get(struct, "video.legendas") == "manual" and _empty(_get(struct, "video.segmentos")):
        gaps.append({"field": "video.segmentos",
                     "question": i18n.t("gap.brief.segments.q"),
                     "why": i18n.t("gap.brief.segments.w"),
                     "required": True})
    if _get(struct, "provider.nome") == "http" and _empty(_get(struct, "provider.api_url")):
        gaps.append({"field": "provider.api_url",
                     "question": i18n.t("gap.brief.apiurl.q"),
                     "why": i18n.t("gap.brief.apiurl.w"), "required": True})

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
    """Writes brand.yaml + campaign.json (and the provenance briefing). Deterministic."""
    v = validate(struct, base_dir)
    if not v["ok"]:
        raise ValueError("briefing not appliable: " +
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
        fname = _copy_file(path, base_dir, os.path.join(brand_root, "fonts"))
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

    slug = _slug(camp.get("slug") or camp["objetivo"]) or "campaign"
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
        "objective": camp["objetivo"],
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
    """Markdown template generated from the schema — fill it in or ask the agent to adapt one."""
    schema = load_schema()
    lines = ["# Briefing — campaign-kit template",
             "",
             "Fill in the fields below (or ask the agent to adapt an existing briefing to this template).",
             "Required fields block apply; optional ones have a default or become a single-round question.",
             "File paths are relative to this briefing.", ""]
    for i, (sec, body) in enumerate(schema["secoes"].items(), 1):
        lines.append(f"## {i}. {body['titulo']}")
        lines.append("")
        for key, meta in body["campos"].items():
            req = "required" if meta.get("obrigatorio") else "optional"
            extra = []
            if "valores" in meta:
                extra.append("values: " + ", ".join(str(v) for v in meta["valores"]))
            if "padrao" in meta:
                extra.append(f"default: {meta['padrao']}")
            if "chaves" in meta:
                extra.append("keys: " + ", ".join(meta["chaves"]))
            suffix = f" ({'; '.join(extra)})" if extra else ""
            lines.append(f"- **{sec}.{key}** [{req}] — {meta['pergunta']}{suffix}")
            lines.append(f"  - {meta['porque']}")
            lines.append(f"  - answer: _fill in_")
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
    """Schema YAML with empty values and each field's question as a comment.

    Empty on purpose: what the agent can't fill stays null/[]/{} and becomes a gap
    in validate's single round — never a silent guess.
    """
    schema = load_schema()
    lines = ["# Canonical briefing — skeleton generated from the schema (normalize).",
             "# The agent fills it from the source briefing; what it doesn't know stays empty",
             "# (becomes a question in validate's single round). Never guess.",
             "# File paths are relative to this file.", ""]
    for sec, body in schema["secoes"].items():
        lines.append(f"{sec}:  # {body['titulo']}")
        opened = set()
        for field, meta in body["campos"].items():
            req = "required" if meta.get("obrigatorio") else "optional"
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
    """Prepares normalizing a free-form briefing into the canonical schema.

    Python only emits the skeleton + the contract; the one who reads the prose (or
    extracts PDF/docx with vision) and fills the YAML is the AGENT. The deterministic
    guarantee remains validate (single round of gaps) + apply. Returns the handoff summary.
    """
    source = os.path.abspath(os.path.expanduser(source))
    out_path = os.path.abspath(os.path.expanduser(out_path))
    if not os.path.isfile(source):
        raise ValueError(f"source briefing not found: {source}")
    if os.path.exists(out_path):
        raise ValueError(f"{out_path} already exists — pick another --out to avoid overwriting")

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
    lines = ["# Normalize briefing → canonical schema",
             "",
             f"- **source:** `{source}`",
             f"- **target (fill in this YAML):** `{out_path}`",
             f"- **base for file paths:** `{base_dir}` (paths in the YAML are relative to it)",
             ""]
    if is_text and raw.strip():
        lines += ["## Source content (text)", "", "```", raw.rstrip(), "```", ""]
    else:
        lines += ["## Extraction (binary file)", "",
                  "The source is PDF/docx/image: **extract the content with your tool**",
                  "(vision for PDF/image, docx reader) before mapping it to the fields.", ""]
    lines += ["## Rules (inviolable)", "",
              "1. Map the prose to the skeleton's fields; each comment is the field's question.",
              "2. **Don't know → leave it empty** (null/[]/{}). Empty becomes a question in",
              "   `validate`'s single round; never invent a value, color, channel, concept or copy.",
              "3. Respect the enums and map keys indicated in the schema (briefing.schema.yaml).",
              "4. `campanha.conceitos` + one `campanha.copy.<concept>.hook` per concept.",
              "5. Logo/font/photo/video/ref paths relative to the base above.",
              "", "## After filling it in", "",
              f"```bash\npython3 -m kit.cli brief {out_path}          # validate (gaps + errors)\n"
              f"python3 -m kit.cli brief {out_path} --apply   # write brand.yaml + campaign.json\n```", ""]
    with open(contract, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"source": source, "kind": "text" if is_text else "binary",
            "needs_extraction": not is_text, "skeleton": out_path,
            "contract": contract, "base_dir": base_dir}