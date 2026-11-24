"""Tests for the asset approval stage: generate -> approve/redo -> regenerate -> render unlocked."""

import json
import os
import tempfile
import threading
import time
import unittest

from kit import assets, campaign
from kit.providers.base import record_manifest


def _piece(pid, status, **kw):
    p = {"id": pid, "concept": "clean", "format": "meta_feed_square",
         "path": f"clean/{pid}.png", "status": status, "asset": "job-01.png"}
    p.update(kw)
    return p


def _write(root, rel, body=b"png-bytes"):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(body)
    return rel


def _entry(rel, sha, job="job-01", kind="image", credits=1):
    return {"id": job, "provider": "manual", "prompt": "a calm kitchen", "kind": kind,
            "aspect": "1:1", "credits": credits, "path": rel, "sha": sha}


class AssetStateTest(unittest.TestCase):
    def test_manifest_becomes_pending_assets(self):
        with tempfile.TemporaryDirectory() as root:
            rel = _write(root, "assets/job-01.png")
            record_manifest(root, [_entry(rel, "sha-a")])
            state = assets.load(root)
            self.assertEqual(len(state["assets"]), 1)
            a = state["assets"][0]
            self.assertEqual((a["status"], a["job"], a["sha"]), ("pending", "job-01", "sha-a"))
            self.assertEqual(assets.counts(state), {"pending": 1, "approved": 0,
                                                    "rejected": 0, "redo": 0})

    def test_a_new_sha_resets_to_pending_and_keeps_other_decisions(self):
        with tempfile.TemporaryDirectory() as root:
            a_rel = _write(root, "assets/job-01.png")
            b_rel = _write(root, "assets/job-02.png")
            record_manifest(root, [_entry(a_rel, "sha-a", job="job-01"),
                                   _entry(b_rel, "sha-b", job="job-02")])
            self.assertTrue(assets.decide(root, a_rel, "approved"))
            self.assertTrue(assets.decide(root, b_rel, "redo", note="softer light"))

            _write(root, b_rel, b"regenerated")
            record_manifest(root, [_entry(b_rel, "sha-b2", job="job-02")])
            state = assets.load(root)
            by_path = {a["path"]: a for a in state["assets"]}
            self.assertEqual(by_path[a_rel]["status"], "approved")
            self.assertEqual(by_path[b_rel]["status"], "pending")
            self.assertEqual(by_path[b_rel]["sha"], "sha-b2")
            self.assertEqual(by_path[b_rel]["note"], "")

    def test_a_missing_file_leaves_the_state(self):
        with tempfile.TemporaryDirectory() as root:
            rel = _write(root, "assets/job-01.png")
            record_manifest(root, [_entry(rel, "sha-a")])
            assets.load(root)
            os.remove(os.path.join(root, rel))
            self.assertEqual(assets.load(root)["assets"], [])

    def test_decide_queues_the_asset_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            rel = _write(root, "assets/job-01.png")
            record_manifest(root, [_entry(rel, "sha-a")])
            self.assertFalse(assets.decide(root, rel, "redo"))
            self.assertTrue(assets.decide(root, rel, "redo", note="  no hands  "))
            with open(os.path.join(root, "assets", "requests.json"), encoding="utf-8") as f:
                batch = json.load(f)
            self.assertEqual(len(batch), 1)
            self.assertEqual(batch[0]["stage"], "assets")
            self.assertEqual(batch[0]["note"], "no hands")
            self.assertEqual(batch[0]["job"], "job-01")
            self.assertEqual(assets.jobs_for(batch), ["job-01"])

    def test_decide_rejects_unknown_path_and_status(self):
        with tempfile.TemporaryDirectory() as root:
            rel = _write(root, "assets/job-01.png")
            record_manifest(root, [_entry(rel, "sha-a")])
            self.assertFalse(assets.decide(root, "assets/nope.png", "approved"))
            self.assertFalse(assets.decide(root, rel, "maybe"))

    def test_all_approved_gates_the_render(self):
        with tempfile.TemporaryDirectory() as root:
            a_rel = _write(root, "assets/job-01.png")
            b_rel = _write(root, "assets/job-02.png")
            record_manifest(root, [_entry(a_rel, "sha-a", job="job-01"),
                                   _entry(b_rel, "sha-b", job="job-02")])
            self.assertEqual(assets.all_approved(root), (False, 2))
            self.assertEqual(len(assets.unapproved(root)), 2)
            assets.decide(root, a_rel, "approved")
            assets.decide(root, b_rel, "approved")
            self.assertEqual(assets.all_approved(root), (True, 2))
            self.assertEqual(assets.unapproved(root), [])

    def test_all_approved_is_false_when_nothing_was_generated(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(assets.all_approved(root), (False, 0))


class TwoStageWaitTest(unittest.TestCase):
    def _campaign_with_assets(self, root):
        rel = _write(root, "assets/job-01.png")
        record_manifest(root, [_entry(rel, "sha-a")])
        with open(os.path.join(root, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "demo", "slug": "demo", "brand": "acme"}, f)
        return rel

    def test_wait_returns_a_marked_asset(self):
        with tempfile.TemporaryDirectory() as root:
            rel = self._campaign_with_assets(root)

            def mark():
                time.sleep(0.3)
                assets.decide(root, rel, "redo", note="different framing")

            threading.Thread(target=mark).start()
            batch = campaign.wait_batch(root, timeout=10, interval=0.1)
            self.assertEqual([b["id"] for b in batch], [rel])
            self.assertEqual(batch[0]["stage"], "assets")

    def test_wait_signals_when_every_asset_is_approved(self):
        with tempfile.TemporaryDirectory() as root:
            rel = self._campaign_with_assets(root)
            self.assertTrue(assets.decide(root, rel, "approved"))
            batch = campaign.wait_batch(root, timeout=0.3, interval=0.1)
            self.assertEqual(batch, [{"stage": "assets", "reason": "all_approved",
                                      "id": None, "count": 1}])

    def test_wait_still_waits_for_pieces_after_a_render(self):
        with tempfile.TemporaryDirectory() as root:
            rel = self._campaign_with_assets(root)
            assets.decide(root, rel, "approved")
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": [_piece("p1", "pending")]}, f)
            self.assertEqual(campaign.wait_batch(root, timeout=0.3, interval=0.1), [])

    def test_wait_merges_both_stages(self):
        with tempfile.TemporaryDirectory() as root:
            rel = self._campaign_with_assets(root)
            assets.decide(root, rel, "rejected")
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": [_piece("p1", "redo", note="bigger logo")]}, f)
            batch = campaign.wait_batch(root, timeout=0.3, interval=0.1)
            self.assertEqual({b["stage"] for b in batch}, {"assets", "pieces"})


if __name__ == "__main__":
    unittest.main()
