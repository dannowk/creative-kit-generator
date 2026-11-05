"""Presets de canal e formato — universais, não pertencem a nenhuma marca.

As safe zones de Stories/reels são regra da plataforma (perfil em cima, campo de
resposta embaixo), por isso vivem aqui e não no brand.yaml.
"""

FORMATS = {
    "meta_feed_square":    {"size": (1080, 1080), "channel": "meta"},
    "meta_feed_portrait":  {"size": (1080, 1350), "channel": "meta"},
    "meta_story":          {"size": (1080, 1920), "channel": "meta", "safe_top": 0.13, "safe_bottom": 0.12},
    "meta_landscape":      {"size": (1200, 628),  "channel": "meta"},
    "google_display_land": {"size": (1200, 628),  "channel": "google"},
    "google_display_sq":   {"size": (1200, 1200), "channel": "google"},
    "google_display_port": {"size": (960, 1200),  "channel": "google"},
    "google_medium_rect":  {"size": (300, 250),   "channel": "google"},
    "google_leaderboard":  {"size": (728, 90),    "channel": "google"},
    "google_skyscraper":   {"size": (160, 600),   "channel": "google"},
    "google_mobile_banner": {"size": (320, 50),   "channel": "google"},
    "linkedin_feed":       {"size": (1200, 627),  "channel": "linkedin"},
    "linkedin_square":     {"size": (1080, 1080), "channel": "linkedin"},
    "x_feed":              {"size": (1600, 900),  "channel": "x"},
    "tiktok_story":        {"size": (1080, 1920), "channel": "tiktok", "safe_top": 0.12, "safe_bottom": 0.20},
    "youtube_thumbnail":   {"size": (1280, 720),  "channel": "youtube"},
    "print_a4_portrait":   {"size": (2480, 3508), "channel": "print", "dpi": 300},
    "print_a3_portrait":   {"size": (3508, 4961), "channel": "print", "dpi": 300},
    "print_letter":        {"size": (2550, 3300), "channel": "print", "dpi": 300},
    "email_header":        {"size": (1200, 400),  "channel": "email"},
    "web_hero":            {"size": (1920, 1080), "channel": "web"},
}

BUNDLES = {
    "meta":     ["meta_feed_square", "meta_feed_portrait", "meta_story", "meta_landscape"],
    "google":   ["google_display_land", "google_display_sq", "google_display_port",
                 "google_medium_rect", "google_leaderboard", "google_skyscraper"],
    "linkedin": ["linkedin_feed", "linkedin_square"],
    "social_paid": ["meta_feed_square", "meta_feed_portrait", "meta_story",
                    "google_display_land", "google_display_sq", "google_display_port"],
    "print":    ["print_a4_portrait", "print_letter"],
    "web":      ["web_hero", "email_header"],
}

# Formatos minúsculos não comportam foto + chamada + logo: o renderer escolhe arquétipo tipográfico.
TIGHT = {"google_leaderboard", "google_mobile_banner", "google_skyscraper", "google_medium_rect"}


def resolve_formats(channels=(), formats=()):
    """Aceita nomes de canal (expande pelo bundle) e nomes de formato explícitos."""
    names = list(formats)
    for c in channels:
        names += BUNDLES.get(c, [])
    seen, out = set(), []
    for n in names:
        if n in FORMATS and n not in seen:
            seen.add(n)
            out.append(n)
    unknown = [n for n in names if n not in FORMATS]
    return out, unknown


def label(name):
    """meta_feed_portrait -> Meta-Feed-Portrait_1080x1350 (compatível com o naming antigo)."""
    w, h = FORMATS[name]["size"]
    channel = name.rsplit("_", 1)[0] if name.count("_") > 1 else name
    return f"{channel.replace('_', '-').title()}_{w}x{h}"


def geometry(name, brand=None):
    """w, h, scale, margem, topo e base seguros, e se é wide — tudo proporcional à √área."""
    spec = FORMATS[name]
    w, h = spec["size"]
    scale = (w * h) ** 0.5
    m = round(scale * 0.06)
    st, sb = spec.get("safe_top", 0), spec.get("safe_bottom", 0)
    if brand is not None:
        st = max(st, brand.safe_zones.get("top", 0))
        sb = max(sb, brand.safe_zones.get("bottom", 0))
    top = max(m, round(h * st))
    bottom = h - max(m, round(h * sb))
    return {"w": w, "h": h, "scale": scale, "m": m, "top": top, "bottom": bottom,
            "wide": w / h > 1.5, "tight": name in TIGHT, "format": name}