"""Export PPC: planilhas de bulk upload (Meta + Google) a partir da campanha renderizada.

Determinístico: cada peça aprovada (criativo + copy) vira uma linha nas colunas de
import em lote de cada plataforma. CSV (import direto) + XLSX (revisão no Excel/Sheets).
O que só o time de PPC sabe — URL final, orçamento, targeting, objetivo, IDs de
Page/Pixel/Instagram — fica como coluna rotulada em branco. O manifesto lista todas as
peças com plataforma, tamanho, conceito, caminho do arquivo e copy.

Meta: Ads Manager → Import/Export → Import Ads in Bulk (CSV ou XLSX).
Google Search (RSA) e Display: Google Ads Editor (CSV) ou Bulk actions → Uploads (CSV/XLSX).
"""

import csv
import os
import re

from . import campaign as C
from . import formats

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    _HAS_XLSX = True
except ImportError:
    _HAS_XLSX = False

META_COLUMNS = [
    "Campaign ID", "Campaign Name", "Campaign Objective", "Campaign Status", "Buying Type",
    "Campaign Daily Budget", "Ad Set ID", "Ad Set Name", "Ad Set Daily Budget", "Ad Set Run Status",
    "Optimization Goal", "Billing Event", "Countries", "Placements", "Ad ID", "Ad Name", "Ad Status",
    "Creative Type", "Image File Name", "Video File Name", "Title", "Body", "Link Description",
    "Call to Action", "Link", "Display Link", "URL Tags", "Instagram Account ID", "Link Object ID",
]
RSA_COLUMNS = (["Campaign", "Ad group", "Ad type"]
               + [f"Headline {i}" for i in range(1, 16)]
               + [f"Description {i}" for i in range(1, 5)]
               + ["Path 1", "Path 2", "Final URL", "Status"])
DISPLAY_COLUMNS = [
    "Campaign", "Ad group", "Ad type", "Headline", "Long headline", "Description",
    "Business name", "Final URL", "Path 1", "Path 2", "Status",
    "Image file", "Logo file", "Size", "Concept", "Placement",
]
MANIFEST_COLUMNS = [
    "Piece ID", "Platform", "Format", "Size", "Concept", "Axes", "Kind", "Status",
    "Creative file", "Delivery path", "Hook", "Kicker", "Program", "CTA",
]

_WRAP = {"Body", "Title", "Link Description", "Headline", "Long headline", "Description",
         "Hook", "Kicker", "Program"} | {f"Headline {i}" for i in range(1, 16)} \
        | {f"Description {i}" for i in range(1, 5)}

_CTA = [("demo", "LEARN_MORE"), ("sign up", "SIGN_UP"), ("signup", "SIGN_UP"),
        ("register", "SIGN_UP"), ("subscribe", "SUBSCRIBE"), ("download", "DOWNLOAD"),
        ("quote", "GET_QUOTE"), ("contact", "CONTACT_US"), ("call", "CALL_NOW"),
        ("apply", "APPLY_NOW"), ("shop", "SHOP_NOW"), ("buy", "SHOP_NOW"),
        ("order", "SHOP_NOW"), ("book", "BOOK_TRAVEL"), ("watch", "WATCH_VIDEO"),
        ("learn", "LEARN_MORE"), ("get", "GET_OFFER")]


def _clean(text):
    return re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]", r"\1", str(text or ""))).strip()


def _trunc(text, n):
    t = _clean(text)
    if len(t) <= n:
        return t
    cut = t[:n]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut).rstrip()


def _cta_enum(cta):
    c = _clean(cta).lower()
    return next((v for k, v in _CTA if k in c), "LEARN_MORE")


def _copy_for(camp, combo, concept):
    copy = C.lookup(camp.get("copy") or {}, combo) or {}
    if isinstance(copy, str):
        copy = {"hook": copy}
    voice = copy.get(concept)
    merged = {**copy, **voice} if isinstance(voice, dict) else copy
    return {"hook": _clean(merged.get("hook", "")),
            "kicker": _clean(merged.get("kicker", "")),
            "program": _clean(merged.get("program") or C.lookup(camp.get("labels"), combo) or ""),
            "cta": _clean(merged.get("cta", camp.get("cta", "Learn more")))}


def _campaign_name(camp, brand):
    return camp.get("campaign_name") or f"{brand.name} | {camp.get('slug', 'campaign').replace('-', ' ').title()}"


def _adgroup(concept, combo):
    return " | ".join([concept] + [str(v) for v in combo.values()])


def _size(fmt):
    w, h = formats.FORMATS.get(fmt, {}).get("size", (0, 0))
    return f"{w}x{h}"


def _channel(fmt):
    return formats.FORMATS.get(fmt, {}).get("channel", "")


def _creative_basename(piece):
    return os.path.basename(piece.get("delivery_path") or piece["path"])


def _meta_placement(fmt):
    if fmt == "meta_story":
        return "Facebook Stories, Instagram Stories, Facebook Reels, Instagram Reels"
    if fmt == "meta_landscape":
        return "Facebook Feed, Instagram Feed, Audience Network"
    return "Facebook Feed, Instagram Feed"


def _dedup(seq):
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


def _meta_rows(pieces, camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    rows = []
    for p in pieces:
        copy = _copy_for(camp, p.get("axes", {}), p["concept"])
        row = {c: "" for c in META_COLUMNS}
        row.update({"Campaign Name": cname, "Campaign Status": "PAUSED", "Buying Type": "AUCTION",
                    "Ad Set Name": _adgroup(p["concept"], p.get("axes", {})), "Ad Set Run Status": "PAUSED",
                    "Placements": _meta_placement(p["format"]), "Ad Name": p["id"], "Ad Status": "PAUSED",
                    "Creative Type": "Link Page Post Ad", "Title": _trunc(copy["program"] or copy["hook"], 40),
                    "Body": copy["hook"], "Link Description": _trunc(copy["kicker"], 30),
                    "Call to Action": _cta_enum(copy["cta"]), "Link": url})
        row["Video File Name" if p.get("kind") == "video" else "Image File Name"] = _creative_basename(p)
        rows.append(row)
    return rows


def _display_rows(pieces, camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    logo = os.path.basename(brand.logo_path) if brand.logo_path else ""
    rows = []
    for p in pieces:
        copy = _copy_for(camp, p.get("axes", {}), p["concept"])
        row = {c: "" for c in DISPLAY_COLUMNS}
        row.update({"Campaign": cname, "Ad group": _adgroup(p["concept"], p.get("axes", {})),
                    "Ad type": "Responsive display ad", "Headline": _trunc(copy["program"] or copy["hook"], 30),
                    "Long headline": _trunc(copy["hook"], 90), "Description": _trunc(copy["kicker"] or copy["hook"], 90),
                    "Business name": brand.name, "Final URL": url, "Status": "Paused",
                    "Image file": _creative_basename(p), "Logo file": logo, "Size": _size(p["format"]),
                    "Concept": p["concept"], "Placement": "Google Display Network"})
        rows.append(row)
    return rows


def _rsa_rows(pieces, camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    seen, combos = set(), []
    for p in pieces:
        combo = p.get("axes", {})
        key = (p["concept"], tuple(sorted(combo.items())))
        if key not in seen:
            seen.add(key)
            combos.append((p["concept"], combo))
    rows = []
    for concept, combo in combos:
        copy = _copy_for(camp, combo, concept)
        headlines = [_trunc(x, 30) for x in _dedup(
            [copy["program"], copy["kicker"], copy["hook"], copy["cta"], brand.name])]
        descriptions = [_trunc(x, 90) for x in _dedup(
            [copy["hook"], " ".join(x for x in [copy["kicker"], copy["program"]] if x),
             " — ".join(x for x in [copy["cta"], copy["program"]] if x)])]
        row = {c: "" for c in RSA_COLUMNS}
        row.update({"Campaign": cname, "Ad group": _adgroup(concept, combo),
                    "Ad type": "Responsive search ad", "Status": "Paused",
                    "Path 1": _trunc(camp.get("slug", ""), 15), "Path 2": _trunc(concept, 15),
                    "Final URL": url})
        for i, h in enumerate(headlines[:15], 1):
            row[f"Headline {i}"] = h
        for i, d in enumerate(descriptions[:4], 1):
            row[f"Description {i}"] = d
        rows.append(row)
    return rows


def _manifest_rows(pieces, camp, brand):
    rows = []
    for p in pieces:
        copy = _copy_for(camp, p.get("axes", {}), p["concept"])
        rows.append({"Piece ID": p["id"], "Platform": _channel(p["format"]), "Format": p["format"],
                     "Size": _size(p["format"]), "Concept": p["concept"],
                     "Axes": "; ".join(f"{k}={v}" for k, v in p.get("axes", {}).items()),
                     "Kind": p.get("kind", "image"), "Status": p.get("status", ""),
                     "Creative file": os.path.join("out", p["path"]),
                     "Delivery path": p.get("delivery_path", ""),
                     "Hook": copy["hook"], "Kicker": copy["kicker"], "Program": copy["program"], "CTA": copy["cta"]})
    return rows


def _write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def _write_xlsx(path, columns, rows, title):
    if not _HAS_XLSX:
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(columns)
    head_font = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    head_fill = PatternFill("solid", start_color="0B6BCB")
    for cell in ws[1]:
        cell.font = head_font
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    body_font = Font(name="Arial", size=11)
    for row in rows:
        ws.append([row.get(c, "") for c in columns])
    for r in ws.iter_rows(min_row=2):
        for cell in r:
            cell.font = body_font
            cell.alignment = Alignment(vertical="top", wrap_text=columns[cell.column - 1] in _WRAP)
    for i, c in enumerate(columns, 1):
        longest = max([len(c)] + [len(str(row.get(c, ""))) for row in rows[:200]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(longest + 2, 12), 46)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)
    return True


_NOTES = {
    "pt": """PLANILHAS DE BULK UPLOAD — time de PPC
=======================================
Arquivos (cada um em CSV e XLSX):
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk.
  google_search_rsa  → Google Ads Editor (CSV) ou Bulk actions → Uploads. Responsive Search Ads.
  google_display     → Google Ads Editor / Uploads. Responsive Display Ads (texto + referências de criativo).
  creative_manifest  → referência humana: cada peça com plataforma, tamanho, conceito, arquivo e copy.

Já preenchido pelo kit: nomes de campanha/ad set/ad, criativo (nome do arquivo), copy
(hook/primary text, headline, description), CTA, placements e tamanho.

Falta o time de PPC preencher (colunas em branco):
  - URL final (Link / Final URL), Display Link e URL Tags (UTM).
  - Objetivo da campanha, orçamento, optimization goal, billing event, países/targeting.
  - IDs: Facebook Page (Link Object ID), Instagram Account ID, Pixel/Conversion (Meta).
  - Google Display: anexar os arquivos de imagem/logo listados (Image file / Logo file) no Editor.

Limites: Google RSA headline ≤ 30 caracteres (até 15), description ≤ 90 (até 4), path ≤ 15.
Tudo sai PAUSED/Paused para revisão antes de ativar. Confira o copy e os limites antes de importar.
""",
    "en": """BULK-UPLOAD SHEETS — PPC team
=============================
Files (each as CSV and XLSX):
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk.
  google_search_rsa  → Google Ads Editor (CSV) or Bulk actions → Uploads. Responsive Search Ads.
  google_display     → Google Ads Editor / Uploads. Responsive Display Ads (text + creative references).
  creative_manifest  → human reference: each piece with platform, size, concept, file and copy.

Pre-filled by the kit: campaign/ad set/ad names, creative (file name), copy (hook/primary
text, headline, description), CTA, placements and size.

PPC team must fill (blank columns):
  - Final URL (Link / Final URL), Display Link and URL Tags (UTM).
  - Campaign objective, budget, optimization goal, billing event, countries/targeting.
  - IDs: Facebook Page (Link Object ID), Instagram Account ID, Pixel/Conversion (Meta).
  - Google Display: attach the listed image/logo files (Image file / Logo file) in Editor.

Limits: Google RSA headline ≤ 30 chars (up to 15), description ≤ 90 (up to 4), path ≤ 15.
Everything ships PAUSED/Paused for review before going live. Check copy and limits before importing.
""",
}


def export(root, all_pieces=False, lang="pt"):
    """Gera as planilhas em ppc/ na pasta de entrega (Desktop). Devolve um resumo (contagens + arquivos)."""
    state_path = os.path.join(root, "state.json")
    if not os.path.isfile(state_path):
        return {"dir": os.path.join(C.delivery_dir(root), "ppc"), "files": [], "meta": 0,
                "google_display": 0, "google_rsa": 0, "manifest": 0, "xlsx": _HAS_XLSX}
    import json
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    camp = C.load_campaign(root)
    brand = C.brand_for(camp)
    pieces = [p for p in state.get("pieces", [])
              if all_pieces or p.get("status") == "approved"]
    meta = [p for p in pieces if _channel(p["format"]) == "meta"]
    google = [p for p in pieces if _channel(p["format"]) == "google"]
    channels = camp.get("channels") or []
    want_meta = bool(meta) or "meta" in channels
    want_google = bool(google) or "google" in channels

    outdir = os.path.join(C.delivery_dir(root), "ppc")
    os.makedirs(outdir, exist_ok=True)
    files, counts = [], {"meta": 0, "google_display": 0, "google_rsa": 0, "manifest": 0}

    def emit(stem, columns, rows, title, key):
        if not rows:
            return
        _write_csv(os.path.join(outdir, stem + ".csv"), columns, rows)
        files.append(stem + ".csv")
        if _write_xlsx(os.path.join(outdir, stem + ".xlsx"), columns, rows, title):
            files.append(stem + ".xlsx")
        counts[key] = len(rows)

    if want_meta:
        emit("meta_bulk_import", META_COLUMNS, _meta_rows(meta, camp, brand), "Meta bulk import", "meta")
    if want_google:
        emit("google_display", DISPLAY_COLUMNS, _display_rows(google, camp, brand), "Google Display", "google_display")
        emit("google_search_rsa", RSA_COLUMNS, _rsa_rows(pieces, camp, brand), "Google Search RSA", "google_rsa")
    emit("creative_manifest", MANIFEST_COLUMNS, _manifest_rows(pieces, camp, brand), "Creative manifest", "manifest")

    notes = os.path.join(outdir, "README.txt")
    with open(notes, "w", encoding="utf-8") as f:
        f.write(_NOTES.get(lang, _NOTES["en"]))
    files.append("README.txt")
    return {"dir": outdir, "files": files, "xlsx": _HAS_XLSX, **counts}