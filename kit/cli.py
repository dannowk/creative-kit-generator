"""CLI do campaign-kit: onboard -> intake -> assets -> render -> review.

  python3 -m kit.cli onboard ~/inbox/acme
  python3 -m kit.cli intake ~/inbox/acme acme
  python3 -m kit.cli assets campaigns/acme-launch
  python3 -m kit.cli render campaigns/acme-launch
  python3 -m kit.cli review campaigns/acme-launch
"""

import argparse
import json
import os
import sys

from . import briefing, campaign, intake, onboard, providers, render, ui, video

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="campaign-kit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake", help="deriva uma marca da pasta jogada")
    p.add_argument("inbox")
    p.add_argument("brand_id")

    p = sub.add_parser("brief", help="briefing canônico: valida gaps/erros e (--apply) escreve brand.yaml + campaign.json")
    p.add_argument("file", nargs="?", help="briefing preenchido (.yaml/.json)")
    p.add_argument("--apply", action="store_true", help="aplica o briefing (escreve marca + campanha)")
    p.add_argument("--template", action="store_true", help="imprime o template markdown gerado do schema")
    p.add_argument("--normalize", metavar="ARQUIVO", help="prepara normalizar um briefing livre (prosa/PDF/docx) para o schema")
    p.add_argument("--out", help="alvo do --normalize (default: <pasta-da-fonte>/briefing.yaml)")

    p = sub.add_parser("assets", help="aviso de custo + geração de assets de IA (imagem e vídeo)")
    p.add_argument("campaign")

    p = sub.add_parser("render", help="renderiza a matriz de peças")
    p.add_argument("campaign")
    p.add_argument("--concepts", nargs="*")
    p.add_argument("--formats", nargs="*")
    p.add_argument("--limit", type=int)
    p.add_argument("--dry", action="store_true")

    p = sub.add_parser("video", help="edita vídeo: trim, reframe por sujeito, overlay de marca, concat, legenda")
    p.add_argument("campaign")

    p = sub.add_parser("review", help="UI local de aprovação")
    p.add_argument("campaign")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="não abre o navegador (headless)")

    p = sub.add_parser("plan", help="direção de arte a partir do briefing + referências")
    p.add_argument("campaign")

    p = sub.add_parser("onboard", help="prepara a pasta da campanha (briefing, refs, fontes, logo, fotos, vídeos)")
    p.add_argument("inbox")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-ui", action="store_true", help="só scaffold + checklist, sem servidor")
    p.add_argument("--no-open", action="store_true", help="não abre o navegador (headless)")

    args = ap.parse_args(argv)

    if args.cmd == "brief":
        if args.normalize:
            src = os.path.expanduser(args.normalize)
            out = args.out or os.path.join(os.path.dirname(os.path.abspath(src)), "briefing.yaml")
            try:
                summary = briefing.normalize_prepare(src, out, ROOT)
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 1
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            extract = " (extraia a fonte com visão/docx)" if summary["needs_extraction"] else ""
            print(f"\nNORMALIZE MEDIADO PELO AGENTE: leia {summary['contract']}, preencha "
                  f"{summary['skeleton']}{extract}; o que não souber fica vazio (vira gap). "
                  f"Depois: brief {summary['skeleton']} --apply")
            return 0
        if args.template:
            print(briefing.template_md())
            return 0
        if not args.file:
            ap.error("brief precisa de um arquivo (ou --template)")
        path = os.path.expanduser(args.file)
        struct = briefing.load(path)
        base = os.path.dirname(os.path.abspath(path))
        if args.apply:
            try:
                summary = briefing.apply(struct, base, ROOT)
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 1
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            print(f"\npróximos passos: plan campaigns/{summary['campaign']} → render → review"
                  "  (review abre o navegador sozinho)")
            if summary["palette_proposed"]:
                print("paleta derivada do logo é PROPOSTA — confirme com o designer antes de veicular.")
            return 0
        v = briefing.validate(struct, base)
        print(f"{'APLICÁVEL' if v['ok'] else 'NÃO APLICÁVEL'} · {len(v['errors'])} erro(s) · "
              f"{sum(g['required'] for g in v['gaps'])} gap(s) obrigatório(s) · "
              f"{sum(not g['required'] for g in v['gaps'])} pergunta(s) opcional(is)")
        for e in v["errors"]:
            print(f"  ERRO [{e['field']}] {e['message']}", file=sys.stderr)
        for g in v["gaps"]:
            tag = "FALTA" if g["required"] else "opcional"
            print(f"  [{tag}] {g['field']}: {g['question']}")
            print(f"          {g['why']}")
        return 0 if v["ok"] else 1

    if args.cmd == "onboard":
        inbox = os.path.expanduser(args.inbox)
        brief = onboard.scaffold(inbox)
        st = onboard.status(inbox)
        print(f"pasta em {st['inbox']}")
        for s in st["slots"].values():
            mark = "ok" if s["ok"] else ("FALTA" if s["required"] else "opcional")
            print(f"  [{mark}] {s['label']}: {len(s['files'])} arquivo(s) — {s['hint']}")
        print(f"  briefing: {brief} · {len(st['briefing']['missing'])} seção(ões) obrigatória(s) em branco")
        if args.no_ui:
            return 0
        server, url = ui.serve_onboard(inbox, os.path.join(ROOT, "brands"), args.port,
                                       open_browser=not args.no_open)
        print("  Ctrl+C para fechar o servidor")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0

    if args.cmd == "intake":
        summary, gaps = intake.run(os.path.expanduser(args.inbox), args.brand_id,
                                   os.path.join(ROOT, "brands"))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"\n{len(gaps)} perguntas para uma única rodada:", file=sys.stderr)
        for g in gaps:
            print(f"  [{g['field']}] {g['question']}", file=sys.stderr)
        return 0

    camp = campaign.load_campaign(os.path.join(ROOT, args.campaign)
                                  if not os.path.isabs(args.campaign) else args.campaign)

    if args.cmd == "assets":
        jobs = camp.get("asset_jobs") or []
        if jobs:
            print(providers.notice(providers.get_provider(camp.get("provider")).estimate(jobs)))
        try:
            result = providers.run_assets(camp)
        except providers.NeedsAgent as e:
            print(f"PROVIDER MEDIADO PELO AGENTE: cumpra os jobs em {e.jobs_path}")
            with open(e.jobs_path, encoding="utf-8") as f:
                print(json.dumps(json.load(f)["jobs"], indent=2, ensure_ascii=False))
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "render":
        state = campaign.run(camp, only_concepts=args.concepts, only_formats=args.formats,
                             limit=args.limit, dry=args.dry)
        print(f"{len(state['pieces'])} peças · {state['blocked_count']} bloqueadas · "
              f"conceitos: {', '.join(state['concepts'])}")
        for p in state["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    print(f"  BLOQUEADA {p['id']}: {f['message']}")
        if state["font_warnings"]["substituted"]:
            print("  fontes substitutas:", state["font_warnings"]["substituted"])
        if not args.dry:
            print(f"  próximo passo: python3 -m kit.cli review {args.campaign}  (abre o navegador)")
        return 0

    if args.cmd == "video":
        result = video.run(camp)
        if not result["count"]:
            print(result.get("note", "sem peças de vídeo"))
            return 0
        print(f"{result['count']} peças de vídeo · {result['blocked']} bloqueadas · "
              f"conceitos: {', '.join(result['concepts'])}")
        for p in result["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    print(f"  BLOQUEADA {p['id']}: {f['message']}")
        print(f"  próximo passo: python3 -m kit.cli review {args.campaign}  (abre o navegador)")
        return 0

    if args.cmd == "plan":
        brand = campaign.brand_for(camp)
        intake_path = os.path.join(brand.root, "intake.json")
        info = {}
        if os.path.isfile(intake_path):
            with open(intake_path, encoding="utf-8") as f:
                info = json.load(f)
        print("DIREÇÃO DE ARTE — leia antes de escolher layout:")
        print("  briefing:", ", ".join(info.get("briefs") or []) or "(nenhum na pasta)")
        answers_path = os.path.join(brand.root, "answers.json")
        if os.path.isfile(answers_path):
            with open(answers_path, encoding="utf-8") as f:
                answers = json.load(f)
            print("  respostas do onboarding (aplique no brand.yaml nesta rodada):")
            for k, v in answers.items():
                if v:
                    print(f"   [{k}] {v}")
        print("  referências (OLHE com visão, não só os pixels):")
        for r in info.get("refs") or []:
            print("   -", r)
        print("  preencha reference_analysis:", ", ".join((info.get("reference_analysis") or {}).keys()))
        concepts_req = info.get("concepts_requested") or []
        if concepts_req:
            print("  conceitos pedidos no briefing:", ", ".join(concepts_req))
            print("   → autorei um templates/<conceito>.yaml por conceito, liste-os em campaign.json.concepts")
            print("     e dê um copy.hook por conceito (sem hook, o conceito é pulado no render).")
        else:
            print("  conceitos: não especificados no briefing — pergunte ou proponha direções a partir das refs.")
        print("\n  A biblioteca global (templates/) é PONTO DE PARTIDA, não destino.")
        print("  Autore/ajuste campaigns/<slug>/templates/<conceito>.yaml a partir do briefing")
        print("  e das refs; o spec local vence o global. Ops disponíveis:")
        print("   ", ", ".join(render.OPS))
        print("  Tratamento de tipo por layer: underline, accent_upper, accent_scale.")
        print("\n  Limite honesto: estes ops cobrem direções fotográficas/tipográficas.")
        print("  Look radicalmente diferente (ilustração flat, 3D, colagem) pede imagem")
        print("  gerada pelo provider ou ops novos — não sai destes specs por mágica.")
        return 0

    if args.cmd == "review":
        server, url = ui.serve(camp["_root"], args.port, open_browser=not args.no_open)
        print("  Ctrl+C para fechar o servidor")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())