"""Rule changes go through the user: propose -> alarm -> agree or keep the original.

The agent never edits `brand.yaml`, `campaign.json` or the kit's own code to make a render pass.
It files a **proposal** (what the rule says now, what it should say, why, how many pieces it
touches) in `<campaign>/rules/proposals.json`; the review page pops a blocking alarm and sends a
desktop notification. Agreeing writes the patch to `<campaign>/rules/overrides.yaml`, which is
merged into the brand/campaign data on every load — the shared files stay pristine and the
decision survives re-renders. Keeping the original leaves the rule (and its findings) as is.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

import yaml

DIR = "rules"
SCOPES = ("brand", "campaign")
_LOCK = threading.RLock()
_SEG = re.compile(r"\s*\.?\s*([A-Za-z_][\w-]*)(?:\[([\w-]+)=([^\]]*)\])?")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir(root):
    return os.path.join(root, DIR)


def _proposals_path(root):
    return os.path.join(_dir(root), "proposals.json")


def _overrides_path(root):
    return os.path.join(_dir(root), "overrides.yaml")


def _read_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ── dotted paths: copy.hero.disclaimer, compliance[check=contrast_min].ratio ──

def _parse(target):
    """Tokenize the whole target; anything left over means the path is malformed."""
    segs, pos, t = [], 0, target or ""
    while pos < len(t):
        m = _SEG.match(t, pos)
        if not m:
            raise KeyError(target)
        segs.append((m.group(1), m.group(2), m.group(3) or ""))
        pos = m.end()
    if not segs:
        raise KeyError(target)
    return segs


def get_path(data, target):
    """The value a target points at (None when the path does not exist yet)."""
    node = data
    for name, mkey, mval in _parse(target):
        if not isinstance(node, dict) or name not in node:
            return None
        node = node[name]
        if mkey:
            if not isinstance(node, list):
                return None
            node = next((e for e in node if isinstance(e, dict) and str(e.get(mkey)) == mval), None)
            if node is None:
                return None
    return node


def set_path(data, target, value):
    """Write `value` at `target`, creating the dicts/list entries on the way."""
    segs = _parse(target)
    node = data
    for i, (name, mkey, mval) in enumerate(segs):
        last = i == len(segs) - 1
        if not isinstance(node, dict):
            raise KeyError(target)
        if node.get(name) is None:
            node[name] = [] if mkey else {}
        child = node[name]
        if not mkey:
            if last:
                node[name] = value
                return data
            node = child
            continue
        if not isinstance(child, list):
            raise KeyError(target)
        entry = next((e for e in child if isinstance(e, dict) and str(e.get(mkey)) == mval), None)
        if entry is None:
            entry = {mkey: mval}
            child.append(entry)
        if last:
            if isinstance(value, dict):
                entry.update(value)
            else:
                raise KeyError(target)
        node = entry
    return data


# ── proposals ──────────────────────────────────────────────────────────────

def load_proposals(root):
    return _read_json(_proposals_path(root)) or []


def _save_proposals(root, items):
    with _LOCK:
        _write(_proposals_path(root), json.dumps(items, indent=2, ensure_ascii=False) + "\n")


def pending(root):
    return [p for p in load_proposals(root) if p.get("status") == "pending"]


def add(root, target, value, reason, scope="brand", current=None, affected=None, total=None,
        who="agent", notify=True):
    """File a proposal. An identical pending one is returned as is (no duplicate alarms)."""
    if scope not in SCOPES:
        raise KeyError(scope)
    if current is None:
        current = get_path(_source(root, scope), target)
    items = load_proposals(root)
    for p in items:
        if (p.get("status") == "pending" and p.get("scope") == scope
                and p.get("target") == target and p.get("value") == value):
            return p
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    proposal = {"id": f"r-{stamp}-{len(items) + 1:02d}", "scope": scope, "target": target,
                "current": current, "value": value, "reason": (reason or "").strip(),
                "affected": affected, "total": total, "status": "pending",
                "proposed_by": who, "created_at": _now(), "decided_at": None, "decided_by": None}
    items.append(proposal)
    _save_proposals(root, items)
    if notify:
        notify_desktop(f"{scope}: {target}", proposal["reason"] or target)
    return proposal


def decide(root, pid, agree, who="user"):
    """Agree -> the patch goes to overrides.yaml. Keep -> the original rule stands."""
    with _LOCK:
        items = load_proposals(root)
        hit = next((p for p in items if p.get("id") == pid), None)
        if hit is None or hit.get("status") != "pending":
            return None
        hit["status"] = "agreed" if agree else "kept"
        hit["decided_at"] = _now()
        hit["decided_by"] = who
        _save_proposals(root, items)
        if agree:
            _add_patch(root, hit)
    return hit


def _add_patch(root, proposal):
    patches = [p for p in load_patches(root) if p.get("target") != proposal["target"]
               or p.get("scope") != proposal["scope"]]
    patches.append({"scope": proposal["scope"], "target": proposal["target"],
                    "value": proposal["value"], "proposal": proposal["id"],
                    "agreed_at": proposal["decided_at"]})
    with _LOCK:
        _write(_overrides_path(root), yaml.safe_dump(patches, sort_keys=False, allow_unicode=True))


def load_patches(root):
    if not os.path.isfile(_overrides_path(root)):
        return []
    try:
        with open(_overrides_path(root), encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    except (OSError, yaml.YAMLError):
        return []


def decided(root):
    return [p for p in load_proposals(root) if p.get("status") in ("agreed", "kept")]


def take_decisions(root):
    """Decisions the agent has not been told about yet — marked as reported on read."""
    items = load_proposals(root)
    out = [p for p in items if p.get("status") in ("agreed", "kept") and not p.get("reported")]
    if out:
        for p in out:
            p["reported"] = True
            p["reported_at"] = _now()
        _save_proposals(root, items)
    return out


def payload(root):
    """What the UI shows: the alarms to pop plus a short history."""
    items = load_proposals(root)
    return {"pending": [p for p in items if p.get("status") == "pending"],
            "decided": [p for p in items if p.get("status") in ("agreed", "kept")][-8:],
            "patches": len(load_patches(root))}


# ── merging the agreed overrides into the data ─────────────────────────────

def _source(root, scope):
    """The pristine data a scope points at — used only to record what the rule says now."""
    try:
        if scope == "campaign":
            return _read_json(os.path.join(root, "campaign.json")) or {}
        from . import campaign as _c
        from .brand import load_brand
        camp = _c.load_campaign(root)
        return load_brand(os.path.join(_c.ROOT, "brands", camp["brand"])).data
    except Exception:
        return {}


def apply(data, root, scope):
    """A copy of `data` with every agreed patch of `scope` merged in."""
    import copy as _copy
    out = _copy.deepcopy(data)
    for patch in load_patches(root):
        if patch.get("scope") != scope:
            continue
        try:
            set_path(out, patch.get("target"), patch.get("value"))
        except KeyError:
            continue
    return out


def brand_for(root, brand):
    """The brand with the agreed rule changes applied (a new Brand, the files untouched)."""
    from .brand import Brand
    data = apply(brand.data, root, "brand")
    if data == brand.data:
        return brand
    return Brand(data, brand.root)


def watch(root, timeout=0, interval=2.0):
    """Block until a pending proposal is decided; return the decisions of this round."""
    seen = {p["id"]: p.get("status") for p in load_proposals(root)}
    deadline = time.time() + timeout if timeout else None
    while True:
        batch = [p for p in load_proposals(root)
                 if p.get("status") in ("agreed", "kept") and seen.get(p["id"]) == "pending"]
        if batch:
            for p in batch:
                seen[p["id"]] = p["status"]
            return batch
        for p in load_proposals(root):
            seen.setdefault(p["id"], p.get("status"))
        if deadline is not None and time.time() > deadline:
            return []
        time.sleep(interval)


# ── the alarm outside the browser ──────────────────────────────────────────

def notify_desktop(title, message):
    """Best-effort OS notification; never raises (the browser modal is the real alarm)."""
    title = (title or "campaign-kit")[:120]
    message = (message or "")[:220]
    try:
        if sys.platform == "darwin":
            script = ('display notification "%s" with title "%s" sound name "Glass"'
                      % (message.replace('"', "'"), title.replace('"', "'")))
            subprocess.run(["osascript", "-e", script], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            return True
        if sys.platform.startswith("win"):
            ps = ("[reflection.assembly]::loadwithpartialname('System.Windows.Forms')|Out-Null;"
                  "$n=New-Object System.Windows.Forms.NotifyIcon;$n.Icon="
                  "[System.Drawing.SystemIcons]::Information;$n.Visible=$true;"
                  "$n.ShowBalloonTip(8000,'%s','%s','Info')"
                  % (title.replace("'", "''"), message.replace("'", "''")))
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            return True
    except Exception:
        return False
    return False
