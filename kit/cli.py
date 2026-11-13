"""CLI do campaign-kit: onboard -> intake -> assets -> render -> review -> deliver.

  python3 -m kit.cli onboard ~/inbox/acme
  python3 -m kit.cli intake ~/inbox/acme acme
  python3 -m kit.cli assets campaigns/acme-launch
  python3 -m kit.cli render campaigns/acme-launch
  python3 -m kit.cli review campaigns/acme-launch
  python3 -m kit.cli deliver campaigns/acme-launch   # etapa 6: o Continuar da revisão
  python3 -m kit.cli ppc campaigns/acme-launch        # planilhas de bulk upload (Meta + Google)
"""

import argparse
import json
import os
import sys

from . import briefing, campaign, i18n, intake, onboard, providers, render, ui, video

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="campaign-kit")
    ap.add_argument("--lang", choices=["pt", "en"],
                    help="idioma das mensagens / message language (default: env KIT_LANG, else pt)")
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
    p.add_argument("--ids", nargs="*", help="re-renderiza só estas peças (etapa 6: recriar/refazer)")
    p.add_argument("--limit", type=int)
    p.add_argument("--dry", action="store_true")

    p = sub.add_parser("video", help="edita vídeo: trim, reframe por sujeito, overlay de marca, concat, legenda")
    p.add_argument("campaign")

    p = sub.add_parser("review", help="UI local de aprovação")
    p.add_argument("campaign")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="não abre o navegador (headless)")

    p = sub.add_parser("deliver", help="etapa 6: exporta aprovadas + enfileira recriação/refazer (o Continuar da revisão)")
    p.add_argument("campaign")

    p = sub.add_parser("ppc", help="planilhas de bulk upload p/ o time de PPC (Meta + Google), CSV + XLSX")
    p.add_argument("campaign")
    p.add_argument("--all", action="store_true", help="exporta todas as peças, não só as aprovadas")

    p = sub.add_parser("plan", help="direção de arte a partir do briefing + referências")
    p.add_argument("campaign")

    p = sub.add_parser("onboard", help="prepara a pasta da campanha (briefing, refs, fontes, logo, fotos, vídeos)")
    p.add_argument("inbox")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-ui", action="store_true", help="só scaffold + checklist, sem servidor")
    p.add_argument("--no-open", action="store_true", help="não abre o navegador (headless)")

    args = ap.parse_args(argv)
    lang = i18n.resolve_lang(args.lang)

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
            extract = i18n.t("cli.normalize.extract", lang) if summary["needs_extraction"] else ""
            print("\n" + i18n.t("cli.normalize.header", lang, contract=summary["contract"],
                                skeleton=summary["skeleton"], extract=extract))
            return 0
        if args.template:
            print(briefing.template_md())
            return 0
        if not args.file:
            ap.error(i18n.t("cli.brief.needfile", lang))
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
            print("\n" + i18n.t("cli.brief.next", lang, campaign=summary["campaign"]))
            if summary["palette_proposed"]:
                print(i18n.t("cli.palette.proposed", lang))
            return 0
        v = briefing.validate(struct, base, lang)
        status = i18n.t("cli.appliable" if v["ok"] else "cli.notappliable", lang)
        print(i18n.t("cli.briefsummary", lang, status=status, errors=len(v["errors"]),
                     reqgaps=sum(g["required"] for g in v["gaps"]),
                     optgaps=sum(not g["required"] for g in v["gaps"])))
        for e in v["errors"]:
            print("  " + i18n.t("cli.err", lang, field=e["field"], message=e["message"]), file=sys.stderr)
        for g in v["gaps"]:
            tag = i18n.t("cli.gap.req" if g["required"] else "cli.gap.opt", lang)
            print(f"  [{tag}] {g['field']}: {g['question']}")
            print(f"          {g['why']}")
        return 0 if v["ok"] else 1

    if args.cmd == "onboard":
        inbox = os.path.expanduser(args.inbox)
        brief = onboard.scaffold(inbox)
        st = onboard.status(inbox, lang)
        print(i18n.t("cli.folder", lang, inbox=st["inbox"]))
        for s in st["slots"].values():
            mark = i18n.t("cli.mark.ok" if s["ok"] else
                          ("cli.mark.missing" if s["required"] else "cli.mark.optional"), lang)
            print("  " + i18n.t("cli.slotline", lang, mark=mark, label=s["label"],
                                n=len(s["files"]), hint=s["hint"]))
        print("  " + i18n.t("cli.briefline", lang, path=brief,
                            n=len(st["briefing"]["missing"])))
        if args.no_ui:
            return 0
        server, url = ui.serve_onboard(inbox, os.path.join(ROOT, "brands"), args.port,
                                       open_browser=not args.no_open, lang=lang)
        print("  " + i18n.t("cli.ctrlc", lang))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0

    if args.cmd == "intake":
        summary, gaps = intake.run(os.path.expanduser(args.inbox), args.brand_id,
                                   os.path.join(ROOT, "brands"), lang)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print("\n" + i18n.t("cli.gaps.one", lang, n=len(gaps)), file=sys.stderr)
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
            print(i18n.t("cli.provider.agent", lang, path=e.jobs_path))
            with open(e.jobs_path, encoding="utf-8") as f:
                print(json.dumps(json.load(f)["jobs"], indent=2, ensure_ascii=False))
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "render":
        state = campaign.run(camp, only_concepts=args.concepts, only_formats=args.formats,
                             limit=args.limit, dry=args.dry, only_ids=args.ids)
        print(i18n.t("cli.render.summary", lang, n=len(state["pieces"]),
                     blocked=state["blocked_count"], concepts=", ".join(state["concepts"])))
        for p in state["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    msg = f.get("message_en") if lang == "en" and f.get("message_en") else f["message"]
                    print("  " + i18n.t("cli.render.blocked", lang, id=p["id"], message=msg))
        if state["font_warnings"]["substituted"]:
            print("  " + i18n.t("cli.render.fonts", lang, fonts=state["font_warnings"]["substituted"]))
        if not args.dry:
            print("  " + i18n.t("cli.render.next", lang, campaign=args.campaign))
        return 0

    if args.cmd == "video":
        result = video.run(camp)
        if not result["count"]:
            print(i18n.t("cli.video.none", lang))
            return 0
        print(i18n.t("cli.video.summary", lang, n=result["count"], blocked=result["blocked"],
                     concepts=", ".join(result["concepts"])))
        for p in result["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    msg = f.get("message_en") if lang == "en" and f.get("message_en") else f["message"]
                    print("  " + i18n.t("cli.render.blocked", lang, id=p["id"], message=msg))
        print("  " + i18n.t("cli.render.next", lang, campaign=args.campaign))
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
        brandbook = info.get("brandbook") or []
        if brandbook:
            print("  brandbook (LEIA — visão p/ PDF/imagem: cores, tipografia, uso do logo, voz):")
            for b in brandbook:
                print("   -", b)
            print("   → as regras do brandbook prevalecem sobre a paleta proposta; conflite com o briefing vira pergunta.")
        brief_docs = info.get("brief_docs") or []
        if brief_docs:
            print("  documentos de apoio do briefing (LEIA todos — texto/planilha; visão p/ PDF/imagem):")
            for b in brief_docs:
                print("   -", b)
            print("   → copy/conteúdo dos anúncios alimenta campaign.json.copy (hook/kicker/program/CTA por conceito/eixo);")
            print("     regras de layout, safe areas e segurança do logo viram geometry/safe_zones e compliance no brand.yaml")
            print("     e nos templates. Conflito com o briefing vira pergunta — não chute.")
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

    if args.cmd == "deliver":
        if not os.path.isfile(os.path.join(camp["_root"], "state.json")):
            print(i18n.t("cli.deliver.nostate", lang), file=sys.stderr)
            return 1
        result = campaign.deliver(camp["_root"], lang=lang)
        if result["exported"] == 0 and result["regen"] == 0:
            print(i18n.t("cli.deliver.empty", lang))
            return 0
        print(i18n.t("cli.deliver.summary", lang, exported=result["exported"],
                     dir=result["delivery_dir"], regen=result["regen"], req=result["requests_path"]))
        print("  " + i18n.t("cli.deliver.next", lang, req=result["requests_path"]))
        if result.get("ppc"):
            print("  " + i18n.t("cli.deliver.ppc", lang, dir=result["ppc"]["dir"],
                                n=len(result["ppc"]["files"])))
        return 0

    if args.cmd == "ppc":
        from . import ppc
        root = camp["_root"]
        if not os.path.isfile(os.path.join(root, "state.json")):
            print(i18n.t("cli.ppc.nostate", lang), file=sys.stderr)
            return 1
        s = ppc.export(root, all_pieces=args.all, lang=lang)
        if not s["meta"] and not s["google_display"] and not s["google_rsa"] and not s["manifest"]:
            print(i18n.t("cli.ppc.empty", lang))
            return 0
        print(i18n.t("cli.ppc.summary", lang, meta=s["meta"], display=s["google_display"],
                     rsa=s["google_rsa"], manifest=s["manifest"], dir=s["dir"], n=len(s["files"])))
        if not s["xlsx"]:
            print("  " + i18n.t("cli.ppc.xlsxoff", lang))
        return 0

    if args.cmd == "review":
        server, url = ui.serve(camp["_root"], args.port, open_browser=not args.no_open, lang=lang)
        print("  " + i18n.t("cli.ctrlc", lang))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())