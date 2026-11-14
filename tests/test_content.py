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