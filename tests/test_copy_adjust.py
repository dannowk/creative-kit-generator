"""Adjust copy: direction note + refs, queued as redo for the whole concept or ticked rows."""

import os
import tempfile
import unittest

from kit import campaign, copy


class CopyAdjust(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        copy.save(self.root, {"concepts": ["clean", "bold"], "rows": [
            {"id": "r1", "concept": "clean", "destination": "ppc", "kind": "headline",
             "text": "One", "status": "approved"},
            {"id": "r2", "concept": "clean", "destination": "ppc", "kind": "description",
             "text": "Two", "status": "pending"},
            {"id": "r3", "concept": "bold", "destination": "overlay", "kind": "hook",
             "text": "Three", "status": "pending"}]})

    def tearDown(self):
        self.tmp.cleanup()

    def _rows(self):
        return {r["id"]: r for r in copy.load(self.root)["rows"]}

    def test_ticked_rows_only(self):
        n = copy.adjust_apply(self.root, "clean", "warmer, shorter", ids=["r1"])
        self.assertEqual(n, 1)
        rows = self._rows()
        self.assertEqual(rows["r1"]["status"], "redo")
        self.assertEqual(rows["r1"]["note"], "warmer, shorter")
        self.assertEqual(rows["r2"]["status"], "pending")
        self.assertEqual(rows["r3"]["status"], "pending")
        st = campaign.load_style(self.root, "clean")
        self.assertEqual(campaign.piece_style(st, "r1")["note"], "warmer, shorter")
        self.assertEqual(campaign.piece_style(st, "r2"), {})

    def test_whole_concept(self):
        n = copy.adjust_apply(self.root, "clean", "no price claims")
        self.assertEqual(n, 2)
        rows = self._rows()
        self.assertEqual(rows["r1"]["status"], "redo")
        self.assertEqual(rows["r2"]["status"], "redo")
        self.assertEqual(rows["r3"]["status"], "pending")
        st = campaign.load_style(self.root, "clean")
        self.assertEqual(st["note"], "no price claims")
        self.assertNotIn("pieces", st)

    def test_requests_queue(self):
        copy.adjust_apply(self.root, "clean", "x", ids=["r2"])
        batch = copy.sync_requests(self.root, copy.load(self.root))
        self.assertEqual([b["id"] for b in batch], ["r2"])

    def test_text_refs_allowed(self):
        saved = campaign.add_ref(self.root, "clean", "voice.md", b"tone: warm",
                                 exts=copy.ADJUST_REF_EXT)
        self.assertEqual(saved, "voice.md")
        self.assertEqual(campaign.list_refs(self.root, "clean"), ["voice.md"])
        with self.assertRaises(ValueError):
            campaign.add_ref(self.root, "clean", "tool.exe", b"x", exts=copy.ADJUST_REF_EXT)


if __name__ == "__main__":
    unittest.main()