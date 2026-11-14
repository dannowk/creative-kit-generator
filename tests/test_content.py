import os
import tempfile
import unittest

from kit import content


class ReadSheet(unittest.TestCase):
    def test_csv_with_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                f.write("conceito,gancho,uso\n clean,Hello,ppc\n")
            rows = content.read_sheet(p)
        self.assertEqual(rows, [{"concept": "clean", "hook": "Hello", "use": "ppc"}])

    def test_xlsx_canonical_headers(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.xlsx")
            wb = Workbook()
            ws = wb.active
            ws.append(["concept", "hook", "kicker", "use"])
            ws.append(["clean", "Hello", "World", "both"])
            ws.append(["clean", "", "empty hook row", ""])
            wb.save(p)
            rows = content.read_sheet(p)
        self.assertEqual(rows[0], {"concept": "clean", "hook": "Hello",
                                   "kicker": "World", "use": "both"})
        self.assertEqual(rows[1].get("hook", ""), "")

    def test_blank_use_defaults_to_both(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write("concept,hook\nclean,Hi\n")
            rows = content.read_sheet(p)
        self.assertEqual(rows[0]["use"], "both")

    def test_unknown_extension_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.txt")
            open(p, "w").write("concept,hook\n")
            with self.assertRaises(ValueError):
                content.read_sheet(p)


class Validate(unittest.TestCase):
    def test_ok(self):
        rows = [{"concept": "clean", "hook": "Hi", "use": "both",
                 "status": "approved", "origin": "sheet"}]
        self.assertEqual(content.validate(rows, ["clean"]), [])

    def test_unknown_concept(self):
        rows = [{"concept": "nope", "hook": "Hi", "use": "both",
                 "status": "approved", "origin": "sheet"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("nope" in e for e in errs))

    def test_bad_use(self):
        rows = [{"concept": "clean", "hook": "Hi", "use": "banner",
                 "status": "approved", "origin": "sheet"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("use" in e for e in errs))

    def test_empty_hook(self):
        rows = [{"concept": "clean", "hook": "", "use": "both",
                 "status": "approved", "origin": "sheet"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("hook" in e for e in errs))


class Ingest(unittest.TestCase):
    def test_writes_content_json(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            cdir = os.path.join(d, "content")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
                f.write("concept,hook,use\nclean,Hi,ppc\n")
            with open(os.path.join(cdir, "content_link.txt"), "w", encoding="utf-8") as f:
                f.write("https://sharepoint.example/base.xlsx\n")
            camp = {"_root": d, "concepts": ["clean"]}
            summary = content.ingest(camp)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["link"], "https://sharepoint.example/base.xlsx")
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["rows"], [{"concept": "clean", "hook": "Hi", "use": "ppc",
                                              "id": "c01", "origin": "sheet", "status": "approved"}])

    def test_no_sheet_is_gap_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            camp = {"_root": d, "concepts": ["clean"]}
            summary = content.ingest(camp)
            self.assertEqual(summary["rows"], 0)
            self.assertTrue(summary["gaps"])
            self.assertEqual(summary["errors"], [])


class Apply(unittest.TestCase):
    def _camp(self, d, rows):
        import json
        cdir = os.path.join(d, "content")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook,use\n" + "\n".join(
                f"{r['concept']},{r['hook']},{r.get('use', 'both')}" for r in rows) + "\n")
        with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"concepts": ["clean"], "copy": {"default": {"other": {"hook": "keep"}}}}, f)
        content.ingest({"_root": d, "concepts": ["clean"]})
        return {"_root": d, "concepts": ["clean"]}

    def test_base_and_versions(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "V1"},
                                  {"concept": "clean", "hook": "V2", "use": "ppc"}])
            summary = content.apply(camp)
            self.assertEqual(summary["errors"], [])
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            entry = campj["copy"]["default"]["clean"]
            self.assertEqual(entry["hook"], "V1")
            self.assertEqual(entry["versions"], [{"hook": "V2", "use": "ppc"}])
            self.assertEqual(campj["copy"]["default"]["other"], {"hook": "keep"})

    def test_axis_key(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "Hi"}])
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                cj = json.load(f)
            cj["rows"][0]["axis"] = "BC|Course-02"
            with open(os.path.join(d, "content.json"), "w", encoding="utf-8") as f:
                json.dump(cj, f)
            content.apply(camp)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            self.assertIn("clean", campj["copy"]["BC|Course-02"])

    def test_errors_block_apply(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "Hi", "use": "banner"}])
            summary = content.apply(camp)
            self.assertTrue(summary["errors"])
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            self.assertNotIn("clean", campj["copy"]["default"])


class Cli(unittest.TestCase):
    def test_content_ingest_and_apply(self):
        import io
        import json
        from contextlib import redirect_stdout
        from kit import cli
        with tempfile.TemporaryDirectory() as d:
            cdir = os.path.join(d, "content")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
                f.write("concept,hook\nclean,Hi\n")
            with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
                json.dump({"concepts": ["clean"]}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli.main(["content", d])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join(d, "content.json")))
            with redirect_stdout(buf):
                rc = cli.main(["content", d, "--apply"])
            self.assertEqual(rc, 0)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["copy"]["default"]["clean"]["hook"], "Hi")


class Wizard(unittest.TestCase):
    def test_slot_and_link_in_status(self):
        from kit import onboard
        with tempfile.TemporaryDirectory() as d:
            onboard.scaffold(d)
            self.assertTrue(os.path.isdir(os.path.join(d, "content")))
            with open(os.path.join(d, "content_link.txt"), "w", encoding="utf-8") as f:
                f.write("https://sharepoint.example/base.xlsx\n")
            st = onboard.status(d)
            self.assertIn("content", st["slots"])
            self.assertEqual(st["content_link"], "https://sharepoint.example/base.xlsx")
            self.assertFalse(st["slots"]["content"]["required"])

    def test_intake_collects_content(self):
        from kit import intake
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "content"))
            p = os.path.join(d, "content", "base.csv")
            open(p, "w").write("concept,hook\nclean,Hi\n")
            inv = intake.inventory(d)
            self.assertEqual(inv["content"], [p])


class BriefingSection(unittest.TestCase):
    def test_section_11_present_both_langs(self):
        from kit import onboard
        for tmpl, marker in ((onboard.BRIEFING_TEMPLATE, "_preencher"),
                             (onboard.BRIEFING_TEMPLATE_EN, "_fill in")):
            self.assertIn("## 11.", tmpl)
            self.assertIn(marker, tmpl.split("## 11.")[1])

    def test_section_11_not_required(self):
        from kit import onboard
        with tempfile.TemporaryDirectory() as d:
            onboard.scaffold(d)
            st = onboard.status(d)
            self.assertFalse(any(t.startswith("11.") for t in st["briefing"]["missing"]))


class RenderRouting(unittest.TestCase):
    def test_ppc_only_copy_skips_images(self):
        from kit import campaign as C
        camp = C.load_campaign("campaigns/acme-launch")
        entries = [e for concepts in (camp.get("copy") or {}).values()
                   if isinstance(concepts, dict) for e in concepts.values()
                   if isinstance(e, dict)]
        self.assertTrue(entries)
        for e in entries:
            e["hook"] = e.get("hook") or "Hi"
            e["use"] = "ppc"
        state = C.run(camp, dry=True)
        self.assertEqual(state["pieces"], [])
        for e in entries:
            e["use"] = "both"
        state = C.run(camp, dry=True)
        self.assertTrue(state["pieces"])


class Sample(unittest.TestCase):
    def _book(self, lang):
        from io import BytesIO
        from openpyxl import load_workbook
        return load_workbook(BytesIO(content.sample_xlsx(lang)))

    def _example_rows(self, wb):
        tab = wb["Exemplos"] if "Exemplos" in wb.sheetnames else wb["Examples"]
        dicts = [dict(zip(content.COLUMNS, [c.value for c in row]))
                 for row in tab.iter_rows(min_row=2)]
        return content._stamp(content._rows_from_dicts(dicts))

    def test_tabs_and_clean_template(self):
        wb = self._book("en")
        self.assertEqual(wb.sheetnames, ["Template", "Examples"])
        tpl = wb["Template"]
        self.assertEqual([c.value for c in tpl[1]], list(content.COLUMNS))
        self.assertEqual(tpl.max_row, 1)

    def test_examples_valid_and_cover_routing(self):
        rows = self._example_rows(self._book("en"))
        self.assertEqual(content.validate(rows, ["clean", "editorial", "cinema"]), [])
        self.assertEqual({r["use"] for r in rows}, {"image", "ppc", "both"})
        pairs = [(r["concept"], r.get("axis", "")) for r in rows]
        self.assertTrue(len(pairs) != len(set(pairs)))  # repeated pair = versions demo

    def test_pt_localized(self):
        wb = self._book("pt")
        self.assertEqual(wb.sheetnames, ["Modelo", "Exemplos"])
        rows = self._example_rows(wb)
        self.assertTrue(all(r["lang"] == "pt" for r in rows))
        self.assertEqual(content.validate(rows, ["clean", "editorial", "cinema"]), [])

    def test_wizard_link_and_endpoint(self):
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer
        from kit import ui
        for lang in ("pt", "en"):
            self.assertIn("/content-sample", ui.onboard_page(lang))
        with tempfile.TemporaryDirectory() as d:
            ui.Handler.root, ui.Handler.mode = d, "onboard"
            srv = ThreadingHTTPServer(("127.0.0.1", 0), ui.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            try:
                url = f"http://127.0.0.1:{srv.server_address[1]}/content-sample?lang=en"
                with urllib.request.urlopen(url) as r:
                    data = r.read()
                    self.assertEqual(r.status, 200)
                    self.assertIn("attachment", r.headers["Content-Disposition"])
                    self.assertIn("spreadsheetml", r.headers["Content-Type"])
            finally:
                srv.shutdown()
                srv.server_close()
        self.assertTrue(data.startswith(b"PK"))


class PpcRouting(unittest.TestCase):
    def _brand(self):
        from kit import campaign as C
        return C.brand_for(C.load_campaign("campaigns/acme-launch"))

    def _camp(self):
        return {"slug": "t", "concepts": ["clean"], "cta": "Learn more",
                "copy": {"default": {"clean": {
                    "hook": "Base", "kicker": "K", "program": "P", "cta": "Buy",
                    "use": "both",
                    "versions": [{"hook": "V2", "use": "ppc"}]}}}}

    def _piece(self):
        return {"id": "p1", "concept": "clean", "format": "meta_feed_square",
                "axes": {}, "path": "clean/p1.png", "status": "approved"}

    def test_copy_for_carries_use_and_versions(self):
        from kit import ppc
        c = ppc._copy_for(self._camp(), {}, "clean")
        self.assertEqual(c["use"], "both")
        self.assertEqual(c["versions"], [{"hook": "V2", "use": "ppc"}])

    def test_meta_one_row_per_version(self):
        from kit import ppc
        rows = ppc._meta_rows([self._piece()], self._camp(), self._brand())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Ad Name"], "p1")
        self.assertEqual(rows[1]["Ad Name"], "p1_V1")
        self.assertEqual(rows[1]["Body"], "V2")

    def test_image_only_excluded(self):
        from kit import ppc
        camp = self._camp()
        camp["copy"]["default"]["clean"]["use"] = "image"
        self.assertEqual(ppc._meta_rows([self._piece()], camp, self._brand()), [])

    def test_ppc_only_extra_rows(self):
        from kit import ppc
        camp = self._camp()
        camp["copy"]["default"]["clean"]["use"] = "ppc"
        rows = ppc._ppc_only_rows(camp, self._brand())
        self.assertEqual(len(rows), 2)  # base + 1 version
        self.assertEqual(rows[0]["Body"], "Base")