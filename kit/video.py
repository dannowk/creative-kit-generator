"""Edição de vídeo local com o ffmpeg embutido do imageio-ffmpeg (sem ffmpeg de sistema).

Cobre o pacote completo: trim por duração, reframe por aspect ratio que mira o anchor
da foto do spec (no wide, a coluna da foto — o texto fica na outra), overlay de marca
reaproveitando os specs declarativos (render transparent), concat de clipes e legenda
queimada — automática (faster-whisper, lazy) ou manual. Legendas viram PNG do PIL
sobrepostos por janela de tempo, então não dependem de libass/fontconfig do ffmpeg.
O prior de rosto sai da conta do crop (onde o sujeito caiu), mesmo contrato do
render._record_face das imagens — não do centro fixo do frame.
"""

import json
import os
import re
import subprocess
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw

from . import compliance, formats, primitives as P, render

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

DEFAULT_VIDEO_FORMATS = ["meta_story", "tiktok_story", "meta_feed_square",
                         "meta_feed_portrait", "meta_landscape", "linkedin_feed",
                         "youtube_thumbnail"]

_ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]


def _run(args):
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou: {r.stderr.strip()[:500]}")
    return r


def probe(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True)
    d = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", r.stderr)
    dur = (int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))) if d else 0.0
    m = re.search(r"Stream #\d+:\d+.*Video:.*?(\d{2,5})x(\d{2,5})", r.stderr)
    w, h = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return {"duration": dur, "w": w, "h": h}


def _even(n):
    return max(2, int(n) // 2 * 2)


def reframe_plan(sw, sh, w, h, fx, fy=0.4, tx=0.5, ty=0.4, zmax=2.2):
    """Janela de crop que leva o sujeito a (tx, ty) do frame de destino.
    Se o alvo não cabe na janela sem zoom, aproxima até zmax; devolve o crop e
    onde o sujeito caiu de fato (sx, sy) — o prior de rosto sai dessa conta."""
    tar = w / h
    if sw / sh > tar:
        ch, cw = sh, sh * tar
    else:
        cw, ch = sw, sw / tar
    z = 1.0
    while True:
        cw_z, ch_z = _even(cw / z), _even(ch / z)
        cx0, cy0 = fx * sw - tx * cw_z, fy * sh - ty * ch_z
        cx = min(max(0, round(cx0)), sw - cw_z)
        cy = min(max(0, round(cy0)), sh - ch_z)
        if (abs(cx0 - cx) < 1 and abs(cy0 - cy) < 1) or z >= zmax:
            break
        z = min(zmax, z + 0.1)
    sx, sy = (fx * sw - cx) / cw_z, (fy * sh - cy) / ch_z
    return cw_z, ch_z, cx, cy, sx, sy


def reframe_filter(sw, sh, w, h, fx=0.5, fy=0.4, tx=0.5, ty=0.4):
    cw, ch, cx, cy, _, _ = reframe_plan(sw, sh, w, h, fx, fy, tx, ty)
    return f"crop={cw}:{ch}:{cx}:{cy},scale={_even(w)}:{_even(h)}"


def _photo_anchor(spec, geo):
    """Coluna horizontal onde o spec coloca o rosto da foto (fração da largura) + o
    retângulo da foto. Mesmo contrato do render._record_face: no wide a foto vive
    numa coluna e o texto na outra — o vídeo mira o sujeito nessa coluna, não no centro."""
    layers, vars_ = render._layers(spec, geo)
    v = dict(geo)
    v.update({"ratio": geo["h"] / geo["w"], "ar": geo["w"] / geo["h"],
              "pi": 3.141592653589793, "true": 1, "false": 0, "logo_w": 0, "logo_h": 0})
    for k, expr in vars_.items():
        v[k] = render.evaluate(expr, v)
    photo = None
    for layer in layers:
        if layer.get("op") == "photo":
            photo = layer
    if photo is None:
        return None
    at = [render.evaluate(a, v) for a in photo.get("at", [0, 0])]
    pw, ph = [render.evaluate(s, v) for s in photo.get("size", [geo["w"], geo["h"]])]
    ax = photo.get("fx_at", photo.get("subject_at", 0.5))
    return {"tx": (at[0] + ax * pw) / geo["w"], "pw": pw, "ph": ph}


def frame_at(src, t, dest):
    _run(["-ss", str(t), "-i", src, "-frames:v", "1", dest])
    return dest


def subject_fx(src):
    info = probe(src)
    with tempfile.TemporaryDirectory() as td:
        f = frame_at(src, info["duration"] / 2, os.path.join(td, "f.png"))
        return P.subject_center(Image.open(f).convert("RGB"))


def overlay_png(spec, brand, geo, copy, extra, logo):
    return render.render(spec, brand, geo, logo=logo, copy=copy, extra=extra,
                         transparent=True)


def concat(paths, dst):
    """Concatena clipes de MESMA geometria/codec (copy, sem re-encode)."""
    with tempfile.TemporaryDirectory() as td:
        lst = os.path.join(td, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in paths:
                f.write(f"file '{os.path.abspath(p)}'\n")
        _run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dst])
    return dst


def transcribe(src, model_size="tiny", language=None):
    """Legendas automáticas. Lazy: só importa/baixa o modelo quando pedido."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError("faster-whisper não instalado; use legendas manuais ou "
                           "pip install faster-whisper") from e
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(src, language=language, vad_filter=True)
    return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments if s.text.strip()]


def caption_png(text, geo, brand):
    """Faixa de legenda legível na base segura, sobre transparência."""
    w, h = geo["w"], geo["h"]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = round(geo["scale"] * 0.042)
    font = P.ft(brand.fonts.spec("text"), size)
    max_w = w - 2 * geo["m"]
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    lines = lines[-2:]
    lh = round(size * 1.3)
    box_h = lh * len(lines) + round(size * 0.6)
    y1 = geo["bottom"]
    y0 = y1 - box_h
    d.rectangle([geo["m"], y0, w - geo["m"], y1], fill=(10, 12, 14, 170))
    y = y0 + round(size * 0.3)
    for line in lines:
        tw = d.textlength(line, font=font)
        d.text(((w - tw) / 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += lh
    return img


def overlay_geo(geo, has_captions):
    """Com legenda, eleva o `bottom`: como os specs ancoram copy/CTA na base, tudo sobe
    acima da faixa de legenda, que ocupa o bottom verdadeiro. Sem legenda, geo intacto."""
    if not has_captions:
        return geo
    return {**geo, "bottom": geo["bottom"] - round(geo["scale"] * 0.16)}


def build_piece(src, dst, geo, fx, duration, overlay, segments, brand, fy=0.4,
                target=None, face_size=None):
    """Pass 1: trim + reframe + overlay de marca. Pass 2 (se houver): legendas.
    `target` = coluna horizontal do sujeito (fração da largura), usada no wide para
    pôr o sujeito na coluna da foto e o texto na outra. Devolve (dst, face_box)."""
    info = probe(src)
    w, h = geo["w"], geo["h"]
    tx = target if target is not None else 0.5
    cw, ch, cx, cy, sx, sy = reframe_plan(info["w"], info["h"], w, h, fx, fy, tx, fy)
    vf = f"crop={cw}:{ch}:{cx}:{cy},scale={_even(w)}:{_even(h)}"
    with tempfile.TemporaryDirectory() as td:
        ov = os.path.join(td, "ov.png")
        overlay.save(ov)
        args = []
        if duration:
            args += ["-ss", "0", "-t", str(duration)]
        args += ["-i", src, "-i", ov,
                 "-filter_complex", f"[0:v]{vf}[b];[b][1:v]overlay=0:0[v]",
                 "-map", "[v]", "-map", "0:a?"] + _ENC + [dst]
        _run(args)
        if segments:
            _burn_captions(dst, dst, segments, geo, brand, td)
    pw, ph = face_size or (w, h)
    box = (sx * w - 0.11 * pw, sy * h - 0.12 * ph, sx * w + 0.11 * pw, sy * h + 0.14 * ph)
    return dst, box


def _burn_captions(src, dst, segments, geo, brand, td):
    inputs, chains, prev = [], [], "[0:v]"
    for i, seg in enumerate(segments, 1):
        png = os.path.join(td, f"cap{i}.png")
        caption_png(seg["text"], geo, brand).save(png)
        inputs += ["-i", png]
        nxt = f"[v{i}]"
        chains.append(f"{prev}[{i}:v]overlay=0:0:enable='between(t,{seg['start']},{seg['end']})'{nxt}")
        prev = nxt
    tmp = dst + ".cap.mp4"
    _run(["-i", src] + inputs +
         ["-filter_complex", ";".join(chains), "-map", prev, "-map", "0:a?"] + _ENC + [tmp])
    os.replace(tmp, dst)


def run(campaign):
    """Monta as peças de vídeo (conceitos × formatos × eixos) e funde no state.json."""
    from . import campaign as C
    cfg = campaign.get("video")
    if not cfg:
        return {"count": 0, "pieces": [], "note": "campanha sem bloco video"}
    brand = C.brand_for(campaign)
    root = campaign["_root"]
    out_dir = os.path.join(root, "out")
    names = [f for f in (cfg.get("formats") or DEFAULT_VIDEO_FORMATS) if f in formats.FORMATS]
    concepts = cfg.get("concepts") or campaign.get("concepts") or C.available_concepts()
    combos = C.expand_axes(brand, campaign)
    logo = Image.open(brand.logo_path).convert("RGBA") if brand.logo_path else None
    copy_map = campaign.get("copy") or {}
    durations = cfg.get("durations") or {}
    cap_mode = cfg.get("captions", "off")

    source = cfg.get("source")
    if cfg.get("concat"):
        master = os.path.join(root, "assets", "_concat.mp4")
        concat([p if os.path.isabs(p) else os.path.join(root, p) for p in cfg["concat"]], master)
        source = master

    pieces, blocked = [], []
    cap_cache = {}
    for combo in combos:
        rel = C.lookup(source, combo) if isinstance(source, dict) else source
        if not rel:
            continue
        src = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"fonte de vídeo não encontrada: {src}")
        fx = subject_fx(src)
        if cap_mode == "auto":
            if src not in cap_cache:
                cap_cache[src] = transcribe(src, language=cfg.get("language"))
            segments = cap_cache[src]
        elif isinstance(cap_mode, list):
            segments = cap_mode
        else:
            segments = []
        copy = C.lookup(copy_map, combo) or {}
        if isinstance(copy, str):
            copy = {"hook": copy}
        extra = {"program": copy.get("program", ""), "campus": copy.get("campus", campaign.get("campus", "")),
                 "cta": copy.get("cta", campaign.get("cta", "Learn more")), "brand_name": brand.name}
        for concept in concepts:
            spec = render.load_spec(C._spec_path(campaign, concept))
            voice = copy.get(concept)
            merged = {**copy, **voice} if isinstance(voice, dict) else copy
            for fmt in names:
                geo = formats.geometry(fmt, brand)
                geo_ov = overlay_geo(geo, bool(segments))
                dur = durations.get(fmt) or durations.get("default")
                ov = overlay_png(spec, brand, geo_ov, merged, extra, logo)
                name = C.piece_name(brand, campaign, combo, concept, fmt)
                rel_out = os.path.join(concept, f"{name}.mp4")
                dest = os.path.join(out_dir, rel_out)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                anchor = _photo_anchor(spec, geo)
                _, face_box = build_piece(src, dest, geo, fx, dur, ov, segments, brand,
                                          target=anchor["tx"] if anchor and geo["wide"] else None,
                                          face_size=(anchor["pw"], anchor["ph"]) if anchor else None)
                trace = {}
                render.render(spec, brand, geo_ov, logo=logo, copy=merged, extra=extra,
                              trace=trace, transparent=True)
                trace["face_box"] = face_box
                with tempfile.TemporaryDirectory() as td:
                    poster = frame_at(dest, (dur or probe(dest)["duration"]) / 2,
                                      os.path.join(td, "p.png"))
                    comp = Image.open(poster).convert("RGB").resize((geo["w"], geo["h"]))
                    comp = Image.alpha_composite(comp.convert("RGBA"), ov).convert("RGB")
                    findings = compliance.run(comp, trace, brand)
                    thumb_dir = os.path.join(root, "review", "thumbs", concept)
                    os.makedirs(thumb_dir, exist_ok=True)
                    comp.resize((max(1, round(comp.width * 360 / comp.height)), 360),
                                P.LANCZOS).save(os.path.join(thumb_dir, f"{name}.video.png"))
                entry = {"id": f"{name}_video", "path": rel_out, "concept": concept, "format": fmt,
                         "axes": combo, "kind": "video", "duration": dur or probe(dest)["duration"],
                         "findings": findings,
                         "status": "blocked" if compliance.blocked(findings) else "pending"}
                if entry["status"] == "blocked":
                    blocked.append(entry)
                pieces.append(entry)

    state_path = os.path.join(root, "state.json")
    state = {"campaign": campaign.get("slug"), "brand": brand.id, "root": root,
             "formats": names, "concepts": concepts, "pieces": [], "blocked_count": 0,
             "font_warnings": {"missing": brand.fonts.missing, "substituted": brand.fonts.substituted}}
    if os.path.isfile(state_path):
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
    state["pieces"] = [p for p in state.get("pieces", []) if p.get("kind") != "video"] + pieces
    state["blocked_count"] = sum(1 for p in state["pieces"] if p["status"] == "blocked")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    return {"count": len(pieces), "blocked": len(blocked), "pieces": pieces,
            "concepts": concepts, "formats": names}