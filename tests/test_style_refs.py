import os
import shutil
import tempfile
import unittest

from kit import campaign


class StyleRefsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ck-refs-")
        os.makedirs(os.path.join(self.root, "styles"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_saves_sanitized_and_lists_in_yaml(self):
        saved = campaign.add_ref(self.root, "in-demand", "mood board.png", b"png")
        self.assertEqual(saved, "mood-board.png")
        self.assertTrue(os.path.isfile(
            os.path.join(self.root, "styles", "in-demand", "refs", saved)))
        self.assertEqual(campaign.load_style(self.root, "in-demand")["refs"], ["mood-board.png"])

    def test_duplicate_gets_a_suffix(self):
        campaign.add_ref(self.root, "c", "a.pdf", b"1")
        self.assertEqual(campaign.add_ref(self.root, "c", "a.pdf", b"2"), "a-1.pdf")
        self.assertEqual(campaign.list_refs(self.root, "c"), ["a-1.pdf", "a.pdf"])

    def test_rejects_other_types_and_oversize(self):
        with self.assertRaises(ValueError):
            campaign.add_ref(self.root, "c", "virus.exe", b"x")
        with self.assertRaises(ValueError):
            campaign.add_ref(self.root, "c", "big.png", b"x" * (campaign.MAX_REF + 1))
        self.assertEqual(campaign.load_style(self.root, "c"), {})

    def test_drop_removes_file_and_yaml_key(self):
        campaign.add_ref(self.root, "c", "a.png", b"1")
        self.assertTrue(campaign.drop_ref(self.root, "c", "a.png"))
        self.assertFalse(campaign.drop_ref(self.root, "c", "a.png"))
        self.assertNotIn("refs", campaign.load_style(self.root, "c"))
        self.assertEqual(campaign.list_refs(self.root, "c"), [])

    def test_path_traversal_is_stripped(self):
        saved = campaign.add_ref(self.root, "c", "../../evil.png", b"1")
        self.assertEqual(saved, "evil.png")
        self.assertTrue(os.path.isfile(
            os.path.join(campaign.refs_dir(self.root, "c"), saved)))


if __name__ == "__main__":
    unittest.main()
