"""Provider manual: os assets entram por uma pasta observada. Custo zero, sem rede.

É o caminho de hoje do CDI (arquivos do Magnific caem em ~/Downloads) e o fallback
universal para qualquer plataforma que não tenha API.
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
        return f"sem custo; arquivos esperados em {self.drop_dir}"

    def generate(self, job):
        pattern = os.path.join(self.drop_dir, f"{job['id']}*")
        hits = sorted(p for p in glob.glob(pattern)
                      if p.lower().endswith(IMG_EXT + VID_EXT))
        if not hits:
            raise FileNotFoundError(
                f"Nenhum arquivo para o job '{job['id']}' em {self.drop_dir}. "
                f"Gere na plataforma e solte lá com o prefixo do job.")
        out = []
        for src in hits[:job.get("n", 1)]:
            dest = os.path.join(job["out_dir"], os.path.basename(src))
            os.makedirs(job["out_dir"], exist_ok=True)
            shutil.copy(src, dest)
            out.append(dest)
        return out