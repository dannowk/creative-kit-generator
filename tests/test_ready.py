"""Next step button: ready.json signal, consumed once by the agent's wait loop."""

import json
import os
import shutil
import tempfile
import unittest

from kit import campaign, copy, onboard


class ReadySignal(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_press_pending_take_consumes_once(self):
        self.assertFalse(onboard.ready_pending(self.root))
        self.assertEqual(onboard.take_ready(self.root), {})
        rec = onboard.press_ready(self.root)
        self.assertIn("at", rec)
        self.assertTrue(onboard.ready_pending(self.root))
        self.assertEqual(onboard.take_ready(self.root), rec)
        self.assertFalse(onboard.ready_pending(self.root))
        self.assertEqual(onboard.take_ready(self.root), {})

    def test_corrupt_record_is_consumed_not_fatal(self):
        with open(os.path.join(self.root, "ready.json"), "w") as f:
            f.write("{broken")
        self.assertTrue(onboard.ready_pending(self.root))
        self.assertEqual(onboard.take_ready(self.root), {})
        self.assertFalse(onboard.ready_pending(self.root))

    def test_visual_wait_returns_ready_stage(self):
        onboard.press_ready(self.root)
        batch = campaign.wait_batch(self.root, timeout=5)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["stage"], "ready")
        self.assertEqual(batch[0]["reason"], "next")
        self.assertFalse(onboard.ready_pending(self.root))

    def test_copy_wait_returns_ready_stage(self):
        onboard.press_ready(self.root)
        batch = copy.wait_batch(self.root, timeout=5)
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]["stage"], "ready")
        self.assertFalse(onboard.ready_pending(self.root))

    def test_restart_clears_pending_signal(self):
        onboard.press_ready(self.root)
        campaign.restart(self.root)
        self.assertFalse(onboard.ready_pending(self.root))
        onboard.press_ready(self.root)
        copy.restart(self.root)
        self.assertFalse(onboard.ready_pending(self.root))


if __name__ == "__main__":
    unittest.main()