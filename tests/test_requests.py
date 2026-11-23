"""Tests for the regeneration loop: mark -> requests.json -> agent waits -> fulfils."""

import json
import os
import tempfile
import threading
import time
import unittest

from kit import campaign, copy


def _piece(pid, status, **kw):
    p = {"id": pid, "concept": "clean", "format": "meta_feed_square",
         "path": f"clean/{pid}.png", "status": status, "asset": "ref-01.png"}
    p.update(kw)
    return p


def _row(rid, status, **kw):
    r = {"id": rid, "destination": "overlay", "concept": "clean", "program": "HCA",
         "axis": "default", "kind": "hook", "text": "Your week, planned.", "lang": "en",
         "status": status, "note": "", "origin": "agent",
         "updated_at": "2026-11-23T10:00:00Z", "updated_by": "agent"}
    r.update(kw)
    return r


class CampaignBatchTest(unittest.TestCase):
    def test_pending_batch_carries_reason_note_and_asset_job(self):
        state = {"pieces": [_piece("p1", "approved"),
                            _piece("p2", "redo", note="different photo", decided_at="2026-11-23T10:00:00Z"),
                            _piece("p3", "rejected")]}
        batch = campaign.pending_batch(state)
        self.assertEqual([b["id"] for b in batch], ["p2", "p3"])
        self.assertEqual(batch[0]["reason"], "redo")
        self.assertEqual(batch[0]["note"], "different photo")
        self.assertEqual(batch[0]["asset_job"], "ref-01")
        self.assertEqual(batch[0]["marked_at"], "2026-11-23T10:00:00Z")
        self.assertEqual(batch[1]["reason"], "rejected")

    def test_sync_requests_writes_only_on_change(self):
        with tempfile.TemporaryDirectory() as root:
            batch = campaign.sync_requests(root, {"pieces": [_piece("p2", "redo", note="x")]})
            path = os.path.join(root, "requests.json")
            self.assertEqual([b["id"] for b in batch], ["p2"])
            first = os.stat(path).st_mtime_ns
            time.sleep(0.01)
            campaign.sync_requests(root, {"pieces": [_piece("p2", "redo", note="x")]})
            self.assertEqual(os.stat(path).st_mtime_ns, first)
            campaign.sync_requests(root, {"pieces": [_piece("p2", "pending")]})
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])

    def test_wait_returns_batch_marked_while_waiting(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": [_piece("p1", "pending")]}, f)

            def mark():
                time.sleep(0.3)
                with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                    json.dump({"pieces": [_piece("p1", "redo", note="bigger logo")]}, f)

            threading.Thread(target=mark).start()
            batch = campaign.wait_batch(root, timeout=10, interval=0.1)
            self.assertEqual([b["id"] for b in batch], ["p1"])
            self.assertEqual(batch[0]["note"], "bigger logo")

    def test_wait_times_out_with_no_work(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                json.dump({"pieces": [_piece("p1", "approved")]}, f)
            self.assertEqual(campaign.wait_batch(root, timeout=0.3, interval=0.1), [])

    def test_deliver_returns_the_batch_when_locked(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as desktop:
            os.environ["KIT_DESKTOP_DIR"] = desktop
            try:
                with open(os.path.join(root, "campaign.json"), "w", encoding="utf-8") as f:
                    json.dump({"name": "demo", "brand": "acme"}, f)
                with open(os.path.join(root, "state.json"), "w", encoding="utf-8") as f:
                    json.dump({"pieces": [_piece("p1", "approved"),
                                          _piece("p2", "redo", note="x")]}, f)
                r = campaign.deliver(root)
                self.assertEqual(r["locked"], 1)
                self.assertEqual([b["id"] for b in r["batch"]], ["p2"])
                self.assertTrue(os.path.isfile(os.path.join(root, "requests.json")))
            finally:
                os.environ.pop("KIT_DESKTOP_DIR", None)


class CopyBatchTest(unittest.TestCase):
    def _write(self, root, rows):
        with open(os.path.join(root, "copy.json"), "w", encoding="utf-8") as f:
            json.dump({"concepts": ["clean"], "rows": rows}, f)

    def test_pending_batch_carries_program_and_note(self):
        batch = copy.pending_batch({"rows": [_row("k01", "approved"),
                                            _row("k02", "redo", note="too long"),
                                            _row("k03", "rejected", destination="ppc",
                                                 platform="google", kind="headline")]})
        self.assertEqual([b["id"] for b in batch], ["k02", "k03"])
        self.assertEqual(batch[0]["program"], "HCA")
        self.assertEqual(batch[0]["note"], "too long")
        self.assertEqual(batch[1]["platform"], "google")

    def test_decide_queues_the_row_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, [_row("k01", "pending"), _row("k02", "pending")])
            copy.decide(root, "k02", "redo", note="mention the January intake")
            with open(os.path.join(root, "requests.json"), encoding="utf-8") as f:
                batch = json.load(f)
            self.assertEqual([b["id"] for b in batch], ["k02"])
            self.assertEqual(batch[0]["note"], "mention the January intake")

    def test_wait_returns_the_row_then_empties_when_rewritten(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, [_row("k01", "pending")])

            def mark():
                time.sleep(0.3)
                copy.decide(root, "k01", "redo", note="shorter")

            threading.Thread(target=mark).start()
            batch = copy.wait_batch(root, timeout=10, interval=0.1)
            self.assertEqual([b["id"] for b in batch], ["k01"])

            rows = [_row("k01", "pending", text="Shorter.", note="")]
            self._write(root, rows)
            self.assertEqual(copy.sync_requests(root), [])

    def test_deliver_locked_while_a_row_is_marked(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as desktop:
            os.environ["KIT_DESKTOP_DIR"] = desktop
            try:
                self._write(root, [_row("k01", "approved"), _row("k02", "redo", note="x")])
                r = copy.deliver(root)
                self.assertEqual(r["locked"], 1)
                self.assertEqual([b["id"] for b in r["batch"]], ["k02"])
                self.assertEqual(r["exported"], 0)
            finally:
                os.environ.pop("KIT_DESKTOP_DIR", None)


if __name__ == "__main__":
    unittest.main()
