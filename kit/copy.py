"""Copy Kit — independent copy skill (text only: PPC + overlay).

Normalize pattern: the agent generates copy from the briefing + examples, the kit
validates the shape and exports only what is approved. Independent of the visual kit
(never touches campaign/render/ppc). One row = one copy (destination ppc/overlay ×
concept × axis × kind). English-only.
"""

import json
import os
import threading
from datetime import datetime, timezone

# The review table serves concurrently: without this, two fast clicks read-modify-write
# copy.json in parallel and the second decision clobbers the first.
_LOCK = threading.Lock()

DESTINATIONS = ("ppc", "overlay")
KINDS = {
    "ppc": ("headline", "description", "primary_text", "link_description", "cta"),
    "overlay": ("hook", "kicker", "program", "cta"),
}
PLATFORMS = ("google", "meta", "both")
LIMITS = {"headline": 30, "description": 90, "link_description": 40}
VOLUME = {
    "google": {"headline": 15, "description": 4},
    "meta": {"primary_text": 5, "headline": 5, "link_description": 5},
}
STATUSES = ("pending", "approved", "rejected", "redo")
LANGS = ("en",)
ORIGINS = ("agent", "sheet")
USES = ("image", "ppc", "both")

PLATFORM_RULES = """  platform playbook (ppc rows carry platform: google | meta | both):
    GOOGLE RSA — per concept × axis: 15 headlines (≤30 chars each) + 4 descriptions (≤90).
      Aim for Ad Strength "Excellent": work the main Google Ads keywords naturally into the
      headlines, spread the angles (direct benefit / differentiator + authority / strong CTA)
      and avoid repeating the same words across headlines (diversity score).
    META — per concept × axis: exactly 5 primary_text + 5 headline (≤30) + 5 link_description
      (≤30–40). The hook (pain / desire / promise) must land in the FIRST 90–125 chars of each
      primary_text — before the "See more" cut on mobile. Feed-stop angle: storytelling +
      solid argument. Add one cta row with the recommended native Meta button
      (e.g. "Learn More", "Sign Up", "Subscribe").
    After authoring, write at the TOP LEVEL of copy.json: "strategy_note" (how the Google Ads
    terms were used and which angles break the scroll) and "meta_cta" (recommended native
    button for the campaign)."""


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
        if dest == "ppc" and r.get("platform", "both") not in PLATFORMS:
            errs.append(f"row {i}: invalid platform: {r.get('platform')!r} (google/meta/both)")
        if r.get("program") is not None and not isinstance(r.get("program"), str):
            errs.append(f"row {i}: program must be a string (the advertised program/product)")
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
    with _LOCK:
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
- Google RSA: 15 headlines ≤ 30 chars + 4 descriptions ≤ 90 per concept × axis
  (keywords in the headlines, varied angles, no repeated words — Ad Strength "Excellent")
- Meta: 5 primary texts (hook in the first 90–125 chars) + 5 headlines ≤ 30 +
  5 link descriptions ≤ 40 per concept × axis
- CTA: short verb; recommended native Meta button (e.g. "Learn More", "Sign Up")
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


ATTACH_DIR = "attachments"


def attach_dir(root):
    return os.path.join(root, ATTACH_DIR)


def save_attachment(root, name, data):
    """Save a dropped/picked file in <root>/attachments/. Returns the stored name
    (suffix added on collision)."""
    name = os.path.basename(str(name)).strip() or "file"
    d = attach_dir(root)
    os.makedirs(d, exist_ok=True)
    dest = os.path.join(d, name)
    n = 2
    while os.path.exists(dest):
        stem, ext = os.path.splitext(name)
        dest = os.path.join(d, f"{stem} ({n}){ext}")
        n += 1
    with open(dest, "wb") as f:
        f.write(data)
    return os.path.basename(dest)


def remove_attachment(root, name):
    p = os.path.join(attach_dir(root), os.path.basename(str(name)))
    if os.path.isfile(p):
        os.remove(p)
        return True
    return False


def attachments(root):
    """[{name, size}] sorted by name — what the wizard lists and `copy plan` prints."""
    d = attach_dir(root)
    if not os.path.isdir(d):
        return []
    return sorted(({"name": n, "size": os.path.getsize(os.path.join(d, n))}
                   for n in os.listdir(d) if os.path.isfile(os.path.join(d, n))),
                  key=lambda a: a["name"])


def delivery_dir(root):
    """~/Desktop/Copy Kit/<folder>/ — same convention as the visual kit, outside the working folder."""
    from .campaign import desktop_dir, _slug
    name = _slug(os.path.basename(os.path.abspath(root)))
    return os.path.join(desktop_dir(), "Copy Kit", name)


OVERLAY_COLUMNS = ["Concept", "Program", "Platform", "Variation", "Type", "Text", "Chars"]
MANIFEST_COLUMNS = ["ID", "Concept", "Program", "Platform", "Destination",
                    "Variation", "Type", "Text", "Chars", "Lang"]

TYPE_LABELS = {
    "headline": "Headline (≤30)",
    "description": "Description (≤90)",
    "primary_text": "Primary text (Meta)",
    "link_description": "Link description (Meta)",
    "cta": "CTA button",
    "hook": "Hook (big line)",
    "kicker": "Kicker (small line above)",
    "program": "Program line",
}

PLATFORM_LABELS = {"google": "Google", "meta": "Meta", "both": "Google + Meta"}


def type_label(kind):
    return TYPE_LABELS.get(kind, kind or "")


def platform_label(row):
    if row.get("destination") != "ppc":
        return "Overlay (on the piece)"
    return PLATFORM_LABELS.get(row.get("platform", "both"), "Google + Meta")


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
    rows = [r for r in rows if r.get("platform", "both") in ("meta", "both")]
    out = []
    for concept, axis, lang in _groups(rows):
        prim = _texts(rows, concept, axis, lang, "primary_text")
        head = _texts(rows, concept, axis, lang, "headline")
        link = (_texts(rows, concept, axis, lang, "link_description")
                or _texts(rows, concept, axis, lang, "description"))
        cta = _texts(rows, concept, axis, lang, "cta")
        n = max(len(prim), len(head), len(link), 1)

        def pick(lst, v):
            if not lst:
                return ""
            return lst[v] if v < len(lst) else lst[v % len(lst)]

        for v in range(n):
            row = {c: "" for c in ppc.META_COLUMNS}
            row.update({"Campaign Name": name, "Campaign Status": "PAUSED",
                        "Ad Set Name": _adset(concept, axis), "Ad Set Run Status": "PAUSED",
                        "Ad Name": _adset(concept, axis) + f" ({lang})" + (f" v{v + 1}" if n > 1 else ""),
                        "Ad Status": "PAUSED",
                        "Title": ppc._trunc(pick(head, v), 40),
                        "Body": ppc._clean(pick(prim, v)),
                        "Link Description": ppc._trunc(pick(link, v), 40),
                        "Call to Action": ppc._clean(cta[0]) if cta else ""})
            out.append(row)
    return out


def _rsa_rows(rows, name):
    from . import ppc
    rows = [r for r in rows if r.get("platform", "both") in ("google", "both")]
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
    """Verticalized: one text per row (easier to approve), labeled by concept + program."""
    from . import ppc
    out = []
    for concept, axis, lang in _groups(rows):
        for r in rows:
            if r.get("destination") != "overlay" or r.get("concept") != concept \
                    or (r.get("axis") or "") != axis or r.get("lang") != lang:
                continue
            text = ppc._clean(r.get("text"))
            out.append({"Concept": concept, "Program": r.get("program") or "",
                        "Platform": "Overlay (on the piece)",
                        "Variation": axis or "", "Type": type_label(r.get("kind")),
                        "Text": text, "Chars": len(text)})
    return out


def _manifest_rows(rows):
    """Every approved text on its own row — the vertical approval sheet for all copy."""
    from . import ppc
    out = []
    for r in rows:
        text = ppc._clean(r.get("text"))
        out.append({"ID": r.get("id"), "Concept": r.get("concept"),
                    "Program": r.get("program") or "",
                    "Platform": platform_label(r),
                    "Destination": r.get("destination"), "Variation": r.get("axis") or "",
                    "Type": type_label(r.get("kind")), "Text": text, "Chars": len(text),
                    "Lang": r.get("lang")})
    return out


def volume_report(rows):
    """Per-group volume notes against the platform playbook (targets, not errors)."""
    out = []
    for concept, axis, lang in _groups(rows):
        ppc = [r for r in rows if r.get("destination") == "ppc"
               and r.get("concept") == concept and (r.get("axis") or "") == axis
               and r.get("lang") == lang]
        grp = " | ".join(x for x in [concept, axis] if x) or "(group)"
        for plat in ("google", "meta"):
            side = [r for r in ppc if r.get("platform", "both") in (plat, "both")]
            for kind, want in VOLUME[plat].items():
                n = sum(1 for r in side if r.get("kind") == kind)
                if n < want:
                    out.append(f"{grp} ({lang}) · {plat} {kind}: {n}/{want}")
    return out


_NOTES = """COPY KIT — APPROVED COPY
========================
Files (each as CSV and XLSX):
  copy_manifest      → APPROVAL SHEET: every approved text on its own row, labeled with
                       Concept, Program, Platform and Type (Headline / Primary text / Hook…).
  overlay            → APPROVAL SHEET for the text over the piece: one line per text
                       (hook / kicker / program line / CTA), labeled by Concept + Program.
  meta_bulk_import   → Meta Ads Manager → Import/Export → Import Ads in Bulk (text only).
                       Kept in Meta's own column layout so the import works.
  google_search_rsa  → Google Ads Editor / Bulk actions → Uploads. Responsive Search Ads.
                       Kept in Google's own column layout (Headline 1–15, Description 1–4)
                       so the upload works.

Read/approve in copy_manifest (vertical, one text per row); upload with the Meta/Google files.
Only APPROVED copy ships. Final URL, budget, targeting and IDs are left blank for the PPC
team. Everything ships PAUSED/Paused.

Platform playbook the copy was authored under:
  Google RSA — 15 headlines (≤ 30 chars) + 4 descriptions (≤ 90) per concept × axis,
    keywords worked into the headlines, varied angles, Ad Strength "Excellent".
  Meta — 5 primary texts (hook in the first 90–125 chars, before "See more") +
    5 headlines (≤ 30) + 5 link descriptions (≤ 40) per concept × axis, one ad per variation.
Limits exceeded become a warning + truncation on export (check before importing).
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
        limit = LIMITS.get(r.get("kind"))
        n = len(ppc._clean(r.get("text")))
        if limit and n > limit:
            warnings.append({"id": r.get("id"), "kind": r.get("kind"), "chars": n, "limit": limit})

    emit("copy_manifest", MANIFEST_COLUMNS, _manifest_rows(rows), "Copy manifest (approval)", "manifest")
    emit("overlay", OVERLAY_COLUMNS, _overlay_rows(ov_rows), "Overlay (approval)", "overlay")
    emit("meta_bulk_import", ppc.META_COLUMNS, _meta_rows(ppc_rows, name), "Meta bulk import", "meta")
    emit("google_search_rsa", ppc.RSA_COLUMNS, _rsa_rows(ppc_rows, name), "Google Search RSA", "google_rsa")

    with open(os.path.join(outdir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(_NOTES)
    files.append("README.txt")
    return {"dir": outdir, "files": files, "xlsx": ppc._HAS_XLSX, "warnings": warnings, **counts}


def deliver(root):
    """The copy 'Continue': exports approved rows to the Desktop folder + download.

    Gated: while any row is still rejected/redo (the agent is rewriting it), nothing
    exports — all changes must be done first. Returns {"locked": n} in that case.
    """
    empty = {"dir": delivery_dir(root), "files": [], "exported": 0, "xlsx": False,
             "warnings": [], "locked": 0, "meta": 0, "google_rsa": 0, "overlay": 0, "manifest": 0}
    if not os.path.isfile(_path(root)):
        return empty
    rows = load(root).get("rows") or []
    working = sum(1 for r in rows if r.get("status") in ("rejected", "redo"))
    if working:
        return {**empty, "locked": working}
    approved = sum(1 for r in rows if r.get("status") == "approved")
    if approved == 0:
        return empty
    s = export(root)
    s["exported"] = approved
    s["locked"] = 0
    return s