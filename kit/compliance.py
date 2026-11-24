"""Rule checking before export. Brand-agnostic vocabulary.

Each brand.yaml rule becomes an executable check — rules that today only exist as
prose in the handoff now actually block the piece.
"""

import numpy as np

from . import i18n


def _overlap(a, b):
    if not a or not b:
        return 0.0
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    area = max(1, (b[2] - b[0]) * (b[3] - b[1]))
    return inter / area


def _luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _num(rule, key, default):
    """A rule value that is missing OR null (`tolerance:` left empty in YAML) → default.

    Without this, an empty field reaches the comparison as None and the render crashes.
    """
    v = rule.get(key)
    if v is None or isinstance(v, bool):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def check_subject_safe(img, trace, rule, brand):
    face = trace.get("face_box")
    if not face:
        return []
    tolerance = _num(rule, "tolerance", 0.02)
    out = []
    for el in trace.get("elements", []):
        if el["op"] not in ("text", "logo"):
            continue
        frac = _overlap(el["box"], face)
        if frac > tolerance:
            out.append({"check": "subject_safe", "level": "fail",
                        "message": i18n.t("cmp.subject_safe", op=el["op"], frac=frac, tol=tolerance)})
    return out


def check_palette_forbidden(img, trace, rule, brand):
    if not brand.forbidden:
        return []
    small = img.convert("RGB").resize((min(400, img.width), min(400, img.height)))
    a = np.asarray(small).reshape(-1, 3).astype(np.int16)
    threshold = _num(rule, "tolerance", 40)
    min_area = _num(rule, "min_area", 0.005)
    out = []
    for color in brand.forbidden:
        dist = np.abs(a - np.array(color, dtype=np.int16)).sum(axis=1)
        frac = float((dist < threshold).mean())
        if frac > min_area:
            out.append({"check": "palette_forbidden", "level": "fail",
                        "message": i18n.t("cmp.palette_forbidden", color=tuple(color),
                                          frac=frac, min_area=min_area)})
    return out


def check_min_font_size(img, trace, rule, brand):
    minimum = _num(rule, "px", 0)
    relative = _num(rule, "scale", 0)
    out = []
    for el in trace.get("elements", []):
        if el["op"] != "text":
            continue
        floor = max(minimum, relative * trace.get("scale", 0))
        if floor and el.get("size", 999) < floor:
            out.append({"check": "min_font_size", "level": "fail",
                        "message": i18n.t("cmp.min_font_size", size=el["size"], floor=floor,
                                          text=el.get("text", "")[:40] + "…")})
    return out


def check_contrast_min(img, trace, rule, brand):
    minimum = _num(rule, "ratio", 4.5)
    out = []
    for el in trace.get("elements", []):
        if el["op"] != "text" or not el.get("under"):
            continue
        ratio = contrast_ratio(el["color"], el["under"])
        if ratio < minimum:
            out.append({"check": "contrast_min", "level": "warn",
                        "message": i18n.t("cmp.contrast_min", ratio=ratio, minimum=minimum,
                                          text=el.get("text", "")[:30] + "…")})
    return out


def check_disclaimer_required(img, trace, rule, brand):
    required = rule.get("text", "")
    if not required:
        return []
    haystack = " ".join(el.get("text", "") for el in trace.get("elements", []))
    when = rule.get("when_text")
    if when and str(when).lower() not in haystack.lower():
        return []
    if required.lower() not in haystack.lower():
        return [{"check": "disclaimer_required", "level": "fail",
                 "message": i18n.t("cmp.disclaimer_required", text=required)}]
    return []


def check_nobreak(img, trace, rule, brand):
    """The no-break is applied at draw time; here we only confirm the term is in the copy."""
    terms = rule.get("text", [])
    terms = terms if isinstance(terms, list) else [terms]
    haystack = " ".join(el.get("text", "") for el in trace.get("elements", []))
    return [{"check": "nobreak", "level": "info",
             "message": i18n.t("cmp.nobreak", t=t)}
            for t in terms if t.lower() in haystack.lower()]


CHECKS = {
    "subject_safe": check_subject_safe,
    "palette_forbidden": check_palette_forbidden,
    "min_font_size": check_min_font_size,
    "contrast_min": check_contrast_min,
    "disclaimer_required": check_disclaimer_required,
    "nobreak": check_nobreak,
}


def run(img, trace, brand):
    """Return the findings list. 'fail' blocks export; 'warn' and 'info' only report."""
    trace = dict(trace, scale=(img.width * img.height) ** 0.5)
    findings = []
    for rule in brand.compliance:
        fn = CHECKS.get(rule.get("check"))
        if fn is None:
            findings.append({"check": rule.get("check"), "level": "warn",
                             "message": i18n.t("cmp.unknown", check=rule.get("check"))})
            continue
        findings += fn(img, trace, rule, brand)
    return findings


def blocked(findings):
    return any(f["level"] == "fail" for f in findings)