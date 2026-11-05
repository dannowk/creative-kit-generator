"""Interpretador de specs de template: layers declarativas -> primitivas.

O vocabulário de `op` é exatamente o conjunto de primitivas que já existia no motor CDI.
Posições aceitam aritmética sobre w/h/scale/m/top/bottom, avaliada com AST restrito —
spec de marca é dado, não código, e não pode executar nada arbitrário.
"""

import ast
import operator
import os

import yaml
from PIL import Image

from . import primitives as P

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow}

OPS = ("canvas", "paper", "photo", "paste", "grade", "fade_to", "light_leak", "film_texture",
       "multiply", "halftone", "rule", "logo", "text", "kicker", "cta", "tracked")
# Ops que pintam fundo/imagem: pulados no modo overlay (só marca/texto sobre transparência).
BG_OPS = {"canvas", "paper", "photo", "paste", "grade", "fade_to", "light_leak",
          "film_texture", "multiply", "halftone"}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"round": round, "min": min, "max": max, "abs": abs, "int": int, "float": float}
_CMP = {ast.Lt: operator.lt, ast.Gt: operator.gt, ast.LtE: operator.le,
        ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


def evaluate(expr, vars_):
    """Avalia número ou expressão aritmética sobre as variáveis de geometria."""
    if isinstance(expr, (int, float)):
        return expr
    if expr is None:
        return 0
    node = ast.parse(str(expr), mode="eval").body
    return _ev(node, vars_)


def _ev(node, v):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in v:
            return v[node.id]
        raise KeyError(f"Variável desconhecida no spec: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        return _BIN[type(node.op)](_ev(node.left, v), _ev(node.right, v))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_ev(node.operand, v))
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP:
        return _CMP[type(node.ops[0])](_ev(node.left, v), _ev(node.comparators[0], v))
    if isinstance(node, ast.IfExp):
        return _ev(node.body, v) if _ev(node.test, v) else _ev(node.orelse, v)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_ev(a, v) for a in node.args])
    raise ValueError(f"Expressão não permitida em spec: {ast.dump(node)}")


def load_spec(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _layers(spec, geo):
    variants = spec.get("variants") or {}
    key = "wide" if geo["wide"] else "portrait"
    if geo["tight"] and "tight" in variants:
        key = "tight"
    branch = variants.get(key) or {}
    return branch.get("layers") or spec.get("layers") or [], branch.get("vars") or spec.get("vars") or {}


def _ref(value, ctx):
    """copy.hook / program / cta -> texto do contexto da campanha.
    Ref de copy não resolvido vira vazio, nunca o caminho literal na peça."""
    if value is None:
        return ""
    cur = ctx
    for part in str(value).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return "" if str(value).startswith("copy.") else str(value)
    return cur if isinstance(cur, str) else str(cur)


def render(spec, brand, geo, photo=None, fx=0.5, logo=None, copy=None, extra=None, trace=None,
           transparent=False):
    """Renderiza uma peça. `photo` é a imagem já aberta; `fx` o centro do sujeito (0..1).

    Se `trace` for um dict, recebe a caixa do rosto e os retângulos de cada elemento —
    é o que permite ao compliance provar que nada cobriu o sujeito.

    `transparent=True` devolve só a marca/texto sobre RGBA transparente (overlay de
    vídeo): pula os ops de fundo/imagem e não achata em RGB.
    """
    copy = copy or {}
    trace = trace if trace is not None else {}
    trace.setdefault("elements", [])
    ctx = {"copy": copy, **(extra or {})}
    for k in ("cta", "program", "campus", "brand_name", "disclaimer"):
        if k not in ctx:
            ctx[k] = copy.get(k, brand.data.get(k, ""))

    w, h = geo["w"], geo["h"]
    if transparent:
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGB", (w, h), brand.color(spec.get("background", "black")))
    surface = None
    last_photo = {}

    logo_w = logo_h = 0
    if logo is not None:
        small = P.sized_logo(logo, round(geo["scale"] * brand.logo_scale))
        logo_w, logo_h = small.width, small.height

    v = {"w": w, "h": h, "scale": geo["scale"], "m": geo["m"], "top": geo["top"],
         "bottom": geo["bottom"], "logo_w": logo_w, "logo_h": logo_h,
         "ratio": h / w, "ar": w / h,
         "pi": 3.141592653589793, "true": 1, "false": 0}

    def pos(expr, default=(0, 0)):
        if expr is None:
            return default
        if isinstance(expr, str):
            named = {"margin": (v["m"], v["m"]),
                     "top_left": (v["m"], v["top"]),
                     "bottom_left": (v["m"], v["bottom"]),
                     "bottom_right": (w - v["m"] - logo_w, v["bottom"] - logo_h),
                     "center": (w / 2, h / 2)}
            if expr in named:
                return named[expr]
            raise ValueError(f"Posição nomeada desconhecida: {expr}")
        return tuple(evaluate(x, v) for x in expr)

    def surface_for(layer):
        if transparent:
            return canvas
        return surface if layer.get("target") == "photo" else canvas

    layers, spec_vars = _layers(spec, geo)
    for name, expr in spec_vars.items():
        v[name] = evaluate(expr, v)

    for layer in layers:
        op = layer.get("op")
        if op is None:
            continue
        if transparent and op in BG_OPS:
            continue

        if op == "canvas":
            canvas = Image.new("RGB", (w, h), brand.color(layer.get("color", "black")))

        elif op == "paper":
            canvas = P.paper(w, h, base=brand.color(layer.get("color", "paper"))).convert("RGBA")

        elif op == "photo":
            if photo is None:
                continue
            last_photo = layer
            size = layer.get("size") or [w, h]
            pw, ph = (round(evaluate(size[0], v)), round(evaluate(size[1], v)))
            fit = layer.get("fit", "cover")
            if fit == "closeup":
                surface = P.closeup(photo, pw, ph, fx, layer.get("zoom", 0.74),
                                    face_at=layer.get("face_at", 0.38),
                                    fx_at=layer.get("fx_at", 0.5),
                                    face_y=layer.get("face_y", 0.27))
            elif fit == "subject":
                surface = P.crop(photo, pw, ph, fx, subject_at=layer.get("subject_at", 0.5))
            else:
                surface = P.resize_and_crop(photo, (pw, ph))
            if layer.get("at") is not None:
                at = tuple(round(x) for x in pos(layer["at"]))
                canvas.paste(surface, at)
                _record_face(trace, layer, at, pw, ph, fx)
                surface = None

        elif op == "paste":
            if surface is not None:
                at = tuple(round(x) for x in pos(layer.get("at", [0, 0])))
                canvas.paste(surface, at)
                _record_face(trace, last_photo, at, surface.width, surface.height, fx)
                surface = None

        elif op == "grade":
            g = P.grade(surface_for(layer).convert("RGB"), vignette=layer.get("vignette", 0.45),
                        grain=layer.get("grain", 7))
            if layer.get("target") == "photo":
                surface = g
            else:
                canvas = g

        elif op == "fade_to":
            g = P.fade_to(surface_for(layer).convert("RGB"), brand.color(layer.get("color", "dark")),
                          layer.get("start", 0.5), layer.get("end", 0.8),
                          horizontal=layer.get("horizontal", False), flip=layer.get("flip", False))
            if layer.get("target") == "photo":
                surface = g
            else:
                canvas = g

        elif op == "light_leak":
            g = P.light_leak(surface_for(layer).convert("RGB"), corner=layer.get("corner", "tl"),
                             strength=layer.get("strength", 0.35),
                             color=tuple(c / 255 for c in brand.color(layer["color"])) if layer.get("color")
                             else (1.0, 0.5, 0.1))
            if layer.get("target") == "photo":
                surface = g
            else:
                canvas = g

        elif op == "film_texture":
            g = P.film_texture(surface_for(layer).convert("RGB"), grain=layer.get("grain", 6),
                               dust=layer.get("dust", 1.0))
            if layer.get("target") == "photo":
                surface = g
            else:
                canvas = g.convert("RGBA")

        elif op == "multiply":
            base = target(layer).convert("RGBA")
            if layer.get("image"):
                ov = Image.open(brand.asset_path(layer["image"])).convert("RGBA")
                ov = P.resize_and_crop(ov, base.size)
                g = P.multiply_overlay(base, ov)
            else:
                g = P.multiply_color(base, brand.color(layer.get("color", "primary")),
                                     alpha=layer.get("alpha", 1.0))
            if layer.get("target") == "photo":
                surface = g
            else:
                canvas = g

        elif op == "halftone":
            size = layer.get("size") or ["round(w*0.5)", "round(h*0.3)"]
            hw, hh = round(evaluate(size[0], v)), round(evaluate(size[1], v))
            tile = P.halftone((hw, hh), layer.get("corner", "br"),
                              brand.color(layer.get("color", "accent")),
                              opacity=layer.get("opacity", 0.45))
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at")) if layer.get("at") is not None else _corner_at(layer.get("corner", "br"), w, h, hw, hh)
            canvas.alpha_composite(tile, (round(at[0]), round(at[1])))

        elif op == "rule":
            canvas = canvas.convert("RGBA")
            from PIL import ImageDraw
            y = round(evaluate(layer.get("y", 0), v))
            t = max(1, round(evaluate(layer.get("thickness", "max(4, round(h*0.006))"), v)))
            ImageDraw.Draw(canvas).rectangle([0, y, w, y + t], fill=brand.color(layer.get("color", "accent")))

        elif op == "logo":
            if logo is None:
                continue
            src = P.ink_logo(logo, brand.color(layer.get("ink"), brand.palette.get("ink", (17, 24, 32)))) \
                if layer.get("ink") else logo
            small = P.sized_logo(src, round(geo["scale"] * layer.get("scale", brand.logo_scale)),
                                 canvas=(w, h) if layer.get("caps") else None)
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at", "bottom_right"))
            canvas.alpha_composite(small, (round(at[0]), round(at[1])))
            trace["elements"].append({"op": "logo",
                                      "box": (at[0], at[1], at[0] + small.width, at[1] + small.height)})

        elif op == "text":
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at", ["m", "bottom"]))
            width = evaluate(layer.get("width", "w - 2*m"), v)
            max_h = evaluate(layer.get("max_h", "h*0.3"), v)
            size = evaluate(layer.get("size", "round(scale*0.105)"), v)
            style = brand.fonts.style(layer.get("style", "display"))
            for knob in ("underline", "accent_upper", "accent_scale"):
                if knob in layer:
                    style[knob] = layer[knob]
            style["nobreak"] = [c.get("text", []) for c in brand.compliance
                                if c.get("check") == "nobreak"]
            style["nobreak"] = [t for group in style["nobreak"] for t in
                                (group if isinstance(group, list) else [group])]
            text = _ref(layer.get("ref"), ctx)
            text_color = brand.color(layer.get("color", "white"))
            region = (max(0, round(at[0])), max(0, round(at[1] - max_h)),
                      min(w, round(at[0] + width)), min(h, round(at[1])))
            under = None
            if region[2] > region[0] and region[3] > region[1]:
                import numpy as np
                under = tuple(int(c) for c in np.asarray(
                    canvas.convert("RGB").crop(region)).reshape(-1, 3).mean(axis=0))
            metrics = {}
            top = P.draw_copy(canvas, at[0], at[1], width, max_h, text, size,
                              text_color, style,
                              align=layer.get("align", "left"),
                              accent=brand.color(layer.get("accent", "accent")),
                              min_size=layer.get("min_size", 14), max_lines=layer.get("max_lines", 4),
                              metrics=metrics)
            trace["elements"].append({"op": "text", "box": (at[0], top, at[0] + width, at[1]),
                                      "text": text, "color": text_color, "under": under,
                                      "size": metrics.get("size", size)})

        elif op == "kicker":
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at", ["m", "top"]))
            P.kicker(canvas, at[0], at[1], _ref(layer.get("ref"), ctx),
                     evaluate(layer.get("size", "round(scale*0.026)"), v),
                     brand.fonts.spec(layer.get("font", "text")),
                     color=brand.color(layer.get("color", "white")),
                     accent=brand.color(layer.get("accent", "accent")),
                     anchor=layer.get("anchor", "l"), dot=layer.get("dot", True))

        elif op == "cta":
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at", ["m", "bottom"]))
            P.cta_text(canvas, at[0], at[1], evaluate(layer.get("size", "round(scale*0.034)"), v),
                       _ref(layer.get("ref", "cta"), ctx), brand.fonts.spec(layer.get("font", "text")),
                       color=brand.color(layer.get("color", "white")),
                       accent=brand.color(layer.get("accent", "accent")),
                       align=layer.get("align", "l"), arrow=layer.get("arrow", "→"),
                       underline=layer.get("underline", True))

        elif op == "tracked":
            from PIL import ImageDraw
            canvas = canvas.convert("RGBA")
            at = pos(layer.get("at", ["m", "bottom"]))
            size = evaluate(layer.get("size", "round(scale*0.02)"), v)
            text = _ref(layer.get("ref"), ctx)
            if layer.get("upper", True):
                text = text.upper()
            font = P.ft(brand.fonts.spec(layer.get("font", "text")), size)
            P.tracked(ImageDraw.Draw(canvas), at, text, font,
                      brand.color(layer.get("color", "white")),
                      evaluate(layer.get("track", "scale*0.004"), v), layer.get("anchor", "l"))

        else:
            raise ValueError(f"op desconhecido no spec '{spec.get('id')}': {op}")

    return canvas.convert("RGBA") if transparent else canvas.convert("RGB")


def _corner_at(corner, w, h, tw, th):
    x = 0 if "l" in corner else w - tw
    y = 0 if "t" in corner else h - th
    return (x, y)


def _record_face(trace, layer, at, pw, ph, fx):
    """Onde o rosto caiu no canvas. No closeup o sujeito é posicionado de propósito em
    fx_at/face_at, então a caixa é conhecida sem precisar detectar nada de novo."""
    if not layer:
        return
    fit = layer.get("fit", "cover")
    if fit == "closeup":
        cx = at[0] + layer.get("fx_at", 0.5) * pw
        cy = at[1] + layer.get("face_at", 0.38) * ph
    elif fit == "subject":
        cx = at[0] + layer.get("subject_at", 0.5) * pw
        cy = at[1] + 0.27 * ph
    else:
        cx, cy = at[0] + fx * pw, at[1] + 0.27 * ph
    trace["face_box"] = (cx - 0.11 * pw, cy - 0.12 * ph, cx + 0.11 * pw, cy + 0.14 * ph)
    trace["photo_rect"] = (at[0], at[1], at[0] + pw, at[1] + ph)