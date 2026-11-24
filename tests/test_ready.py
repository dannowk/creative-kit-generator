"""Handoff is manual: the legacy ready.json auto-signal (pre-2.14) is ignored and cleaned."""

import json
import os
import shutil
import tempfile
import unittest

from kit import campaign, copy


class LegacyReadySignal(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        with open(os.path.join(self.root, "ready.json"), "w") as f:
            json.dump({"at": "2026-01-01T00:00:00Z"}, f)

    def test_visual_wait_ignores_legacy_signal(self):
        self.assertEqual(campaign.wait_batch(self.root, timeout=1), [])
        self.assertTrue(os.path.isfile(os.path.join(self.root, "ready.json")))

    def test_copy_wait_ignores_legacy_signal(self):
        self.assertEqual(copy.wait_batch(self.root, timeout=1), [])

    def test_restart_removes_legacy_signal(self):
        campaign.restart(self.root)
        self.assertFalse(os.path.isfile(os.path.join(self.root, "ready.json")))
        with open(os.path.join(self.root, "ready.json"), "w") as f:
            f.write("{}")
        copy.restart(self.root)
        self.assertFalse(os.path.isfile(os.path.join(self.root, "ready.json")))


if __name__ == "__main__":
    unittest.main()