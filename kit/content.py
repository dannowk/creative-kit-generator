"""Base content from the content team's spreadsheet.

Normalize pattern: the kit parses + validates, the agent adapts per the briefing
rules, the kit applies. One row = one base copy; `use` routes it (image/ppc/both).
"""

import csv
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