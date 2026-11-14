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