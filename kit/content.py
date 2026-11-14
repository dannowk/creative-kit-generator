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
STATUSES = ("pending", "approved", "rejected", "redo")
ORIGINS = ("sheet", "agent")


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


def _stamp(rows):
    """Sheet rows are the team's own copy: trusted (approved), sequential ids."""
    for i, r in enumerate(rows, 1):
        r["id"] = f"c{i:02d}"
        r["origin"] = "sheet"
        r["status"] = "approved"
    return rows


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
        if r.get("status") not in STATUSES:
            errs.append(f"linha {i}: status ausente ou inválido: {r.get('status')!r} — rode content de novo")
        if r.get("origin") not in ORIGINS:
            errs.append(f"linha {i}: origin ausente ou inválido: {r.get('origin')!r} — rode content de novo")
    return errs


_SAMPLE_ROWS = {
    "pt": [
        ("clean", "", "Sua semana, planejada em minutos.", "NOVO", "Teste grátis por 14 dias", "Começar grátis", "both", "pt"),
        ("clean", "", "Chega de abas abertas. Comece a entregar.", "NOVO", "Teste grátis por 14 dias", "Experimente agora", "both", "pt"),
        ("clean", "urgencia", "Última chamada: preço de lançamento acaba sexta.", "LIMITADO", "Oferta de lançamento", "Aproveitar", "image", "pt"),
        ("editorial", "", "A história por trás da sua agenda.", "", "", "Saiba mais", "ppc", "pt"),
        ("cinema", "beneficio", "Veja sua semana sob outra luz.", "", "", "Assistir", "", "pt"),
    ],
    "en": [
        ("clean", "", "Your week, planned in minutes.", "NEW", "Free 14-day trial", "Start free", "both", "en"),
        ("clean", "", "Stop juggling tabs. Start shipping.", "NEW", "Free 14-day trial", "Try it now", "both", "en"),
        ("clean", "urgency", "Last call: launch pricing ends Friday.", "LIMITED", "Launch offer", "Get the deal", "image", "en"),
        ("editorial", "", "The story behind your calendar.", "", "", "Read more", "ppc", "en"),
        ("cinema", "benefit", "See your week in a new light.", "", "", "Watch now", "", "en"),
    ],
}
_SAMPLE_NOTES = {
    "pt": {"concept": "obrigatório — um dos conceitos pedidos no briefing (seção 7)",
           "axis": "opcional — eixo da campanha; linhas repetidas (mesmo concept+axis) viram versões",
           "hook": "obrigatório — texto principal da peça",
           "use": "image = só nas peças · ppc = só nas planilhas · both/vazio = ambos",
           "lang": "opcional — pt ou en",
           "_ex": "referência: preencha a aba Modelo — o kit lê a primeira aba"},
    "en": {"concept": "required — one of the concepts requested in the briefing (section 7)",
           "axis": "optional — campaign axis; repeated rows (same concept+axis) become versions",
           "hook": "required — main text of the piece",
           "use": "image = pieces only · ppc = spreadsheets only · both/blank = both",
           "lang": "optional — pt or en",
           "_ex": "reference: fill the Template tab — the kit reads the first tab"},
}


def sample_xlsx(lang="pt"):
    """Modelo .xlsx para o time de conteúdo: aba limpa + aba de exemplos."""
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    key = "pt" if lang == "pt" else "en"
    notes = _SAMPLE_NOTES[key]
    wb = Workbook()
    tpl = wb.active
    tpl.title = "Modelo" if key == "pt" else "Template"
    ex = wb.create_sheet("Exemplos" if key == "pt" else "Examples")
    for ws in (tpl, ex):
        ws.append(list(COLUMNS))
        for c in ws[1]:
            c.font = Font(bold=True)
        for i, w in enumerate((12, 12, 46, 12, 26, 18, 8, 6), 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
    for col, text in notes.items():
        target = ex["A1"] if col == "_ex" else tpl.cell(row=1, column=COLUMNS.index(col) + 1)
        target.comment = Comment(text, "campaign-kit")
    for row in _SAMPLE_ROWS[key]:
        ex.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
        rows = _stamp(read_sheet(sheet))
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
    """Merge only approved rows into campaign.json.copy (the single review gate).

    First approved row per (axis, concept) = base entry; further approved rows =
    versions in row order. Unrelated existing copy entries are preserved.
    `pending` counts rows not approved (still awaiting review/agent).
    """
    root = camp["_root"]
    cj_path = os.path.join(root, "content.json")
    if not os.path.isfile(cj_path):
        return {"errors": ["content.json ausente — rode content primeiro"],
                "merged": 0, "pending": 0}
    with open(cj_path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    pending = sum(1 for r in rows if r.get("status") != "approved")
    errors = validate(rows, camp.get("concepts") or [])
    if errors:
        return {"errors": errors, "merged": 0, "pending": pending}
    camp_path = os.path.join(root, "campaign.json")
    with open(camp_path, encoding="utf-8") as f:
        campj = json.load(f)
    copy = campj.setdefault("copy", {})
    merged = 0
    for row in rows:
        if row.get("status") != "approved":
            continue
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
    return {"errors": [], "merged": merged, "pending": pending}


def _load_rows(root):
    with open(os.path.join(root, "content.json"), encoding="utf-8") as f:
        return json.load(f)


def _save_rows(root, data):
    with open(os.path.join(root, "content.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def decide(root, row_id, status, note=""):
    """Mark one row (UI/import). Writes only status/note. False if id unknown."""
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status}")
    data = _load_rows(root)
    found = False
    for r in data.get("rows") or []:
        if r.get("id") == row_id:
            r["status"] = status
            if note:
                r["note"] = note
            else:
                r.pop("note", None)
            found = True
            break
    if found:
        _save_rows(root, data)
    return found


def review_payload(root):
    """{rows, counts} for the review /state, or None without content.json."""
    path = os.path.join(root, "content.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    counts = {s: sum(1 for r in rows if r.get("status") == s) for s in STATUSES}
    return {"rows": rows, "counts": counts}