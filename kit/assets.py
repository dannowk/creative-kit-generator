"""Asset approval — the stage between generating the images and rendering the pieces.

The user looks at what the provider (Magnific/MCP, manual drop) actually produced and approves
or asks for changes **before** any logo, overlay or copy is composited on top. Regenerating a
raw image is cheap and fixes the cause; re-rendering a composited piece only hides it.

`assets/manifest.json` (written by the providers) is the source of truth for which files exist
and what they cost. This module keeps the decisions beside it in `assets/state.json`, keyed by
file + sha: a regenerated file (new sha) goes back to `pending` on its own, an untouched one
keeps its approval. Marked files queue in `assets/requests.json` — the same derived-view contract
as the piece review, so one `wait` covers both stages.
"""

import json
import os
import threading
from datetime import datetime, timezone

DIR = "assets"
STATUSES = ("pending", "approved", "rejected", "redo")

# RLock: decide() holds it while calling load() -> sync_state(), which takes it again.
_LOCK = threading.RLock()


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state_path(root):
    return os.path.join(root, DIR, "state.json")


def _requests_path(root):
    return os.path.join(root, DIR, "requests.json")


def _read_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def manifest(root):
    """Latest manifest entry per file (the manifest is append-only, keyed by sha)."""
    out = {}
    for e in _read_json(os.path.join(root, DIR, "manifest.json")) or []:
        path = e.get("path")
        if path:
            out[path] = e
    return out


def sync_state(root):
    """Rebuild `assets/state.json` from the manifest, preserving decisions of unchanged files.

    Called after every generation and on every poll of the approval page, so a file the agent
    just regenerated shows up as pending (badged NEW in the UI) without anyone pressing anything.
    """
    entries = manifest(root)
    if not entries:
        return []
    prior = {a["path"]: a for a in (_read_json(_state_path(root)) or {}).get("assets", [])}
    assets, changed = [], len(prior) != len(entries)
    for path, e in sorted(entries.items()):
        if not os.path.isfile(os.path.join(root, path)):
            changed = True
            continue
        old = prior.get(path)
        if old and old.get("sha") == e.get("sha"):
            assets.append(old)
            continue
        changed = True
        assets.append({"path": path, "file": os.path.basename(path), "job": e.get("id"),
                       "kind": e.get("kind", "image"), "prompt": e.get("prompt", ""),
                       "aspect": e.get("aspect"), "credits": e.get("credits", 0),
                       "provider": e.get("provider", ""), "sha": e.get("sha"),
                       "status": "pending", "note": "", "updated_at": _now()})
    if changed or not os.path.isfile(_state_path(root)):
        with _LOCK:
            _write_json(_state_path(root), {"assets": assets})
    return assets


def load(root):
    """The approval state, synced with the manifest first (never stale)."""
    assets = sync_state(root)
    return {"assets": assets}


def counts(state):
    out = {s: 0 for s in STATUSES}
    for a in state.get("assets", []):
        out[a.get("status", "pending")] = out.get(a.get("status", "pending"), 0) + 1
    return out


def pending(state):
    """What the agent must regenerate NOW: every asset still rejected (new image) or redo (note)."""
    out = []
    for a in state.get("assets", []):
        st = a.get("status")
        if st not in ("rejected", "redo"):
            continue
        out.append({"stage": "assets", "id": a["path"], "file": a.get("file"),
                    "job": a.get("job"), "kind": a.get("kind", "image"),
                    "prompt": a.get("prompt", ""), "credits": a.get("credits", 0),
                    "reason": "redo" if st == "redo" else "rejected",
                    "note": a.get("note", ""), "marked_at": a.get("updated_at", "")})
    return out


def sync_requests(root, state=None):
    """Keep `assets/requests.json` a derived view of the marked assets (the agent's work queue)."""
    state = state or load(root)
    batch = pending(state)
    path = _requests_path(root)
    if _read_json(path) != batch:
        with _LOCK:
            _write_json(path, batch)
    return batch


def decide(root, path, status, note="", who="user"):
    """Mark one asset. Queues it immediately — the agent picks it up with `wait`."""
    if status not in STATUSES:
        return False
    note = (note or "").strip()
    if status == "redo" and not note:
        return False
    with _LOCK:
        state = load(root)
        hit = False
        for a in state["assets"]:
            if a["path"] != path:
                continue
            a["status"] = status
            a["note"] = note if status == "redo" else ""
            a["decided_at"] = _now()
            a["decided_by"] = who
            if status in ("rejected", "redo"):
                a["queued"] = True
            else:
                a.pop("queued", None)
            hit = True
        if not hit:
            return False
        _write_json(_state_path(root), state)
    sync_requests(root, state)
    return True


def unapproved(root):
    """Assets waiting for the user (empty when the campaign has no generated assets)."""
    return [a for a in load(root).get("assets", []) if a.get("status") != "approved"]


def all_approved(root):
    """(every generated asset approved, total) — False with total 0 when nothing was generated."""
    found = load(root).get("assets", [])
    return (bool(found) and not any(a.get("status") != "approved" for a in found), len(found))


def jobs_for(batch):
    """The provider job ids behind a batch — what `assets --jobs` regenerates."""
    return sorted({b["job"] for b in batch if b.get("job")})


def wait_batch(root, timeout=0, interval=2.0):
    """Block until an asset is marked, then return the batch (the agent's hook)."""
    import time
    deadline = time.time() + timeout if timeout else None
    while True:
        batch = sync_requests(root)
        if batch:
            return batch
        if deadline is not None and time.time() >= deadline:
            return []
        time.sleep(interval)


def payload(root):
    """What the approval page consumes."""
    state = load(root)
    batch = sync_requests(root, state)
    return {"root": root, "assets": state["assets"], "counts": counts(state),
            "batch": batch, "jobs": jobs_for(batch),
            "requests_path": os.path.join(DIR, "requests.json")}
