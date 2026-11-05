"""Primitivas de imagem e tipografia, sem nenhuma marca dentro.

Portado do motor CDI (gerar_templates_v3.py / processar_campanha.py / gerar_concept4.py).
Cores, fontes e textos entram por parâmetro — o resultado visual é o mesmo do original.
"""

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

LANCZOS = Image.LANCZOS


# ---------------------------------------------------------------- geometria de foto
def resize_and_crop(img, size):
    tw, th = size
    ratio = max(tw / img.width, th / img.height)
    nw, nh = round(img.width * ratio), round(img.height * ratio)
    img = img.resize((nw, nh), LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def subject_center(img):
    """Centro horizontal da pessoa por energia de bordas na faixa rosto/tronco, puxado ao centro."""
    small = img.convert("L").resize((640, 360)).filter(ImageFilter.FIND_EDGES)
    cols = [ImageStat.Stat(small.crop((x * 16, 40, x * 16 + 16, 250))).mean[0] for x in range(40)]
    weights = [max(0, c - 6) ** 2 for c in cols]
    centroid = sum((i + 0.5) * w for i, w in enumerate(weights)) / max(1, sum(weights)) / 40
    return 0.5 + (centroid - 0.5) * 0.6


def crop(img, w, h, center, subject_at=0.5):
    """Cobre w×h com a pessoa na posição horizontal subject_at; corta mais embaixo que em cima."""
    ratio = max(w / img.width, h / img.height)
    sw, sh = round(img.width * ratio), round(img.height * ratio)
    scaled = img.resize((sw, sh), LANCZOS)
    x0 = max(0, min(round(center * sw - subject_at * w), sw - w))
    y0 = round((sh - h) * 0.15)
    return scaled.crop((x0, y0, x0 + w, y0 + h))


def closeup(img, w, h, fx, zoom, face_at=0.38, fx_at=0.5, face_y=0.27):
    """Janela w:h com altura zoom×altura da foto, sujeito em fx e na altura face_at."""
    ch = img.height * zoom
    cw = ch * w / h
    if cw > img.width:
        cw, ch = img.width, img.width * h / w
    x0 = min(max(fx * img.width - fx_at * cw, 0), img.width - cw)
    y0 = min(max(face_y * img.height - face_at * ch, 0), img.height - ch)
    return img.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((w, h), LANCZOS)


# ---------------------------------------------------------------- película e logo
def multiply_overlay(base, overlay):
    """Multiply como no Photoshop: multiplica as cores e usa o alfa da película como máscara."""
    base = base.convert("RGBA")
    overlay = overlay.convert("RGBA")
    mult = ImageChops.multiply(base.convert("RGB"), overlay.convert("RGB")).convert("RGBA")
    mult.putalpha(overlay.getchannel("A"))
    return Image.alpha_composite(base, mult)


def multiply_color(base, color, alpha=1.0):
    film = Image.new("RGBA", base.size, tuple(color) + (round(255 * alpha),))
    return multiply_overlay(base, film)


def sized_logo(logo, width, max_w_ratio=0.36, max_h_ratio=0.18, canvas=None):
    """Logo escala por √(L×A) para ocupar a mesma fração visual em qualquer formato."""
    if canvas is not None:
        w, h = canvas
        width = min(width, w * max_w_ratio, h * max_h_ratio * logo.width / logo.height)
    width = max(1, round(width))
    return logo.resize((width, round(logo.height * width / logo.width)), LANCZOS)


def ink_logo(logo, ink):
    out = Image.new("RGBA", logo.size, tuple(ink) + (0,))
    out.putalpha(logo.getchannel("A"))
    return out


# ---------------------------------------------------------------- grading
def grade(img, vignette=0.45, grain=7, shadow=(0.02, 0.07, 0.09), light=(1.0, 0.86, 0.7), seed=7):
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Color(img).enhance(0.9)
    a = np.asarray(img).astype(np.float32) / 255
    lum = a.mean(axis=2, keepdims=True)
    a = a + (1 - lum) ** 2 * (np.array(shadow) - a) * 0.35
    a = a + lum ** 2 * (np.array(light) - a) * 0.12
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.42) / (h * 0.7)) ** 2)
    a *= 1 - vignette * np.clip(d - 0.55, 0, 1)[..., None]
    a += np.random.default_rng(seed).normal(0, grain / 255, (h, w, 1))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def fade_to(img, color, start, end, horizontal=False, flip=False):
    """Esmaece para `color` entre start e end (fração do comprimento, 0 = lado da foto)."""
    w, h = img.size
    n = w if horizontal else h
    line = Image.new("L", (n, 1))
    for i in range(n):
        t = min(1, max(0, (i / n - start) / (end - start)))
        line.putpixel((i, 0), round(255 * t * t * (3 - 2 * t)))
    mask = line.resize((w, h)) if horizontal else line.rotate(-90, expand=True).resize((w, h))
    if flip:
        mask = mask.transpose(Image.FLIP_LEFT_RIGHT if horizontal else Image.FLIP_TOP_BOTTOM)
    out = img.copy()
    out.paste(Image.new("RGB", (w, h), tuple(color)), (0, 0), mask)
    return out


def light_leak(img, corner="tl", strength=0.35, color=(1.0, 0.5, 0.1)):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (0 if "l" in corner else w), (0 if "t" in corner else h)
    t = np.clip(1 - np.hypot(xx - cx, yy - cy) / (0.75 * max(w, h)), 0, 1) ** 2 * strength
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
    leak = np.array(color, dtype=np.float32)
    a = 1 - (1 - a) * (1 - leak[None, None, :] * t[..., None])
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


# ---------------------------------------------------------------- textura
def _rng(seed):
    return np.random.default_rng(seed)


def film_texture(img, grain=6, dust=1.0, seed=3):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w = a.shape[:2]
    r = _rng(seed)
    a += r.normal(0, grain, (h, w, 1))
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    for _ in range(int(w * h / 9000 * dust)):
        x, y, s = r.integers(0, w), r.integers(0, h), r.uniform(0.6, 2.2)
        d.ellipse([x, y, x + s, y + s], fill=int(r.uniform(40, 120)))
    for _ in range(int(6 * dust)):
        x, y0 = r.integers(0, w), r.integers(0, h)
        d.line([x, y0, x + r.uniform(-3, 3), y0 + r.uniform(h * 0.1, h * 0.4)],
               fill=int(r.uniform(20, 55)), width=1)
    layer = layer.filter(ImageFilter.GaussianBlur(0.5))
    a += np.asarray(layer).astype(np.float32)[..., None] * 0.6
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def paper(w, h, base=(244, 239, 230), seed=5):
    r = _rng(seed)
    low = Image.fromarray(r.normal(128, 40, (h // 40 + 2, w // 40 + 2)).clip(0, 255).astype(np.uint8))
    low = np.asarray(low.resize((w, h), Image.BICUBIC)).astype(np.float32) / 255 - 0.5
    fine = r.normal(0, 1, (h, w)).astype(np.float32)
    fib = Image.new("L", (w, h), 128)
    d = ImageDraw.Draw(fib)
    for _ in range(int(w * h / 2500)):
        x, y, ang, ln = r.uniform(0, w), r.uniform(0, h), r.uniform(0, 6.28), r.uniform(4, 14)
        d.line([x, y, x + np.cos(ang) * ln, y + np.sin(ang) * ln], fill=int(r.choice([108, 150])), width=1)
    fibers = (np.asarray(fib.filter(ImageFilter.GaussianBlur(0.4))).astype(np.float32) - 128) / 128
    a = np.array(base, dtype=np.float32)[None, None, :] * (
        1 + low[..., None] * 0.05 + fine[..., None] * 0.012 + fibers[..., None] * 0.06)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def halftone(size, corner, color, opacity=0.45, step=None, reach=0.9):
    """Pontos grandes no canto que diminuem até sumir. corner: tl tr bl br. Devolve RGBA."""
    w, h = size
    step = step or max(10, round(min(w, h) * 0.032))
    sc = 2
    layer = Image.new("L", (w * sc, h * sc), 0)
    d = ImageDraw.Draw(layer)
    cx, cy = (0 if "l" in corner else w), (0 if "t" in corner else h)
    far = reach * max(w, h)
    for gy in range(0, h + step, step):
        for gx in range(0, w + step, step):
            ox = gx + (step / 2 if (gy // step) % 2 else 0)
            t = 1 - min(1, np.hypot(ox - cx, gy - cy) / far)
            rad = step * 0.48 * t ** 1.2
            if rad > 0.7:
                d.ellipse([(ox - rad) * sc, (gy - rad) * sc, (ox + rad) * sc, (gy + rad) * sc], fill=255)
    mask = layer.resize((w, h), LANCZOS).point(lambda v: round(v * opacity))
    out = Image.new("RGBA", (w, h), tuple(color) + (0,))
    out.putalpha(mask)
    return out


# ---------------------------------------------------------------- tipografia
def tokens(text):
    """[colchete] marca a palavra de destaque; pode abranger várias palavras."""
    out, marked = [], False
    for raw in text.split():
        start = raw.startswith("[")
        marked = marked or start
        out.append((raw.replace("[", "").replace("]", ""), marked))
        if "]" in raw:
            marked = False
    return out


def ft(spec, size):
    path, index = spec
    return ImageFont.truetype(path, max(1, round(size)), index=index)


def draw_copy(canvas, x, y_bottom, width, max_h, text, start, color, font_style,
              align="left", accent=(255, 158, 0), min_size=14, max_lines=4, metrics=None):
    """Contraste de peso: palavra marcada em fonte mais pesada/condensada/itálica, na cor de acento.
    Encolhe até caber em max_lines e max_h. Termina em y_bottom; devolve o topo."""
    base_spec, acc_spec = font_style["base"], font_style["accent"]
    acc_scale = font_style.get("accent_scale", 1.2)
    acc_upper = font_style.get("accent_upper", True)
    underline = font_style.get("underline", True)
    nobreak = font_style.get("nobreak", [])
    words = _apply_nobreak(tokens(text), nobreak)

    size, lines, base, acc = start, None, None, None
    while size > min_size:
        base, acc = ft(base_spec, size), ft(acc_spec, size * acc_scale)

        def wl(wd):
            return (acc if wd[1] else base).getlength(wd[0].upper() if wd[1] and acc_upper else wd[0])

        cand, cur = [], []
        for wd in words:
            if sum(wl(t) for t in cur + [wd]) + base.getlength(" ") * len(cur) <= width:
                cur.append(wd)
            elif cur and wl(wd) <= width:
                cand.append(cur)
                cur = [wd]
            else:
                cand = None
                break
        if cand is not None:
            cand.append(cur)
            lines = cand
            if len(cand) <= max_lines and len(cand) * size * 1.12 <= max_h:
                break
        size -= 2

    if lines is None:
        lines = [[w] for w in words]
    if metrics is not None:
        metrics["size"] = size
        metrics["lines"] = len(lines)
    lead = round(size * 1.12)
    draw = ImageDraw.Draw(canvas)
    space = base.getlength(" ")
    y = y_bottom - lead * (len(lines) - 1)
    for line in lines:
        total = sum(wl(t) for t in line) + space * (len(line) - 1)
        cx = x + (width - total) / 2 if align == "center" else x
        for wd in line:
            if wd[1]:
                label = wd[0].upper() if acc_upper else wd[0]
                draw.text((cx, y), label, font=acc, fill=tuple(accent), anchor="ls")
                if underline:
                    aw = acc.getlength(label)
                    t = size * 0.075
                    yy = y + size * 0.14
                    draw.polygon([(cx - size * 0.04, yy + t), (cx + aw * 0.98, yy - t * 0.5),
                                  (cx + aw, yy + t * 0.6), (cx, yy + t * 1.9)], fill=tuple(accent))
            else:
                draw.text((cx, y), wd[0], font=base, fill=tuple(color), anchor="ls")
            cx += wl(wd) + space
        y += lead
    return y_bottom - lead * (len(lines) - 1) - size * 0.75


def _apply_nobreak(words, phrases):
    """Cola com espaço não-quebrável os termos que a marca proíbe quebrar em duas linhas."""
    if not phrases:
        return words
    joined = "\u00a0"
    out, i = [], 0
    lowered = [w[0].lower() for w in words]
    targets = [[t.lower() for t in p.split()] for p in phrases]
    while i < len(words):
        hit = next((t for t in targets if lowered[i:i + len(t)] == t), None)
        if hit:
            n = len(hit)
            out.append((joined.join(w[0] for w in words[i:i + n]), any(w[1] for w in words[i:i + n])))
            i += n
        else:
            out.append(words[i])
            i += 1
    return out


def tracked(draw, xy, text, font, fill, track, anchor="l"):
    total = sum(font.getlength(c) for c in text) + track * (len(text) - 1)
    x, y = xy
    x -= {"l": 0, "m": total / 2, "r": total}[anchor]
    for c in text:
        draw.text((x, y), c, font=font, fill=tuple(fill), anchor="ls")
        x += font.getlength(c) + track


def kicker(canvas, x, y, text, size, info_spec, color=(255, 255, 255),
           accent=(255, 158, 0), anchor="l", dot=True):
    draw = ImageDraw.Draw(canvas)
    if anchor == "l":
        avail = canvas.width * 0.96 - x - size * 1.4
        while size > 10 and sum(ft(info_spec, size).getlength(c) for c in text.upper()) \
                + size * 0.18 * (len(text) - 1) > avail:
            size -= 1
    font = ft(info_spec, size)
    off = 0
    if dot:
        r = size * 0.32
        cx = x if anchor == "l" else x - (
            sum(font.getlength(c) for c in text.upper()) + size * 0.18 * (len(text) - 1)) / 2 - r * 2.4
        draw.ellipse([cx, y - size * 0.5 - r, cx + 2 * r, y - size * 0.5 + r], fill=tuple(accent))
        off = 2 * r + size * 0.5 if anchor == "l" else 0
    tracked(draw, (x + off, y), text.upper(), font, color, size * 0.18, anchor)


def cta_text(canvas, x, y, size, label, info_spec, color=(255, 255, 255),
             accent=(255, 158, 0), align="l", arrow="→", underline=True):
    draw = ImageDraw.Draw(canvas)
    font = ft(info_spec, size)
    label = f"{label}  {arrow}" if arrow else label
    if align == "m":
        x -= font.getlength(label) / 2
    draw.text((x, y), label, font=font, fill=tuple(color), anchor="ls")
    if underline:
        lw = font.getlength(label)
        draw.rectangle([x, y + size * 0.3, x + lw, y + size * 0.3 + max(2, size * 0.09)], fill=tuple(accent))


# ---------------------------------------------------------------- folhas de contato
def contact_sheet(paths, out_path, thumb_h=420, cols=None, bg=(225, 228, 232), pad=12):
    """Grade de miniaturas com altura normalizada — serve para revisão em lote."""
    thumbs = []
    for p in paths:
        t = Image.open(p).convert("RGB")
        thumbs.append(t.resize((max(1, round(t.width * thumb_h / t.height)), thumb_h), LANCZOS))
    if not thumbs:
        return None
    cols = cols or len(thumbs)
    rows = [thumbs[i:i + cols] for i in range(0, len(thumbs), cols)]
    width = max(sum(t.width for t in r) + pad * (len(r) + 1) for r in rows)
    height = len(rows) * (thumb_h + pad) + pad
    sheet = Image.new("RGB", (width, height), bg)
    for i, r in enumerate(rows):
        x = pad
        for t in r:
            sheet.paste(t, (x, pad + i * (thumb_h + pad)))
            x += t.width + pad
    sheet.save(out_path, "PNG", optimize=True)
    return out_path