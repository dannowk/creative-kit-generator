"""Base content from the content team's spreadsheet.

Normalize pattern: the kit parses + validates, the agent adapts per the briefing
rules, the kit applies. One row = one base copy; `use` routes it (image/ppc/both).
"""

import csv
import json
import os

COLUMNS = ("concept", "axis", "hook", "kicker", "program", "cta", "use", "lang")
ALIASES = {
    "conceito": "concept", "eixo": "axis", "gancho": "hook", "chamada": "hook",
    "headline": "hook", "apoio": "kicker", "subtitulo": "kicker",
    "programa": "program", "oferta": "program", "uso": "use", "destino": "use",
    "idioma": "lang", "locale": "lang",
}
USES = ("image", "ppc", "both")
SHEET_EXT = (".xlsx", ".csv")


def _norm_header(h):
    h = str(h or "").strip().lower()
    return ALIASES.get(h, h)


def _rows_from_dicts(dicts):
    rows = []
    for raw in dicts:
        row = {}
        for k, v in raw.items():
            key = _norm_header(k)
            if key in COLUMNS and v is not None and str(v).strip() != "":
                row[key] = str(v).strip()
        if not row:
            continue
        row.setdefault("use", "both")
        rows.append(row)
    return rows


def read_sheet(path):
    """Canonical rows from .xlsx/.csv. Empty cells dropped; blank use = both."""
    low = path.lower()
    if low.endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            return _rows_from_dicts(list(csv.DictReader(f)))
    if low.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            it = wb.active.iter_rows(values_only=True)
            headers = [_norm_header(h) for h in next(it, ())]
            dicts = [dict(zip(headers, vals)) for vals in it]
        finally:
            wb.close()
        return _rows_from_dicts(dicts)
    raise ValueError(f"unsupported sheet extension: {path} (use .xlsx or .csv)")


def validate(rows, concepts):
    """Row-level errors (PT — agent contract). Empty list = appliable."""
    errs = []
    for i, r in enumerate(rows, 1):
        if not r.get("concept"):
            errs.append(f"linha {i}: concept vazio")
        elif r["concept"] not in concepts:
            errs.append(f"linha {i}: conceito não declarado: {r['concept']}")
        if not r.get("hook"):
            errs.append(f"linha {i}: hook vazio")
        if r.get("use", "both") not in USES:
            errs.append(f"linha {i}: use inválido: {r.get('use')} (image/ppc/both)")
    return errs


def find_sheet(root):
    d = os.path.join(root, "content")
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(SHEET_EXT):
            return os.path.join(d, f)
    return None


def ingest(camp):
    """Parse + validate the sheet into <campaign>/content.json. Touches nothing else."""
    root = camp["_root"]
    sheet = find_sheet(root)
    link_path = os.path.join(root, "content", "content_link.txt")
    link = ""
    if os.path.isfile(link_path):
        with open(link_path, encoding="utf-8") as f:
            link = f.read().strip()
    rows, gaps = [], []
    if sheet:
        rows = read_sheet(sheet)
    elif link:
        gaps.append("link presente, arquivo ausente — o agente baixa a planilha uma vez "
                    "e salva em content/ antes de rodar content de novo")
    else:
        gaps.append("sem planilha em content/ — passo opcional; o copy manual segue valendo")
    errors = validate(rows, camp.get("concepts") or []) if rows else []
    out = {"source": {"file": os.path.relpath(sheet, root) if sheet else None, "link": link},
           "rows": rows, "gaps": gaps, "errors": errors}
    with open(os.path.join(root, "content.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return {"file": out["source"]["file"], "link": link, "rows": len(rows),
            "gaps": gaps, "errors": errors}


def _entry(row):
    e = {k: row[k] for k in ("hook", "kicker", "program", "cta", "lang") if row.get(k)}
    e["use"] = row.get("use", "both")
    return e


def apply(camp):
    """Re-validate content.json and merge rows into campaign.json.copy.

    First row per (axis, concept) = base entry; further rows = versions.
    Existing copy entries not covered by the sheet are preserved.
    """
    root = camp["_root"]
    cj_path = os.path.join(root, "content.json")
    if not os.path.isfile(cj_path):
        return {"errors": ["content.json ausente — rode content primeiro"], "merged": 0}
    with open(cj_path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    errors = validate(rows, camp.get("concepts") or [])
    if errors:
        return {"errors": errors, "merged": 0}
    camp_path = os.path.join(root, "campaign.json")
    with open(camp_path, encoding="utf-8") as f:
        campj = json.load(f)
    copy = campj.setdefault("copy", {})
    merged = 0
    for row in rows:
        key = row.get("axis") or "default"
        concept = row["concept"]
        entry = _entry(row)
        slot = copy.setdefault(key, {}).setdefault(concept, {})
        if not slot.get("hook"):
            slot.update(entry)
            merged += 1
        else:
            slot.setdefault("versions", []).append(entry)
    with open(camp_path, "w", encoding="utf-8") as f:
        json.dump(campj, f, indent=2, ensure_ascii=False)
    return {"errors": [], "merged": merged}