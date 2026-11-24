"""Restart clears working output and queues, keeps briefing/uploads/paid assets."""

import json
import os
import shutil
import tempfile
import unittest

from kit import campaign, copy


def _put(root, rel, data=b"x"):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def _json(root, rel, obj):
    _put(root, rel, json.dumps(obj).encode())


class VisualRestart(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_clears_work_keeps_inputs_and_assets(self):
        _json(self.root, "state.json", {"campaign": "acme", "pieces": [
            {"id": "k001", "concept": "c", "status": "approved"},
            {"id": "k002", "concept": "c", "status": "redo", "queued": True}]})
        _json(self.root, "requests.json", [{"id": "k002"}])
        _put(self.root, "out/k001.png")
        _put(self.root, "review/thumbs/c/k001.png")
        _put(self.root, "styles/c.yaml", b"note: tweak")
        _put(self.root, "styles/c/refs/ref.png")
        _json(self.root, "assets/manifest.json", [{"path": "assets/img.png", "sha": "a"}])
        _json(self.root, "assets/state.json", {"assets/img.png": {"status": "approved"}})
        _json(self.root, "assets/requests.json", [{"id": "assets/img.png"}])
        _put(self.root, "assets/img.png")
        _put(self.root, "briefing.md", b"# brief")
        _json(self.root, "campaign.json", {"slug": "acme"})

        campaign.restart(self.root)

        for gone in ("out", "review", "styles", "requests.json",
                     "assets/state.json", "assets/requests.json"):
            self.assertFalse(os.path.exists(os.path.join(self.root, gone)), gone)
        for kept in ("assets/img.png", "assets/manifest.json", "briefing.md", "campaign.json"):
            self.assertTrue(os.path.isfile(os.path.join(self.root, kept)), kept)
        with open(os.path.join(self.root, "state.json"), encoding="utf-8") as f:
            state = json.load(f)
        self.assertEqual(state["pieces"], [])
        self.assertEqual(state["campaign"], "acme")
        self.assertEqual(campaign.sync_requests(self.root, state), [])

    def test_empty_folder_is_safe(self):
        campaign.restart(self.root)
        self.assertFalse(os.path.exists(os.path.join(self.root, "state.json")))


class CopyRestart(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_clears_table_keeps_briefing(self):
        _json(self.root, "copy.json", {"rows": [{"id": "r1", "status": "redo"}]})
        _json(self.root, "requests.json", [{"id": "r1"}])
        _put(self.root, "styles/c.yaml", b"note: tweak")
        _put(self.root, "styles/c/refs/ref.png")
        _put(self.root, "briefing.md", b"# brief")
        _put(self.root, "examples.txt", b"example")
        _put(self.root, "direction.md", b"limits")

        copy.restart(self.root)

        for gone in ("copy.json", "requests.json", "styles"):
            self.assertFalse(os.path.exists(os.path.join(self.root, gone)), gone)
        for kept in ("briefing.md", "examples.txt", "direction.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.root, kept)), kept)
        self.assertEqual(copy.sync_requests(self.root), [])

    def test_empty_folder_is_safe(self):
        copy.restart(self.root)
        self.assertFalse(os.path.exists(os.path.join(self.root, "copy.json")))


if __name__ == "__main__":
    unittest.main()