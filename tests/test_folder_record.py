"""The folder card's saved state lives inside the folder, shared by both kits."""

import json
import os
import tempfile
import unittest

from kit import onboard


class FolderRecord(unittest.TestCase):
    def test_missing_record_is_empty(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(onboard.folder_record(root), {})
            self.assertFalse(onboard.status(root)["folder_saved"])

    def test_save_roundtrip_and_status_flag(self):
        with tempfile.TemporaryDirectory() as parent:
            root = os.path.join(parent, "my-copy")
            os.makedirs(root)
            rec = onboard.save_folder_record(root)
            self.assertEqual(rec["name"], "my-copy")
            self.assertEqual(rec["parent"], parent)
            self.assertTrue(rec["saved_at"])
            self.assertEqual(onboard.folder_record(root), rec)
            self.assertTrue(onboard.status(root)["folder_saved"])

    def test_corrupt_record_degrades_to_empty(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, onboard.FOLDER_RECORD), "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(onboard.folder_record(root), {})

    def test_record_moves_with_the_folder(self):
        with tempfile.TemporaryDirectory() as parent:
            root = os.path.join(parent, "before")
            os.makedirs(root)
            onboard.save_folder_record(root)
            new = onboard.relocate(root, parent, "after")
            self.assertEqual(onboard.folder_record(new)["name"], "after")
            self.assertFalse(os.path.exists(os.path.join(root, onboard.FOLDER_RECORD)))


if __name__ == "__main__":
    unittest.main()