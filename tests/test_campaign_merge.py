"""Tests for campaign._merge_prior (working-queue timestamps)."""

import json
import os
import tempfile
import unittest

from kit import campaign


def _piece(pid, status, **kw):
    p = {"id": pid, "concept": "clean", "format": "meta_feed_square",
         "path": f"clean/{pid}.png", "status": status}
    p.update(kw)
    return p


class MergePriorTest(unittest.TestCase):
    def test_rerendered_redo_gets_updated_at(self):
        with tempfile.TemporaryDirectory() as root:
            prior = [_piece("p1", "approved", delivered=True),
                     _piece("p2", "redo", note="bigger logo", decided_at="2026-11-23T10:00:00Z"),
                     _piece("p3", "rejected", decided_at="2026-11-23T10:00:00Z")]
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": prior}, f)
            fresh = [_piece("p1", "pending"), _piece("p2", "pending"), _piece("p3", "pending")]
            merged = campaign._merge_prior(root, fresh)
            by_id = {p["id"]: p for p in merged}
            self.assertEqual(by_id["p1"]["status"], "approved")
            self.assertTrue(by_id["p1"]["delivered"])
            self.assertNotIn("updated_at", by_id["p1"])
            self.assertTrue(by_id["p2"]["updated_at"])
            self.assertTrue(by_id["p3"]["updated_at"])

    def test_unrerendered_pieces_kept(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": [_piece("p9", "pending")]}, f)
            merged = campaign._merge_prior(root, [_piece("p1", "pending")])
            self.assertEqual({p["id"] for p in merged}, {"p1", "p9"})


class DeliverLockTest(unittest.TestCase):
    def test_locked_while_batch_queued(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as desktop:
            os.environ["KIT_DESKTOP_DIR"] = desktop
            try:
                with open(os.path.join(root, "campaign.json"), "w", encoding="utf-8") as f:
                    json.dump({"name": "demo", "brand": "acme"}, f)
                with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                    json.dump({"pieces": [_piece("p1", "approved"),
                                          _piece("p2", "redo", note="x", queued=True)]}, f)
                r = campaign.deliver(root)
                self.assertEqual(r["locked"], 1)
                self.assertEqual(r["exported"], 0)
                with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                    json.dump({"pieces": [_piece("p1", "approved"),
                                          _piece("p2", "pending")]}, f)
                r = campaign.deliver(root)
                self.assertEqual(r.get("locked", 0), 0)
            finally:
                os.environ.pop("KIT_DESKTOP_DIR", None)


if __name__ == "__main__":
    unittest.main()
