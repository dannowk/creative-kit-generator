"""Copy Kit — independent copy skill (text only: PPC + overlay).

Normalize pattern: the agent generates copy from the briefing + examples, the kit
validates the shape and exports only what is approved. Independent of the visual kit
(never touches campaign/render/ppc). One row = one copy (destination ppc/overlay ×
concept × axis × kind). English-only.
"""

import json
import os
from datetime import datetime, timezone

DESTINATIONS = ("ppc", "overlay")
KINDS = {
    "ppc": ("headline", "description", "primary_text"),
    "overlay": ("hook", "kicker", "program", "cta"),
}
STATUSES = ("pending", "approved", "rejected", "redo")
LANGS = ("en",)
ORIGINS = ("agent", "sheet")
USES = ("image", "ppc", "both")


def _path(root):
    return os.path.join(root, "copy.json")


def load(root):
    with open(_path(root), encoding="utf-8") as f:
        return json.load(f)


def save(root, data):
    with open(_path(root), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_id(rows):
    used = {r.get("id") for r in rows}
    n = 1
    while f"k{n:02d}" in used:
        n += 1
    return f"k{n:02d}"


def validate(data):
    """Per-row errors (the agent contract). Empty list = appliable."""
    errs = []
    concepts = data.get("concepts") or []
    if not isinstance(concepts, list) or any(not str(c).strip() for c in concepts):
        errs.append("concepts: invalid or empty concept list")
    seen = set()
    for i, r in enumerate(data.get("rows") or [], 1):
        rid = r.get("id")
        if not rid:
            errs.append(f"row {i}: empty id")
        elif rid in seen:
            errs.append(f"row {i}: duplicate id: {rid}")
        else:
            seen.add(rid)
        dest = r.get("destination")
        if dest not in DESTINATIONS:
            errs.append(f"row {i}: invalid destination: {dest!r} (ppc/overlay)")
        elif r.get("kind") not in KINDS[dest]:
            errs.append(f"row {i}: invalid kind for {dest}: {r.get('kind')!r} "
                        f"({'/'.join(KINDS[dest])})")
        if not str(r.get("text") or "").strip():
            errs.append(f"row {i}: empty text")
        if concepts and r.get("concept") not in concepts:
            errs.append(f"row {i}: undeclared concept: {r.get('concept')!r}")
        if r.get("lang") not in LANGS:
            errs.append(f"row {i}: invalid lang: {r.get('lang')!r} (en)")
        if r.get("status") not in STATUSES:
            errs.append(f"row {i}: invalid status: {r.get('status')!r}")
        if r.get("origin") not in ORIGINS:
            errs.append(f"row {i}: invalid origin: {r.get('origin')!r}")
        if r.get("use", "both") not in USES:
            errs.append(f"row {i}: invalid use: {r.get('use')!r} (image/ppc/both)")
    return errs


def decide(root, row_id, status, note="", who=""):
    """Mark a row (intent). Writes status/note + stamp. False if the id is unknown.

    redo requires a note. approve/reject clear the note. The agent never calls approved —
    the decision belongs to the user in the table.
    """
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")
    if status == "redo" and not str(note).strip():
        raise ValueError("redo requires a note (what to adjust)")
    data = load(root)
    found = False
    for r in data.get("rows") or []:
        if r.get("id") == row_id:
            r["status"] = status
            if status == "redo":
                r["note"] = note
            else:
                r.pop("note", None)
            r["updated_at"] = now_iso()
            if who:
                r["updated_by"] = who
            found = True
            break
    if found:
        save(root, data)
    return found


def review_payload(root):
    """{rows, counts} for the review table, or None without copy.json."""
    if not os.path.isfile(_path(root)):
        return None
    rows = load(root).get("rows") or []
    counts = {s: sum(1 for r in rows if r.get("status") == s) for s in STATUSES}
    return {"rows": rows, "counts": counts}


BRIEF_TEMPLATE = """# Copy briefing

## 1. Objective
(what the campaign wants to achieve)

## 2. Audience
(who you speak to, pain/desire)

## 3. Tone of voice
(how the brand speaks — e.g. direct, warm, technical)

## 4. Offer / product
(what is advertised, differentiator, price if any)

## 5. Destinations
- PPC (text only): Meta / Google Search
- Overlay: hook / kicker / program / CTA over the piece

## 6. Concepts
(comma-separated list — e.g. clean, editorial)

## 7. Axes (optional)
(variations — e.g. urgency, benefit)

## 8. Constraints
- Google RSA: headline ≤ 30 chars, description ≤ 90
- CTA: short verb
- (other rules)

## 9. Languages
en
"""

EXAMPLES_HEADER = ("# Paste example texts here (copy you like / want to use as a model).\n"
                   "# One per line or block. The agent uses this + the briefing to generate copy.\n\n")


def scaffold(folder):
    """Lean copy folder: briefing.md + examples.txt (no logo/brandbook/refs).

    Does not overwrite existing files. Returns the briefing path.
    """
    os.makedirs(folder, exist_ok=True)
    brief = os.path.join(folder, "briefing.md")
    if not os.path.isfile(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(BRIEF_TEMPLATE)
    examples = os.path.join(folder, "examples.txt")
    if not os.path.isfile(examples):
        with open(examples, "w", encoding="utf-8") as f:
            f.write(EXAMPLES_HEADER)
    return brief


def read_text(folder, name):
    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def delivery_dir(root):
    """~/Desktop/Copy Kit/<folder>/ — same convention as the visual kit, outside the working folder."""
    from .campaign import desktop_dir, _slug
    name = _slug(os.path.basename(os.path.abspath(root)))
    return os.path.join(desktop_dir(), "Copy Kit", name)


OVERLAY_COLUMNS = ["Concept", "Axis", "Lang", "Hook", "Kicker", "Program", "CTA"]
MANIFEST_COLUMNS = ["ID", "Destination", "Concept", "Axis", "Kind", "Text", "Lang", "Chars"]


def _groups(rows):
    seen, out = set(), []
    for r in rows:
        key = (r.get("concept"), r.get("axis") or "", r.get("lang"))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _texts(rows, concept, axis, lang, kind):
    return [r.get("text") for r in rows
            if r.get("concept") == concept and (r.get("axis") or "") == axis
            and r.get("lang") == lang and r.get("kind") == kind]


def _adset(concept, axis):
    return " | ".join(x for x in [concept, axis] if x)


def _meta_rows(rows, name):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        head = _texts(rows, concept, axis, lang, "headline")
        prim = _texts(rows, concept, axis, lang, "primary_text")
        desc = _texts(rows, concept, axis, lang, "description")
        row = {c: "" for c in ppc.META_COLUMNS}
        row.update({"Campaign Name": name, "Campaign Status": "PAUSED",
                    "Ad Set Name": _adset(concept, axis), "Ad Set Run Status": "PAUSED",
                    "Ad Name": f"{_adset(concept, axis)} ({lang})", "Ad Status": "PAUSED",
                    "Title": ppc._trunc(head[0] if head else "", 40),
                    "Body": ppc._clean(prim[0] if prim else ""),
                    "Link Description": ppc._trunc(desc[0] if desc else "", 30)})
        out.append(row)
    return out


def _rsa_rows(rows, name):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        heads = [ppc._trunc(t, 30) for t in ppc._dedup(_texts(rows, concept, axis, lang, "headline"))]
        descs = [ppc._trunc(t, 90) for t in ppc._dedup(_texts(rows, concept, axis, lang, "description"))]
        row = {c: "" for c in ppc.RSA_COLUMNS}
        row.update({"Campaign": name, "Ad group": _adset(concept, axis),
                    "Ad type": "Responsive search ad", "Status": "Paused"})
        for i, h in enumerate(heads[:15], 1):
            row[f"Headline {i}"] = h
        for i, d in enumerate(descs[:4], 1):
            row[f"Description {i}"] = d
        out.append(row)
    return out


def _overlay_rows(rows):
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        def first(kind):
            t = _texts(rows, concept, axis, lang, kind)
            return ppc._clean(t[0]) if t else ""
        out.append({"Concept": concept, "Axis": axis, "Lang": lang,
                    "Hook": first("hook"), "Kicker": first("kicker"),
                    "Program": first("program"), "CTA": first("cta")})
    return out


def _manifest_rows(rows):
    from . import ppc
    return [{"ID": r.get("id"), "Destination": r.get("destination"), "Concept": r.get("concept"),
             "Axis": r.get("axis") or "", "Kind": r.get("kind"), "Text": ppc._clean(r.get("text")),
             "Lang": r.get("lang"), "Chars": len(ppc._clean(r.get("text")))} for r in rows]


_NOTES = """COPY KIT — APPROVED COPY
========================
Files (each as CSV and XLSX):
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk (text only).
  google_search_rsa  → Google Ads Editor / Bulk actions → Uploads. Responsive Search Ads.
  overlay            → copy over the piece: hook / kicker / program / CTA per concept × axis.
  copy_manifest      → human reference: every approved row (destination, concept, kind, text, chars).

Only APPROVED copy ships. Final URL, budget, targeting and IDs are left blank for the PPC
team. Everything ships PAUSED/Paused. Google RSA limits: headline ≤ 30, description ≤ 90
(the export truncates and warns which rows exceeded — check before importing).
"""


def export(root):
    """Export only approved rows → sheets (Meta/RSA/overlay/manifest) in the Desktop folder.

    Deterministic; reuses the visual ppc writers/columns. RSA limits become warnings,
    not gatekeepers. Returns a summary (counts + files + warnings).
    """
    from . import ppc
    rows = [r for r in load(root).get("rows") or [] if r.get("status") == "approved"]
    outdir = delivery_dir(root)
    os.makedirs(outdir, exist_ok=True)
    name = os.path.basename(os.path.abspath(root)).replace("-", " ").title()
    files, warnings = [], []
    counts = {"meta": 0, "google_rsa": 0, "overlay": 0, "manifest": 0}

    def emit(stem, columns, data, title, key):
        if not data:
            return
        ppc._write_csv(os.path.join(outdir, stem + ".csv"), columns, data)
        files.append(stem + ".csv")
        if ppc._write_xlsx(os.path.join(outdir, stem + ".xlsx"), columns, data, title):
            files.append(stem + ".xlsx")
        counts[key] = len(data)

    ppc_rows = [r for r in rows if r.get("destination") == "ppc"]
    ov_rows = [r for r in rows if r.get("destination") == "overlay"]
    for r in ppc_rows:
        limit = {"headline": 30, "description": 90}.get(r.get("kind"))
        n = len(ppc._clean(r.get("text")))
        if limit and n > limit:
            warnings.append({"id": r.get("id"), "kind": r.get("kind"), "chars": n, "limit": limit})

    emit("meta_bulk_import", ppc.META_COLUMNS, _meta_rows(ppc_rows, name), "Meta bulk import", "meta")
    emit("google_search_rsa", ppc.RSA_COLUMNS, _rsa_rows(ppc_rows, name), "Google Search RSA", "google_rsa")
    emit("overlay", OVERLAY_COLUMNS, _overlay_rows(ov_rows), "Overlay", "overlay")
    emit("copy_manifest", MANIFEST_COLUMNS, _manifest_rows(rows), "Copy manifest", "manifest")

    with open(os.path.join(outdir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(_NOTES)
    files.append("README.txt")
    return {"dir": outdir, "files": files, "xlsx": ppc._HAS_XLSX, "warnings": warnings, **counts}


def deliver(root):
    """The copy 'Continue': exports approved rows to the Desktop folder + download."""
    empty = {"dir": delivery_dir(root), "files": [], "exported": 0, "xlsx": False,
             "warnings": [], "meta": 0, "google_rsa": 0, "overlay": 0, "manifest": 0}
    if not os.path.isfile(_path(root)):
        return empty
    approved = sum(1 for r in load(root).get("rows") or [] if r.get("status") == "approved")
    if approved == 0:
        return empty
    s = export(root)
    s["exported"] = approved
    return s