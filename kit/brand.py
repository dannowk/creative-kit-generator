"""Marca como dado: paleta, tipografia, voz, eixos, naming e compliance.

Nada de marca vive no motor — este módulo é a única ponte entre o brand.yaml e as primitivas.
"""

import os
import glob
import yaml

FONT_ENV = "CAMPAIGN_FONTS"

# Degradação honesta quando a fonte da marca não veio na pasta: mantém peso/itálico
# aproximados em vez de estourar. O intake avisa que a tipografia não foi inferida.
FALLBACK = {
    "display": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "accent": [
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:\\Windows\\Fonts\\arialbi.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    ],
    "text": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def hex_rgb(value):
    if isinstance(value, (list, tuple)):
        return tuple(int(v) for v in value[:3])
    s = str(value).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def font_dirs(extra=()):
    here = os.path.dirname(os.path.abspath(__file__))
    return [d for d in list(extra) + [
        os.environ.get(FONT_ENV),
        os.path.expanduser("~/Library/Fonts"),
        os.path.join(here, "..", "fonts"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
    ] if d]


def find_font(filename, dirs):
    """Procura pelo nome exato, depois por stem, em qualquer pasta de fonte conhecida."""
    if not filename:
        return None
    if os.path.isabs(filename) and os.path.isfile(filename):
        return filename
    for d in dirs:
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    stem = os.path.splitext(os.path.basename(filename))[0].lower()
    for d in dirs:
        for p in glob.glob(os.path.join(d, "*")):
            if os.path.splitext(os.path.basename(p))[0].lower() == stem:
                return p
    return None


class FontBook:
    def __init__(self, type_cfg, dirs):
        self.dirs = dirs
        self.cfg = type_cfg or {}
        self.missing = []
        self.substituted = []

    def spec(self, role):
        """role -> (caminho, índice TTC). Registra substituição para o intake reportar."""
        entry = self.cfg.get(role) or {}
        if isinstance(entry, str):
            entry = {"file": entry}
        path = find_font(entry.get("file"), self.dirs)
        if path is None:
            if entry.get("file") and entry["file"] not in self.missing:
                self.missing.append(entry["file"])
            for cand in FALLBACK.get(role, FALLBACK["text"]):
                if os.path.isfile(cand):
                    pair = (role, os.path.basename(cand))
                    if pair not in self.substituted:
                        self.substituted.append(pair)
                    return (cand, entry.get("index", 0))
            raise FileNotFoundError(f"Sem fonte para '{role}' e sem fallback de sistema.")
        return (path, entry.get("index", 0))

    def style(self, role="display"):
        """Parâmetros do contraste tipográfico que o draw_copy consome."""
        accent_role = f"{role}_accent"
        return {
            "base": self.spec(role),
            "accent": self.spec(accent_role if accent_role in self.cfg else "accent"),
            "accent_scale": self.cfg.get("accent_scale", 1.22),
            "accent_upper": self.cfg.get("accent_upper", True),
            "underline": self.cfg.get("underline", True),
        }


class Brand:
    def __init__(self, data, root):
        self.root = root
        self.data = data
        self.id = data.get("id") or os.path.basename(root.rstrip("/"))
        self.name = data.get("name", self.id)
        self.palette = {k: hex_rgb(v) for k, v in (data.get("palette") or {}).items()
                        if k != "forbidden"}
        self.forbidden = [hex_rgb(v) for v in (data.get("palette") or {}).get("forbidden", [])]
        self.assets_dir = os.path.join(root, data.get("assets_dir", "assets"))
        self.fonts = FontBook(data.get("type"), font_dirs([self.assets_dir, os.path.join(root, "fontes")]))
        self.voice = data.get("voice") or {}
        self.axes = data.get("axes") or []
        self.naming = data.get("naming", "{slug}_{concept}_{size}")
        self.compliance = data.get("compliance") or []
        self.safe_zones = data.get("safe_zones") or {}
        self.locales = data.get("locales") or [data.get("locale_default", "en")]
        self.locale_default = data.get("locale_default", self.locales[0])
        self.logo_path = self._logo(data.get("logo"))
        self.logo_scale = (data.get("logo") or {}).get("scale", 0.30)

    def _logo(self, cfg):
        if isinstance(cfg, str):
            cfg = {"file": cfg}
        cfg = cfg or {}
        if cfg.get("file"):
            p = cfg["file"]
            p = p if os.path.isabs(p) else os.path.join(self.root, p)
            if os.path.isfile(p):
                return p
        for p in sorted(glob.glob(os.path.join(self.assets_dir, "*"))):
            if "logo" in os.path.basename(p).lower() and p.lower().endswith((".png", ".webp")):
                return p
        return None

    def color(self, ref, default=(255, 255, 255)):
        """Resolve 'palette.primary', 'white', '#FF9E00' ou [r,g,b]."""
        if ref is None:
            return default
        if isinstance(ref, (list, tuple)):
            return hex_rgb(ref)
        s = str(ref)
        if s.startswith("#"):
            return hex_rgb(s)
        if s.startswith("palette."):
            key = s.split(".", 1)[1]
            if key in self.palette:
                return self.palette[key]
            raise KeyError(f"Cor '{key}' não está na paleta de {self.id}.")
        named = {"white": (255, 255, 255), "black": (0, 0, 0),
                 "ink": self.palette.get("ink", (17, 24, 32)),
                 "dark": self.palette.get("dark", (8, 13, 17)),
                 "paper": self.palette.get("paper", (244, 239, 230)),
                 "accent": self.palette.get("accent", (255, 158, 0)),
                 "primary": self.palette.get("primary", (1, 58, 129))}
        return named.get(s, default)

    def axis_values(self, axis):
        """Eixo pode listar valores inline ou apontar para um CSV/JSON da pasta da marca."""
        if "values" in axis:
            return list(axis["values"])
        src = axis.get("values_from")
        if not src:
            return []
        p = src if os.path.isabs(src) else os.path.join(self.root, src)
        if p.endswith(".json"):
            import json
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            return [r.get("id") or r.get("name") for r in data] if isinstance(data, list) else list(data)
        import csv
        with open(p, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        key = axis.get("column") or ("id" if rows and "id" in rows[0] else None)
        if key:
            return [r[key] for r in rows if r.get(key)]
        return [r[list(r)[0]] for r in rows if r]

    def asset_path(self, rel):
        return rel if os.path.isabs(rel) else os.path.join(self.root, rel)


def load_brand(path):
    """path = pasta da marca (com brand.yaml) ou o próprio arquivo."""
    if os.path.isdir(path):
        root, file = path, os.path.join(path, "brand.yaml")
    else:
        root, file = os.path.dirname(path), path
    with open(file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Brand(data, root)