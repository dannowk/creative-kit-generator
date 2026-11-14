import json
import os
import tempfile
import unittest

from kit import content


class StampAndValidate(unittest.TestCase):
    def _sheet(self, d, text="concept,hook\nclean,Hi\n"):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_ingest_stamps_ids_origin_status(self):
        with tempfile.TemporaryDirectory() as d:
            self._sheet(d, "concept,hook\nclean,One\nclean,Two\n")
            content.ingest({"_root": d, "concepts": ["clean"]})
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                rows = json.load(f)["rows"]
        self.assertEqual([r["id"] for r in rows], ["c01", "c02"])
        self.assertTrue(all(r["origin"] == "sheet" and r["status"] == "approved"
                            for r in rows))

    def test_validate_rejects_missing_status(self):
        rows = [{"concept": "clean", "hook": "Hi", "origin": "sheet"}]
        self.assertTrue(any("status" in e for e in content.validate(rows, ["clean"])))

    def test_validate_rejects_bad_origin(self):
        rows = [{"concept": "clean", "hook": "Hi", "status": "approved", "origin": "alien"}]
        self.assertTrue(any("origin" in e for e in content.validate(rows, ["clean"])))

    def test_validate_accepts_stamped(self):
        rows = content._stamp([{"concept": "clean", "hook": "Hi"}])
        self.assertEqual(content.validate(rows, ["clean"]), [])


class ApplyApprovedOnly(unittest.TestCase):
    def _camp(self, d, rows):
        with open(os.path.join(d, "content.json"), "w", encoding="utf-8") as f:
            json.dump({"rows": rows}, f)
        with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"concepts": ["clean"]}, f)
        return {"_root": d, "concepts": ["clean"]}

    def test_only_approved_merged(self):
        with tempfile.TemporaryDirectory() as d:
            rows = content._stamp([{"concept": "clean", "hook": "A"},
                                   {"concept": "clean", "hook": "B"}])
            rows[1]["status"] = "pending"
            summary = content.apply(self._camp(d, rows))
            self.assertEqual(summary["merged"], 1)
            self.assertEqual(summary["pending"], 1)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                copy = json.load(f)["copy"]["default"]["clean"]
            self.assertEqual(copy["hook"], "A")
            self.assertNotIn("versions", copy)

    def test_rejected_and_redo_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            rows = content._stamp([{"concept": "clean", "hook": "A"},
                                   {"concept": "clean", "hook": "B"},
                                   {"concept": "clean", "hook": "C"}])
            rows[1]["status"] = "rejected"
            rows[2]["status"] = "redo"
            summary = content.apply(self._camp(d, rows))
            self.assertEqual(summary["merged"], 1)
            self.assertEqual(summary["pending"], 2)


class DecideAndPayload(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,One\nclean,Two\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def test_decide_marks_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            self.assertTrue(content.decide(d, "c01", "rejected", "mudar"))
            payload = content.review_payload(d)
            row = next(r for r in payload["rows"] if r["id"] == "c01")
            self.assertEqual(row["status"], "rejected")
            self.assertEqual(row["note"], "mudar")
            self.assertEqual(payload["counts"]["rejected"], 1)

    def test_decide_unknown_id_false(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            self.assertFalse(content.decide(d, "nope", "approved"))

    def test_decide_bad_status_raises(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            with self.assertRaises(ValueError):
                content.decide(d, "c01", "bogus")

    def test_review_payload_none_without_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(content.review_payload(d))


class ExportReview(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,Hi\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def test_export_tabs_and_columns(self):
        from unittest import mock
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            with mock.patch("kit.campaign.delivery_dir",
                            return_value=os.path.join(d, "delivery")):
                summary = content.export_review(d, "en")
            self.assertEqual(summary["rows"], 1)
            wb = load_workbook(summary["path"])
            try:
                self.assertEqual(wb.sheetnames, ["Review", "Instructions"])
                self.assertEqual([c.value for c in wb["Review"][1]],
                                 list(content.REVIEW_COLUMNS))
            finally:
                wb.close()

    def test_export_without_content_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                content.export_review(d)


class ImportDecisions(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,One\nclean,Two\nclean,Three\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def _return_xlsx(self, d, rows):
        from openpyxl import Workbook
        p = os.path.join(d, "return.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["id", "decision", "note"])
        for row in rows:
            ws.append(list(row))
        wb.save(p)
        wb.close()
        return p

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "approve", ""),
                                      ("c02", "reject", "mudar"),
                                      ("c03", "", "")])
            summary = content.import_decisions(d, p)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["approved"], 1)
            self.assertEqual(summary["rejected"], 1)
            self.assertEqual(summary["unchanged"], 1)
            rows = {r["id"]: r for r in content.review_payload(d)["rows"]}
            self.assertEqual(rows["c01"]["status"], "approved")
            self.assertEqual(rows["c02"]["status"], "rejected")
            self.assertEqual(rows["c02"]["note"], "mudar")
            self.assertEqual(rows["c03"]["status"], "approved")

    def test_unknown_id_blocks_all(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "reject", ""), ("nope", "approve", "")])
            summary = content.import_decisions(d, p)
            self.assertTrue(summary["errors"])
            rows = {r["id"]: r for r in content.review_payload(d)["rows"]}
            self.assertEqual(rows["c01"]["status"], "approved")  # nothing written

    def test_bad_decision_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "maybe", "")])
            self.assertTrue(content.import_decisions(d, p)["errors"])

    def test_missing_id_column_blocks(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = os.path.join(d, "noid.xlsx")
            wb = Workbook()
            wb.active.append(["decision"])
            wb.active.append(["approve"])
            wb.save(p)
            wb.close()
            self.assertTrue(content.import_decisions(d, p)["errors"])

    def test_pt_decision_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = os.path.join(d, "return.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,decisao,nota\nc01,aprovar,\nc02,rejeitar,ajustar\n")
            summary = content.import_decisions(d, p)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["approved"], 1)
            self.assertEqual(summary["rejected"], 1)