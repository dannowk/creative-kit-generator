"""campaign-kit CLI: onboard -> intake -> assets -> render -> review -> deliver.

  python3 -m kit.cli onboard ~/inbox/acme
  python3 -m kit.cli intake ~/inbox/acme acme
  python3 -m kit.cli assets campaigns/acme-launch
  python3 -m kit.cli render campaigns/acme-launch
  python3 -m kit.cli review campaigns/acme-launch
  python3 -m kit.cli deliver campaigns/acme-launch   # step 6: the review's Continue
  python3 -m kit.cli ppc campaigns/acme-launch        # bulk-upload sheets (Meta + Google)
"""

import argparse
import json
import os
import sys

from . import briefing, campaign, copy, i18n, intake, onboard, providers, render, ui, video

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    # Windows console (cp1252) can't encode the kit's Unicode symbols (➜, ✓, ≈): force UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="campaign-kit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("intake", help="derive a brand from the dropped folder")
    p.add_argument("inbox")
    p.add_argument("brand_id")

    p = sub.add_parser("brief", help="canonical briefing: validate gaps/errors and (--apply) write brand.yaml + campaign.json")
    p.add_argument("file", nargs="?", help="filled briefing (.yaml/.json)")
    p.add_argument("--apply", action="store_true", help="apply the briefing (writes brand + campaign)")
    p.add_argument("--template", action="store_true", help="print the markdown template generated from the schema")
    p.add_argument("--normalize", metavar="FILE", help="prepare normalizing a free-form briefing (prose/PDF/docx) into the schema")
    p.add_argument("--out", help="target of --normalize (default: <source-folder>/briefing.yaml)")

    p = sub.add_parser("assets", help="cost notice + AI asset generation (image and video)")
    p.add_argument("campaign")

    p = sub.add_parser("render", help="render the piece matrix")
    p.add_argument("campaign")
    p.add_argument("--concepts", nargs="*")
    p.add_argument("--formats", nargs="*")
    p.add_argument("--ids", nargs="*", help="re-render only these pieces (step 6: recreate/redo)")
    p.add_argument("--limit", type=int)
    p.add_argument("--dry", action="store_true")

    p = sub.add_parser("video", help="edit video: trim, subject-aware reframe, brand overlay, concat, captions")
    p.add_argument("campaign")

    p = sub.add_parser("review", help="local approval UI")
    p.add_argument("campaign")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="don't open the browser (headless)")

    p = sub.add_parser("deliver", help="step 6: export approved + queue recreate/redo (the review's Continue)")
    p.add_argument("campaign")

    p = sub.add_parser("ppc", help="bulk-upload sheets for the PPC team (Meta + Google), CSV + XLSX")
    p.add_argument("campaign")
    p.add_argument("--all", action="store_true", help="export all pieces, not just approved ones")

    p = sub.add_parser("plan", help="art direction from the briefing + references")
    p.add_argument("campaign")

    p = sub.add_parser("onboard", help="prepare the campaign folder (briefing, refs, fonts, logo, photos, videos)")
    p.add_argument("inbox")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--no-ui", action="store_true", help="scaffold + checklist only, no server")
    p.add_argument("--no-open", action="store_true", help="don't open the browser (headless)")

    p = sub.add_parser("copy", help="Copy Kit: standalone copy (PPC + overlay), skill /campaign-kit:copy")
    p.add_argument("action", choices=["onboard", "plan", "validate", "review", "deliver"])
    p.add_argument("folder")
    p.add_argument("--port", type=int, default=None, help="UI port (default: onboard 8767, review 8768)")
    p.add_argument("--no-ui", action="store_true", help="scaffold + checklist only, no server")
    p.add_argument("--no-open", action="store_true", help="don't open the browser (headless)")

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
            extract = i18n.t("cli.normalize.extract") if summary["needs_extraction"] else ""
            print("\n" + i18n.t("cli.normalize.header", contract=summary["contract"],
                                skeleton=summary["skeleton"], extract=extract))
            return 0
        if args.template:
            print(briefing.template_md())
            return 0
        if not args.file:
            ap.error(i18n.t("cli.brief.needfile"))
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
            print("\n" + i18n.t("cli.brief.next", campaign=summary["campaign"]))
            if summary["palette_proposed"]:
                print(i18n.t("cli.palette.proposed"))
            return 0
        v = briefing.validate(struct, base)
        status = i18n.t("cli.appliable" if v["ok"] else "cli.notappliable")
        print(i18n.t("cli.briefsummary", status=status, errors=len(v["errors"]),
                     reqgaps=sum(g["required"] for g in v["gaps"]),
                     optgaps=sum(not g["required"] for g in v["gaps"])))
        for e in v["errors"]:
            print("  " + i18n.t("cli.err", field=e["field"], message=e["message"]), file=sys.stderr)
        for g in v["gaps"]:
            tag = i18n.t("cli.gap.req" if g["required"] else "cli.gap.opt")
            print(f"  [{tag}] {g['field']}: {g['question']}")
            print(f"          {g['why']}")
        return 0 if v["ok"] else 1

    if args.cmd == "onboard":
        inbox = os.path.expanduser(args.inbox)
        brief = onboard.scaffold(inbox)
        st = onboard.status(inbox)
        print(i18n.t("cli.folder", inbox=st["inbox"]))
        for s in st["slots"].values():
            mark = i18n.t("cli.mark.ok" if s["ok"] else
                          ("cli.mark.missing" if s["required"] else "cli.mark.optional"))
            print("  " + i18n.t("cli.slotline", mark=mark, label=s["label"],
                                n=len(s["files"]), hint=s["hint"]))
        print("  " + i18n.t("cli.briefline", path=brief,
                            n=len(st["briefing"]["missing"])))
        if args.no_ui:
            return 0
        server, url = ui.serve_onboard(inbox, os.path.join(ROOT, "brands"), args.port,
                                       open_browser=not args.no_open)
        print("  " + i18n.t("cli.ctrlc"))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0

    if args.cmd == "intake":
        summary, gaps = intake.run(os.path.expanduser(args.inbox), args.brand_id,
                                   os.path.join(ROOT, "brands"))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print("\n" + i18n.t("cli.gaps.one", n=len(gaps)), file=sys.stderr)
        for g in gaps:
            print(f"  [{g['field']}] {g['question']}", file=sys.stderr)
        return 0

    if args.cmd == "copy":
        folder = os.path.expanduser(args.folder)
        if args.action == "onboard":
            copy.scaffold(folder)
            print("Copy Kit — folder ready: " + folder)
            print("  briefing.md  ← fill in the copy briefing")
            print("  examples.txt ← paste example texts")
            print("  (no logo/brandbook/refs — copy is text only)")
            if args.no_ui:
                print("Next: fill briefing + examples, then `copy plan <folder>`.")
                return 0
            from . import copy_ui
            server, url = copy_ui.serve_onboard(folder, args.port or 8767,
                                                open_browser=not args.no_open)
            print("  " + i18n.t("cli.ctrlc"))
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                server.shutdown()
            return 0
        if args.action == "plan":
            brief = copy.read_text(folder, "briefing.md")
            examples = copy.read_text(folder, "examples.txt")
            print("COPY — content direction (read before generating):")
            print("  briefing:\n" + (brief or "(empty)"))
            print("  examples:\n" + (examples or "(empty)"))
            print("  destinations / kinds:")
            print("    ppc:     headline (≤30 for Google RSA), description (≤90), primary_text")
            print("    overlay: hook, kicker, program, cta")
            print("  YOUR JOB: author "
                  + os.path.join(folder, "copy.json") + ' = {"concepts":[...], "rows":[...]}')
            print("    each row: id, destination(ppc/overlay), concept, axis, kind, text, "
                  "lang(en), status:\"pending\", origin:\"agent\", updated_at, updated_by.")
            print("    Never invent copy beyond briefing+examples; never mark approved (the user does).")
            print("    Then: copy validate <folder> → copy review <folder>.")
            return 0
        if args.action == "validate":
            if not os.path.isfile(os.path.join(folder, "copy.json")):
                print("copy.json missing — generate the copy first (copy plan).", file=sys.stderr)
                return 1
            data = copy.load(folder)
            errs = copy.validate(data)
            rows = data.get("rows") or []
            counts = {s: sum(1 for r in rows if r.get("status") == s) for s in copy.STATUSES}
            print("copy.json: " + str(len(rows)) + " rows — "
                  + ", ".join(f"{k}:{v}" for k, v in counts.items()))
            for e in errs:
                print("  " + e, file=sys.stderr)
            print("OK — appliable." if not errs
                  else f"{len(errs)} error(s) — nothing written.")
            return 0 if not errs else 1
        if args.action == "review":
            if not os.path.isfile(os.path.join(folder, "copy.json")):
                print("copy.json missing — generate the copy first (copy plan).", file=sys.stderr)
                return 1
            from . import copy_ui
            server, url = copy_ui.serve_review(folder, args.port or 8768,
                                               open_browser=not args.no_open)
            print("  " + i18n.t("cli.ctrlc"))
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                server.shutdown()
            return 0
        if args.action == "deliver":
            if not os.path.isfile(os.path.join(folder, "copy.json")):
                print("copy.json missing — generate the copy first (copy plan).", file=sys.stderr)
                return 1
            s = copy.deliver(folder)
            if s["exported"] == 0:
                print("No approved copy to export — approve rows in the review first.")
                return 0
            print("Exported " + str(s["exported"]) + " approved rows → " + s["dir"])
            print("  files: " + ", ".join(s["files"]))
            if s["warnings"]:
                print("  RSA limit warnings (truncated): "
                      + ", ".join(f"{w['id']} {w['kind']} {w['chars']}>{w['limit']}" for w in s["warnings"]))
            if not s["xlsx"]:
                print("  XLSX unavailable (openpyxl missing) — CSV only.")
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
            print(i18n.t("cli.provider.agent", path=e.jobs_path))
            with open(e.jobs_path, encoding="utf-8") as f:
                print(json.dumps(json.load(f)["jobs"], indent=2, ensure_ascii=False))
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "render":
        state = campaign.run(camp, only_concepts=args.concepts, only_formats=args.formats,
                             limit=args.limit, dry=args.dry, only_ids=args.ids)
        print(i18n.t("cli.render.summary", n=len(state["pieces"]),
                     blocked=state["blocked_count"], concepts=", ".join(state["concepts"])))
        for p in state["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    print("  " + i18n.t("cli.render.blocked", id=p["id"], message=f["message"]))
        if state["font_warnings"]["substituted"]:
            print("  " + i18n.t("cli.render.fonts", fonts=state["font_warnings"]["substituted"]))
        if not args.dry:
            print("  " + i18n.t("cli.render.next", campaign=args.campaign))
        return 0

    if args.cmd == "video":
        result = video.run(camp)
        if not result["count"]:
            print(i18n.t("cli.video.none"))
            return 0
        print(i18n.t("cli.video.summary", n=result["count"], blocked=result["blocked"],
                     concepts=", ".join(result["concepts"])))
        for p in result["pieces"]:
            for f in p["findings"]:
                if f["level"] == "fail":
                    print("  " + i18n.t("cli.render.blocked", id=p["id"], message=f["message"]))
        print("  " + i18n.t("cli.render.next", campaign=args.campaign))
        return 0

    if args.cmd == "plan":
        brand = campaign.brand_for(camp)
        intake_path = os.path.join(brand.root, "intake.json")
        info = {}
        if os.path.isfile(intake_path):
            with open(intake_path, encoding="utf-8") as f:
                info = json.load(f)
        print("ART DIRECTION — read before choosing layout:")
        print("  briefing:", ", ".join(info.get("briefs") or []) or "(none in the folder)")
        answers_path = os.path.join(brand.root, "answers.json")
        if os.path.isfile(answers_path):
            with open(answers_path, encoding="utf-8") as f:
                answers = json.load(f)
            print("  onboarding answers (apply them to brand.yaml this round):")
            for k, v in answers.items():
                if v:
                    print(f"   [{k}] {v}")
        print("  references (LOOK with vision, not just the pixels):")
        for r in info.get("refs") or []:
            print("   -", r)
        brandbook = info.get("brandbook") or []
        if brandbook:
            print("  brandbook (READ — vision for PDF/image: colors, typography, logo usage, voice):")
            for b in brandbook:
                print("   -", b)
            print("   → brandbook rules prevail over the proposed palette; a conflict with the briefing becomes a question.")
        brief_docs = info.get("brief_docs") or []
        if brief_docs:
            print("  briefing support documents (READ all — text/spreadsheet; vision for PDF/image):")
            for b in brief_docs:
                print("   -", b)
            print("   → ad copy/content feeds campaign.json.copy (hook/kicker/program/CTA per concept/axis);")
            print("     layout rules, safe areas and logo safety become geometry/safe_zones and compliance in brand.yaml")
            print("     and in the templates. A conflict with the briefing becomes a question — don't guess.")
        print("  fill in reference_analysis:", ", ".join((info.get("reference_analysis") or {}).keys()))
        concepts_req = info.get("concepts_requested") or []
        if concepts_req:
            print("  concepts requested in the briefing:", ", ".join(concepts_req))
            print("   → author one templates/<concept>.yaml per concept, list them in campaign.json.concepts")
            print("     and give a copy.hook per concept (without a hook, the concept is skipped in render).")
        else:
            print("  concepts: not specified in the briefing — ask or propose directions from the refs.")
        print("\n  The global library (templates/) is a STARTING POINT, not the destination.")
        print("  Author/adjust campaigns/<slug>/templates/<concept>.yaml from the briefing")
        print("  and the refs; the local spec wins over the global one. Available ops:")
        print("   ", ", ".join(render.OPS))
        print("  Type treatment per layer: underline, accent_upper, accent_scale.")
        print("\n  Honest limit: these ops cover photographic/typographic directions.")
        print("  A radically different look (flat illustration, 3D, collage) needs a")
        print("  provider-generated image or new ops — it won't come out of these specs by magic.")
        return 0

    if args.cmd == "deliver":
        if not os.path.isfile(os.path.join(camp["_root"], "state.json")):
            print(i18n.t("cli.deliver.nostate"), file=sys.stderr)
            return 1
        result = campaign.deliver(camp["_root"])
        if result["exported"] == 0 and result["regen"] == 0:
            print(i18n.t("cli.deliver.empty"))
            return 0
        print(i18n.t("cli.deliver.summary", exported=result["exported"],
                     dir=result["delivery_dir"], regen=result["regen"], req=result["requests_path"]))
        print("  " + i18n.t("cli.deliver.next", req=result["requests_path"]))
        if result.get("ppc"):
            print("  " + i18n.t("cli.deliver.ppc", dir=result["ppc"]["dir"],
                                n=len(result["ppc"]["files"])))
        return 0

    if args.cmd == "ppc":
        from . import ppc
        root = camp["_root"]
        if not os.path.isfile(os.path.join(root, "state.json")):
            print(i18n.t("cli.ppc.nostate"), file=sys.stderr)
            return 1
        s = ppc.export(root, all_pieces=args.all)
        if not s["meta"] and not s["google_display"] and not s["google_rsa"] and not s["manifest"]:
            print(i18n.t("cli.ppc.empty"))
            return 0
        print(i18n.t("cli.ppc.summary", meta=s["meta"], display=s["google_display"],
                     rsa=s["google_rsa"], manifest=s["manifest"], dir=s["dir"], n=len(s["files"])))
        if not s["xlsx"]:
            print("  " + i18n.t("cli.ppc.xlsxoff"))
        return 0

    if args.cmd == "review":
        server, url = ui.serve(camp["_root"], args.port, open_browser=not args.no_open)
        print("  " + i18n.t("cli.ctrlc"))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0


if __name__ == "__main__":
    sys.exit(main())