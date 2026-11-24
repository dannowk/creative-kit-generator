"""direction.md — the technical direction for the whole creation, in both kits."""

import os
import tempfile
import unittest

from kit import copy, intake, onboard


class DirectionTest(unittest.TestCase):
    def test_the_wizard_field_round_trips_into_the_inbox(self):
        with tempfile.TemporaryDirectory() as inbox:
            onboard.scaffold(inbox)
            self.assertEqual(onboard.read_direction(inbox), "")
            self.assertEqual(onboard.status(inbox)["direction"], "")
            onboard.save_direction(inbox, "story 9:16 · headline max 2 lines")
            self.assertEqual(onboard.status(inbox)["direction"], "story 9:16 · headline max 2 lines")

    def test_intake_treats_it_as_direction_not_as_a_briefing(self):
        with tempfile.TemporaryDirectory() as inbox:
            onboard.scaffold(inbox)
            onboard.save_direction(inbox, "logo never below 8% width")
            inv = intake.inventory(inbox)
            self.assertEqual(inv["direction"], os.path.join(inbox, onboard.DIRECTION_FILE))
            self.assertNotIn(inv["direction"], inv["briefs"])
            self.assertIn(os.path.join(inbox, "briefing.md"), inv["briefs"])

    def test_the_copy_kit_reads_the_same_field(self):
        with tempfile.TemporaryDirectory() as folder:
            copy.scaffold(folder)
            self.assertEqual(copy.read_text(folder, "direction.md"), "")
            with open(os.path.join(folder, "direction.md"), "w", encoding="utf-8") as f:
                f.write("5 headlines ≤30, never split the program name")
            self.assertEqual(copy.read_text(folder, "direction.md"),
                             "5 headlines ≤30, never split the program name")


if __name__ == "__main__":
    unittest.main()
