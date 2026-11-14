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