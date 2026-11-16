"""Manual provider: assets come in through a watched folder. Zero cost, no network.

This is today's CDI path (Magnific files land in ~/Downloads) and the universal fallback
for any platform without an API.
"""

import glob
import os
import shutil

from .base import IMG_EXT, VID_EXT, Provider, sha256


class Manual(Provider):
    name = "manual"
    credits_per_image = 0.0

    def __init__(self, drop_dir):
        self.drop_dir = os.path.expanduser(drop_dir)

    def note(self):
        return f"no cost; files expected in {self.drop_dir}"

    def generate(self, job):
        pattern = os.path.join(self.drop_dir, f"{job['id']}*")
        hits = sorted(p for p in glob.glob(pattern)
                      if p.lower().endswith(IMG_EXT + VID_EXT))
        if not hits:
            raise FileNotFoundError(
                f"No file for job '{job['id']}' in {self.drop_dir}. "
                f"Generate on the platform and drop it there with the job prefix.")
        out = []
        for src in hits[:job.get("n", 1)]:
            dest = os.path.join(job["out_dir"], os.path.basename(src))
            os.makedirs(job["out_dir"], exist_ok=True)
            shutil.copy(src, dest)
            out.append(dest)
        return out