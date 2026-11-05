"""Magnific via MCP: o transporte é o agente, não o Python.

O Python prepara os jobs (imagem e vídeo) e coleta o que o agente baixou; a chamada à
ferramenta MCP acontece no agente, que é quem tem a conexão (por instalação). O aviso
de custo roda antes, com o crédito/unidade que o agente confirmou no plano.
"""

import glob
import json
import os
import shutil

from .base import IMG_EXT, VID_EXT, NeedsAgent, Provider, sha256


class MagnificMCP(Provider):
    name = "magnific-mcp"

    def __init__(self, drop_dir="~/Downloads", credits_per_image=0.0, credits_per_video=0.0):
        self.drop_dir = os.path.expanduser(drop_dir)
        self.credits_per_image = credits_per_image
        self.credits_per_video = credits_per_video

    def note(self):
        return ("o agente chama a ferramenta MCP do Magnific (imagem ou vídeo) e solta os "
                f"arquivos em {self.drop_dir} com o prefixo do job")

    def prepare(self, jobs, campaign_root):
        path = os.path.join(campaign_root, "assets", "jobs.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"provider": self.name, "drop_dir": self.drop_dir, "jobs": jobs},
                      f, indent=2, ensure_ascii=False)
        return path

    def generate(self, job):
        hits = sorted(p for p in glob.glob(os.path.join(self.drop_dir, f"{job['id']}*"))
                      if p.lower().endswith(IMG_EXT + VID_EXT))
        if not hits:
            raise NeedsAgent(job.get("_jobs_path", "assets/jobs.json"), [job])
        out = []
        for src in hits[:job.get("n", 1)]:
            dest = os.path.join(job["out_dir"], os.path.basename(src))
            os.makedirs(job["out_dir"], exist_ok=True)
            shutil.copy(src, dest)
            out.append(dest)
        return out