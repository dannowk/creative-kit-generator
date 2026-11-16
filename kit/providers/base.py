"""Contract for AI asset providers (image and video).

The contract is the folder + manifest, not the API: Magnific comes in mediated by the
agent (MCP), others come in over direct HTTP. Switching platforms means switching
adapters, not the pipeline.

`estimate` is mandatory and informational: shows ≈ how much will be spent before
generating. It never blocks — the user already expects the charge; what matters is the
approximate amount.
"""

import hashlib
import json
import os
import time

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
VID_EXT = (".mp4", ".mov", ".webm", ".m4v")


class NeedsAgent(Exception):
    """This provider's transport is the agent (MCP). The CLI stops and hands it the jobs."""

    def __init__(self, jobs_path, jobs):
        super().__init__(f"Agent-mediated provider: fulfill the jobs in {jobs_path}")
        self.jobs_path = jobs_path
        self.jobs = jobs


class Provider:
    name = "base"
    credits_per_image = 0.0
    credits_per_video = 0.0

    def estimate(self, jobs):
        ni = sum(j.get("n", 1) for j in jobs if j.get("kind", "image") == "image")
        nv = sum(j.get("n", 1) for j in jobs if j.get("kind") == "video")
        credits = ni * self.credits_per_image + nv * self.credits_per_video
        return {"provider": self.name, "images": ni, "videos": nv, "count": ni + nv,
                "credits": round(credits, 2), "note": self.note()}

    def note(self):
        return ""

    def generate(self, job):
        raise NotImplementedError


def notice(estimate):
    """Short approximate-spend notice — informational, never a blocker."""
    bits = []
    if estimate.get("images"):
        bits.append(f"{estimate['images']} image(s)")
    if estimate.get("videos"):
        bits.append(f"{estimate['videos']} video(s)")
    what = " + ".join(bits) or "nothing"
    return f"≈ {estimate['credits']} credits ({what}) · estimate {estimate['provider']}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def record_manifest(campaign_root, entries):
    """Provenance and spend per asset — what the old pipeline lacked."""
    path = os.path.join(campaign_root, "assets", "manifest.json")
    existing = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    known = {e["sha"] for e in existing}
    for e in entries:
        e.setdefault("created", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if e["sha"] not in known:
            existing.append(e)
            known.add(e["sha"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return path