"""Campaign: structured briefing -> matrix of pieces in distinct folders.

The axes (product, region, audience, language) replace the hardcoded regions×programs:
the cartesian product and the file name come from brand.yaml, not from code.
"""

import copy
import itertools
import json
import os
import glob
import re
import shutil
import sys
from datetime import datetime, timezone

import yaml
from PIL import Image

from . import compliance, formats, primitives as P, render, rules
from .brand import Brand, load_brand

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(ROOT, "templates")
STYLES_DIR = "styles"


def load_campaign(path):
    if os.path.isdir(path):
        path = os.path.join(path, "campaign.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["_root"] = os.path.dirname(os.path.abspath(path))
    return rules.apply(data, data["_root"], "campaign")


def brand_for(campaign, brands_dir=None):
    brands_dir = brands_dir or os.path.join(ROOT, "brands")
    brand = load_brand(os.path.join(brands_dir, campaign["brand"]))
    root = campaign.get("_root")
    return rules.brand_for(root, brand) if root else brand


def expand_axes(brand, campaign):
    """Cartesian product of the axes declared in the briefing (or the brand's, if omitted)."""
    declared = campaign.get("axes")
    if declared:
        names = list(declared)
        values = [declared[n] for n in names]
    else:
        specs = brand.axes
        names = [a["name"] for a in specs]
        values = [brand.axis_values(a) for a in specs]
    names = [n for n, v in zip(names, values) if v]
    values = [v for v in values if v]
    if not names:
        return [{}]
    return [dict(zip(names, combo)) for combo in itertools.product(*values)]


def lookup(mapping, combo):
    """Accepts a key by the whole combo ('BC|Course-02'), by a single value, or 'default'."""
    if not mapping:
        return None
    joined = "|".join(str(combo[k]) for k in sorted(combo))
    for key in (joined, *combo.values(), "default"):
        if key in mapping:
            return mapping[key]
    return None


def axis_suffix(combo):
    """'angle-urgency_locale-en' — the axes in a file-name-safe form ('' when there are none)."""
    return "_".join(f"{k}-{re.sub(r'[^A-Za-z0-9]+', '-', str(v)).strip('-')}"
                    for k, v in sorted((combo or {}).items()))


def piece_name(brand, campaign, combo, concept, format_name, n=1):
    axes = axis_suffix(combo)
    fields = {"slug": campaign.get("slug", "campaign"), "concept": concept,
              "size": formats.label(format_name), "format": format_name,
              "n": n, "V": f"V{n}", "brand": brand.id,
              "axes": f"_{axes}" if axes else "",
              "axis": axes,
              "locale": combo.get("locale", campaign.get("locale", brand.locale_default))}
    fields.update(combo)
    pattern = campaign.get("naming") or brand.naming
    return pattern.format_map(_Safe(fields))


def unique_name(name, combo, used):
    """A pattern that ignores the axes makes every variation resolve to the same file, so
    they silently overwrite each other. When that happens, append the axes (then a counter).
    """
    if name not in used:
        used.add(name)
        return name
    axes = axis_suffix(combo)
    cand = f"{name}_{axes}" if axes and axes not in name else name
    base, n = cand, 2
    while cand in used:
        cand = f"{base}_{n}"
        n += 1
    used.add(cand)
    return cand


class _Safe(dict):
    def __missing__(self, key):
        return key


def load_subject_overrides(campaign):
    """Replaces the hand-measured face table: intake/agent writes the center per file."""
    p = os.path.join(campaign["_root"], "assets", "subject.json")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def resolve_asset(campaign, combo, overrides):
    rel = lookup(campaign.get("assets"), combo)
    if not rel:
        return None, 0.5, None
    path = rel if os.path.isabs(rel) else os.path.join(campaign["_root"], rel)
    if not os.path.isfile(path):
        matches = glob.glob(path)
        if not matches:
            return None, 0.5, path
        path = sorted(matches)[0]
    base = os.path.basename(path)
    fx = overrides.get(base)
    img = Image.open(path).convert("RGB")
    if fx is None:
        fx = P.subject_center(img)
    return img, fx, path


def available_concepts():
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(TEMPLATES_DIR, "*.yaml")))


def _spec_path(campaign, concept):
    """The campaign spec wins over the global library: art direction comes from this
    campaign's briefing and references, not another brand's archive."""
    local = os.path.join(campaign["_root"], "templates", f"{concept}.yaml")
    return local if os.path.isfile(local) else os.path.join(TEMPLATES_DIR, f"{concept}.yaml")


def style_path(root, concept):
    return os.path.join(root, STYLES_DIR, f"{concept}.yaml")


def load_style(root, concept):
    """Concept style override (palette/typography/note) written by the review.

    Empty if there is no adjustment. Render applies it per concept, so the adjustment
    holds for every piece of that concept and persists across the agent's next renders.
    """
    p = style_path(root, concept)
    if not os.path.isfile(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_style(root, concept, style):
    sp = style_path(root, concept)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as f:
        yaml.safe_dump(style, f, allow_unicode=True, sort_keys=False)


def merge_style(root, concept, pal, typ, note, ids=()):
    """Write the review's adjustment. With ids: per-piece overrides under `pieces:`
    (only those pieces change on the next render). Without: concept-wide, and any
    per-piece overrides are cleared so the whole concept matches again."""
    style = load_style(root, concept)
    fields = {k: v for k, v in (("palette", pal), ("type", typ), ("note", note)) if v}
    if ids:
        pm = style.setdefault("pieces", {})
        for pid in ids:
            if fields:
                pm[pid] = dict(fields)
            else:
                pm.pop(pid, None)
        if not pm:
            style.pop("pieces", None)
    else:
        style.pop("pieces", None)
        for k in ("palette", "type", "note"):
            if k in fields:
                style[k] = fields[k]
            else:
                style.pop(k, None)
    save_style(root, concept, style)
    return style


def piece_style(style, piece_id):
    return (style.get("pieces") or {}).get(piece_id) or {}


MAX_REF = 15 * 1024 * 1024
REF_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")


def refs_dir(root, concept):
    return os.path.join(root, STYLES_DIR, concept, "refs")


def list_refs(root, concept):
    d = refs_dir(root, concept)
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def _set_refs(root, concept):
    style = load_style(root, concept)
    names = list_refs(root, concept)
    if names:
        style["refs"] = names
    else:
        style.pop("refs", None)
    save_style(root, concept, style)


def add_ref(root, concept, name, data, exts=REF_EXT):
    """Save a reference attached in the review under styles/<concept>/refs/ and list it."""
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", os.path.basename(name or "").strip()).strip("-.")
    if not base:
        base = "reference"
    if not base.lower().endswith(exts) or len(data) > MAX_REF:
        raise ValueError(base)
    d = refs_dir(root, concept)
    os.makedirs(d, exist_ok=True)
    stem, ext = os.path.splitext(base)
    saved, n = base, 1
    while os.path.isfile(os.path.join(d, saved)):
        saved, n = f"{stem}-{n}{ext}", n + 1
    with open(os.path.join(d, saved), "wb") as f:
        f.write(data)
    _set_refs(root, concept)
    return saved


def drop_ref(root, concept, name):
    path = os.path.join(refs_dir(root, concept), os.path.basename(name or ""))
    if not os.path.isfile(path):
        return False
    os.remove(path)
    _set_refs(root, concept)
    return True


def styled_brand(brand, style):
    """Brand with the concept's palette/typography merged over the base brand."""
    if not style:
        return brand
    data = copy.deepcopy(brand.data)
    pal = style.get("palette") or {}
    if pal:
        data.setdefault("palette", {}).update(pal)
    typ = style.get("type") or {}
    if typ:
        data.setdefault("type", {}).update(typ)
    return Brand(data, brand.root)


def run(campaign, brand=None, only_concepts=None, only_formats=None, limit=None, dry=False,
        only_ids=None):
    """Render the whole matrix. Returns the state the local UI consumes.

    `only_ids` restricts to the exact piece(s) — used in step 6 for the agent to recreate
    only rejected/redo ones. Previous decisions (approved/delivered) are preserved in the
    merge; re-rendered pieces go back to `pending` for a new review.
    """
    brand = brand or brand_for(campaign)
    root = campaign["_root"]
    out_dir = os.path.join(root, "out")
    names, unknown = formats.resolve_formats(campaign.get("channels", []), campaign.get("formats", []))
    if unknown:
        raise ValueError(f"Unknown format/channel: {', '.join(unknown)}")
    if only_formats:
        names = [n for n in names if n in only_formats]
    concepts = only_concepts or campaign.get("concepts") or available_concepts()
    specs = {c: render.load_spec(_spec_path(campaign, c)) for c in concepts}
    cstyles = {c: load_style(root, c) for c in concepts}
    cbrands = {c: styled_brand(brand, cstyles[c]) for c in concepts}
    pbrands = []

    combos = expand_axes(brand, campaign)
    overrides = load_subject_overrides(campaign)
    logo = Image.open(brand.logo_path).convert("RGBA") if brand.logo_path else None
    copy_map = campaign.get("copy") or {}

    pieces = []
    used_names = set()
    for combo in combos:
        photo, fx, asset_path = resolve_asset(campaign, combo, overrides)
        copy = lookup(copy_map, combo) or {}
        if isinstance(copy, str):
            copy = {"hook": copy}
        extra = {"program": copy.get("program") or lookup(campaign.get("labels"), combo) or "",
                 "campus": copy.get("campus", campaign.get("campus", "")),
                 "cta": copy.get("cta", campaign.get("cta", "Learn more")),
                 "brand_name": brand.name}
        for concept in concepts:
            spec = specs[concept]
            c_photo, c_fx, c_path = photo, fx, asset_path
            by_concept = (campaign.get("assets_by_concept") or {}).get(concept)
            if by_concept:  # foto própria deste conceito (vence a foto do eixo)
                c_photo, c_fx, c_path = resolve_asset({**campaign, "assets": by_concept}, combo, overrides)
            if spec.get("needs_photo") and c_photo is None:
                continue
            voice = copy.get(concept)
            merged = {**copy, **voice} if isinstance(voice, dict) else copy
            if not merged.get("hook"):
                print(f"  no copy.hook for {concept} in {combo or 'campaign'} — concept skipped")
                continue
            for fmt in names:
                name = unique_name(piece_name(brand, campaign, combo, concept, fmt),
                                   combo, used_names)
                if only_ids and name not in only_ids:
                    continue
                geo = formats.geometry(fmt, brand)
                if geo["tight"] and spec.get("needs_photo") and "tight" not in (spec.get("variants") or {}):
                    continue
                trace = {}
                pstyle = piece_style(cstyles[concept], name)
                cb = styled_brand(cbrands[concept], pstyle)
                if pstyle:
                    pbrands.append(cb)
                img = render.render(spec, cb, geo, photo=c_photo, fx=c_fx, logo=logo,
                                    copy=merged, extra=extra, trace=trace)
                findings = compliance.run(img, trace, cb)
                rel = os.path.join(concept, f"{name}.png")
                entry = {"id": name, "path": rel, "concept": concept, "format": fmt,
                         "axes": combo, "asset": os.path.basename(c_path) if c_path else None,
                         "subject_fx": round(c_fx, 4), "findings": findings,
                         "status": "blocked" if compliance.blocked(findings) else "pending"}
                if not dry:
                    dest = os.path.join(out_dir, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    img.save(dest, "PNG", optimize=True)
                    thumb_dir = os.path.join(root, "review", "thumbs", concept)
                    os.makedirs(thumb_dir, exist_ok=True)
                    img.resize((max(1, round(img.width * 360 / img.height)), 360),
                               P.LANCZOS).save(os.path.join(thumb_dir, f"{name}.png"))
                pieces.append(entry)
                if limit and len(pieces) >= limit:
                    break
            if limit and len(pieces) >= limit:
                break
        if limit and len(pieces) >= limit:
            break

    if not dry:
        pieces = _merge_prior(root, pieces)
        _sheets(root, out_dir, pieces)
    for cb in list(cbrands.values()) + pbrands:
        for m in cb.fonts.missing:
            if m not in brand.fonts.missing:
                brand.fonts.missing.append(m)
        for s in cb.fonts.substituted:
            if s not in brand.fonts.substituted:
                brand.fonts.substituted.append(s)
    state = {"campaign": campaign.get("slug"), "brand": brand.id, "root": root,
             "formats": names, "concepts": concepts, "pieces": pieces,
             "blocked_count": sum(1 for p in pieces if p.get("status") == "blocked"),
             "font_warnings": {"missing": brand.fonts.missing, "substituted": brand.fonts.substituted}}
    if not dry:
        with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        sync_requests(root, state)
    return state


def _merge_prior(root, pieces):
    """Preserve review decisions when re-rendering (step 6).

    Approved/delivered stay approved; pieces outside the re-rendered set are kept intact;
    re-rendered ones (recreated rejected/redo) go back to pending without `note`/`queued`,
    for a new review on the same page.
    """
    prior_path = os.path.join(root, "state.json")
    if not os.path.isfile(prior_path):
        return pieces
    with open(prior_path, encoding="utf-8") as f:
        prior = {p["id"]: p for p in json.load(f).get("pieces", [])}
    rendered = {p["id"] for p in pieces}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for p in pieces:
        old = prior.get(p["id"])
        if old and old.get("status") == "approved":
            p["status"] = "approved"
            if old.get("delivered"):
                p["delivered"] = True
            if old.get("delivery_path"):
                p["delivery_path"] = old["delivery_path"]
        elif old and old.get("status") in ("rejected", "redo"):
            p["updated_at"] = now
    for pid, old in prior.items():
        if pid not in rendered:
            pieces.append(old)
    return pieces


def desktop_dir():
    """The user's Desktop (macOS/Windows/Linux), honoring redirection.

    `KIT_DESKTOP_DIR` overrides (tests and non-standard setups). On Windows the Desktop
    may live in OneDrive; on Linux XDG may point to a localized name.
    """
    override = os.environ.get("KIT_DESKTOP_DIR")
    if override:
        return os.path.expanduser(override)
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
                val = os.path.expandvars(winreg.QueryValueEx(k, "Desktop")[0])
            if os.path.isdir(val):
                return val
        except OSError:
            pass
    else:
        xdg = os.path.join(home, ".config", "user-dirs.dirs")
        if os.path.isfile(xdg):
            with open(xdg, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("XDG_DESKTOP_DIR="):
                        val = line.split("=", 1)[1].strip().strip('"').replace("$HOME", home)
                        if os.path.isdir(val):
                            return val
                        break
    return os.path.join(home, "Desktop")


def delivery_dir(root):
    """Delivery folder on the Desktop: ~/Desktop/Campaign Kit/<campaign>/.

    Outside the kit's working folder on purpose: the user finds the final files straight
    on the Desktop. Nothing in the kit reads these files back (merge and PPC use
    `state.json`/`out/`), so moving the delivery here does not break regeneration.
    """
    camp = load_campaign(root)
    name = _slug(camp.get("slug") or os.path.basename(os.path.abspath(root)))
    return os.path.join(desktop_dir(), "Campaign Kit", name)


def pending_batch(state):
    """What the agent must do NOW: every piece still rejected (recreate) or redo (with note)."""
    out = []
    for p in state.get("pieces") or []:
        st = p.get("status")
        if st not in ("rejected", "redo"):
            continue
        out.append({"stage": "pieces", "id": p["id"], "concept": p["concept"],
                    "format": p["format"],
                    "axes": p.get("axes", {}), "path": p["path"],
                    "kind": p.get("kind", "image"), "asset": p.get("asset"),
                    "asset_job": os.path.splitext(p["asset"])[0] if p.get("asset") else None,
                    "reason": "redo" if st == "redo" else "rejected",
                    "note": p.get("note", ""), "marked_at": p.get("decided_at", "")})
    return out


def sync_requests(root, state=None):
    """Keep `requests.json` a derived view of the marked pieces — the agent's work queue.

    Written on every review poll and after every render, so it appears the moment the user
    marks a redo (no need to press Continue) and empties itself when the agent re-renders
    those pieces back to pending. Only rewritten when the content actually changed.
    """
    if state is None:
        path = os.path.join(root, "state.json")
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    batch = pending_batch(state)
    req = os.path.join(root, "requests.json")
    prior = None
    if os.path.isfile(req):
        try:
            with open(req, encoding="utf-8") as f:
                prior = json.load(f)
        except (OSError, ValueError):
            prior = None
    if prior != batch:
        with open(req, "w", encoding="utf-8") as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)
    return batch


def restart(root):
    """The Restart button: stop queued work and clear working output, back to zero.

    Goes: renders (out/, review/), piece decisions, style adjustments and refs (styles/),
    both work queues and the asset decisions (the files and their cost manifest stay).
    Stays: briefing, uploads, templates, campaign.json, generated asset files and the
    delivery folder on the Desktop.
    """
    from . import assets
    for d in ("out", "review", STYLES_DIR):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            shutil.rmtree(p)
    for f in ("requests.json",
              os.path.join(assets.DIR, "state.json"),
              os.path.join(assets.DIR, "requests.json")):
        p = os.path.join(root, f)
        if os.path.isfile(p):
            os.remove(p)
    sp = os.path.join(root, "state.json")
    if os.path.isfile(sp):
        with open(sp, encoding="utf-8") as f:
            state = json.load(f)
        state["pieces"] = []
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)


def wait_batch(root, timeout=0, interval=2.0):
    """Block until there is work, then return the batch (the agent's hook for BOTH stages).

    One trigger for the whole loop: marked assets (`assets/requests.json`, regenerate with the
    provider) and marked pieces (`requests.json`, re-render). A rule proposal the user answered
    in the alarm comes back here too (`stage: rules`), so the agreed override gets re-rendered.
    When nothing is marked but every generated asset is approved and no piece has been rendered
    yet, it returns a single `all_approved` item — that is the signal to run `render` (logos,
    overlays, copy, compliance). `timeout` 0 = wait forever. Returns [] on timeout.
    """
    from . import assets as approval
    import time
    deadline = time.time() + timeout if timeout else None
    while True:
        batch = approval.sync_requests(root) + sync_requests(root)
        if batch:
            return batch
        decided = rules.take_decisions(root)
        if decided:
            return [{"stage": "rules", "reason": p["status"], "id": p["id"], "scope": p["scope"],
                     "target": p["target"], "value": p["value"], "affected": p.get("affected")}
                    for p in decided]
        ok, total = approval.all_approved(root)
        if ok and not os.path.isfile(os.path.join(root, "state.json")):
            return [{"stage": "assets", "reason": "all_approved", "id": None, "count": total}]
        if deadline is not None and time.time() >= deadline:
            return []
        time.sleep(interval)


def deliver(root):
    """Step 7 — the Continue button: exports approved pieces and queues recreation/redo.

    Local and immediate: copies approved pieces from `out/` to the delivery folder on the
    Desktop (`~/Desktop/Campaign Kit/<campaign>/<concept>/`) and marks `delivered`. Rejected
    (recreate) and redo (with the note) become a batch in `requests.json` — regeneration
    belongs to the agent (render is deterministic; the UI never calls MCP). The agent
    recreates/redoes, runs `render --ids` and the review updates itself. With approved
    pieces exported, it also generates the PPC bulk-upload sheets (Meta + Google) in `ppc/`
    inside the same delivery folder.

    Gated: while any piece is still rejected/redo (the agent is working on it), nothing
    exports — all changes must be done first. Returns {"locked": n} in that case.
    """
    with open(os.path.join(root, "state.json"), encoding="utf-8") as f:
        state = json.load(f)
    delivery = delivery_dir(root)
    batch = sync_requests(root, state)
    if batch:
        return {"locked": len(batch), "exported": 0, "regen": 0, "exported_ids": [],
                "delivery_dir": delivery, "requests_path": "requests.json", "batch": batch,
                "ppc": None}
    os.makedirs(delivery, exist_ok=True)
    exported = []
    for p in state["pieces"]:
        if p.get("status") == "approved":
            src = os.path.join(root, "out", p["path"])
            if os.path.isfile(src):
                dest = os.path.join(delivery, p["concept"], os.path.basename(p["path"]))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                p["delivered"] = True
                p["delivery_path"] = dest
                exported.append(p["id"])
    with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    sync_requests(root, state)
    ppc_summary = None
    if exported:
        from . import ppc
        ppc_summary = ppc.export(root)
    return {"exported": len(exported), "regen": len(batch), "exported_ids": exported,
            "delivery_dir": delivery, "requests_path": "requests.json", "batch": batch,
            "ppc": ppc_summary}


def _sheets(root, out_dir, pieces):
    by_key = {}
    for p in pieces:
        axis = "|".join(str(v) for v in p["axes"].values())
        by_key.setdefault((p["concept"], axis), []).append(p)
    review = os.path.join(root, "review")
    os.makedirs(review, exist_ok=True)
    for (concept, axis), group in by_key.items():
        paths = [os.path.join(out_dir, p["path"]) for p in group
                 if os.path.isfile(os.path.join(out_dir, p["path"]))]
        if paths:
            suffix = f"_{_slug(axis)}" if axis else ""
            P.contact_sheet(paths, os.path.join(review, f"sheet_{_slug(concept)}{suffix}.png"), cols=4)


def _slug(text):
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in str(text)).strip("-")[:80]