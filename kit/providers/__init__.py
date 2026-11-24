"""Provider factory + the assets flow with a cost notice.

Flow: estimate (informational ≈ credits notice) -> generate -> manifest + subject.json.
For MCP, generate raises NeedsAgent and the CLI hands the jobs to the agent.
Video is a provider job (kind=video), not local render.
"""

import json
import os

from PIL import Image

from .. import primitives as P
from .base import IMG_EXT, NeedsAgent, Provider, notice, num, record_manifest, sha256
from .http_api import HttpAPI
from .manual import Manual
from .mcp import MagnificMCP


def get_provider(cfg):
    cfg = cfg or {}
    name = cfg.get("name", "manual")
    if name in ("magnific-mcp", "mcp"):
        return MagnificMCP(cfg.get("drop_dir", "~/Downloads"),
                           num(cfg.get("credits_per_image")), num(cfg.get("credits_per_video")))
    if name == "manual":
        return Manual(cfg.get("drop_dir", "~/Downloads"))
    return HttpAPI(cfg)


def run_assets(campaign):
    root = campaign["_root"]
    jobs = campaign.get("asset_jobs") or []
    if not jobs:
        return {"count": 0, "credits": 0, "generated": [], "note": "campaign has no asset_jobs"}
    provider = get_provider(campaign.get("provider"))
    estimate = provider.estimate(jobs)
    estimate["notice"] = notice(estimate)

    out_dir = os.path.join(root, "assets")
    for j in jobs:
        j["out_dir"] = out_dir
    if isinstance(provider, MagnificMCP):
        jobs_path = provider.prepare(jobs, root)
        for j in jobs:
            j["_jobs_path"] = jobs_path

    generated, entries = [], []
    for j in jobs:
        paths = provider.generate(j)
        kind = j.get("kind", "image")
        rate = num(provider.credits_per_video if kind == "video" else provider.credits_per_image)
        for p in paths:
            generated.append(p)
            entries.append({"id": j["id"], "provider": provider.name, "prompt": j["prompt"],
                            "kind": kind, "aspect": j.get("aspect"), "credits": rate,
                            "path": os.path.relpath(p, root), "sha": sha256(p)})

    subjects = {}
    spath = os.path.join(out_dir, "subject.json")
    if os.path.isfile(spath):
        with open(spath, encoding="utf-8") as f:
            subjects = json.load(f)
    for p in generated:
        if p.lower().endswith(IMG_EXT):
            subjects[os.path.basename(p)] = round(P.subject_center(Image.open(p).convert("RGB")), 4)
    with open(spath, "w", encoding="utf-8") as f:
        json.dump(subjects, f, indent=2)

    record_manifest(root, entries)
    from .. import assets as approval
    return {**estimate, "generated": generated,
            "approval": approval.counts(approval.load(root))}