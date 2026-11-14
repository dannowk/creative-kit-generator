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
        rows = [{"concept": "clean", "hook": "Hi", "use": "both"}]
        self.assertEqual(content.validate(rows, ["clean"]), [])

    def test_unknown_concept(self):
        rows = [{"concept": "nope", "hook": "Hi", "use": "both"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("nope" in e for e in errs))

    def test_bad_use(self):
        rows = [{"concept": "clean", "hook": "Hi", "use": "banner"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("use" in e for e in errs))

    def test_empty_hook(self):
        rows = [{"concept": "clean", "hook": "", "use": "both"}]
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
            self.assertEqual(saved["rows"], [{"concept": "clean", "hook": "Hi", "use": "ppc"}])

    def test_no_sheet_is_gap_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            camp = {"_root": d, "concepts": ["clean"]}
            summary = content.ingest(camp)
            self.assertEqual(summary["rows"], 0)
            self.assertTrue(summary["gaps"])
            self.assertEqual(summary["errors"], [])