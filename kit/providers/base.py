"""Contrato de provider de assets de IA (imagem e vídeo).

O contrato é a pasta + manifest, não a API: o Magnific entra mediado pelo agente (MCP),
outros entram por HTTP direto. Trocar de plataforma é trocar adapter, não o pipeline.

`estimate` é obrigatório e informativo: mostra ≈ quanto será gasto antes de gerar.
Não bloqueia — o usuário já espera a cobrança; o que importa é o valor aproximado.
"""

import hashlib
import json
import os
import time

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
VID_EXT = (".mp4", ".mov", ".webm", ".m4v")


class NeedsAgent(Exception):
    """O transporte deste provider é o agente (MCP). O CLI para e entrega os jobs a ele."""

    def __init__(self, jobs_path, jobs):
        super().__init__(f"Provider mediado pelo agente: cumpra os jobs em {jobs_path}")
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
    """Aviso curto de gasto aproximado — informativo, nunca um bloqueio."""
    bits = []
    if estimate.get("images"):
        bits.append(f"{estimate['images']} imagem(ns)")
    if estimate.get("videos"):
        bits.append(f"{estimate['videos']} vídeo(s)")
    what = " + ".join(bits) or "nada"
    return f"≈ {estimate['credits']} créditos ({what}) · estimativa {estimate['provider']}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def record_manifest(campaign_root, entries):
    """Proveniência e gasto por asset — o que o pipeline antigo não tinha."""
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