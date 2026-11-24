"""Adjust style applied to ticked pieces only: per-piece overrides in styles/<concept>.yaml."""

import os
import tempfile
import unittest

from kit import campaign
from kit.brand import Brand


class MergeStyle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_concept_wide(self):
        st = campaign.merge_style(self.root, "clean", {"primary": "#112233"}, {}, "warmer")
        self.assertEqual(st["palette"], {"primary": "#112233"})
        self.assertEqual(st["note"], "warmer")
        self.assertEqual(campaign.load_style(self.root, "clean"), st)

    def test_piece_overrides_and_precedence(self):
        campaign.merge_style(self.root, "clean", {"primary": "#111111"}, {}, "all")
        st = campaign.merge_style(self.root, "clean", {"primary": "#222222"}, {}, "only this",
                                ids=["clean-feed-1"])
        self.assertEqual(st["palette"], {"primary": "#111111"})
        self.assertEqual(campaign.piece_style(st, "clean-feed-1"),
                         {"palette": {"primary": "#222222"}, "note": "only this"})
        self.assertEqual(campaign.piece_style(st, "clean-feed-2"), {})
        brand = Brand({"palette": {"primary": "#000000"}, "type": {}}, self.root)
        cb = campaign.styled_brand(brand, st)
        pb = campaign.styled_brand(cb, campaign.piece_style(st, "clean-feed-1"))
        self.assertEqual(cb.palette["primary"], (0x11, 0x11, 0x11))
        self.assertEqual(pb.palette["primary"], (0x22, 0x22, 0x22))

    def test_concept_wide_clears_piece_overrides(self):
        campaign.merge_style(self.root, "clean", {}, {}, "x", ids=["a", "b"])
        st = campaign.merge_style(self.root, "clean", {"accent": "#334455"}, {}, "")
        self.assertNotIn("pieces", st)
        self.assertNotIn("note", st)

    def test_empty_piece_apply_removes_override(self):
        campaign.merge_style(self.root, "clean", {}, {}, "x", ids=["a"])
        st = campaign.merge_style(self.root, "clean", {}, {}, "", ids=["a"])
        self.assertNotIn("pieces", st)

    def test_refs_preserved(self):
        campaign.add_ref(self.root, "clean", "look.png", b"\x89PNG fake")
        st = campaign.merge_style(self.root, "clean", {}, {}, "note", ids=["a"])
        self.assertEqual(st["refs"], ["look.png"])
        self.assertTrue(os.path.isfile(os.path.join(campaign.refs_dir(self.root, "clean"), "look.png")))


class Relocate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.inbox = os.path.join(self.base, "my-campaign")
        os.makedirs(os.path.join(self.inbox, "logo"))
        with open(os.path.join(self.inbox, "briefing.md"), "w") as f:
            f.write("hello")

    def tearDown(self):
        self.tmp.cleanup()

    def test_moves_content(self):
        from kit import onboard
        new = onboard.relocate(self.inbox, self.base, "acme launch")
        self.assertEqual(new, os.path.join(self.base, "acme launch"))
        self.assertTrue(os.path.isfile(os.path.join(new, "briefing.md")))
        self.assertTrue(os.path.isdir(os.path.join(new, "logo")))
        self.assertFalse(os.path.exists(self.inbox))

    def test_same_path_noop(self):
        from kit import onboard
        self.assertEqual(onboard.relocate(self.inbox, self.base, "my-campaign"), self.inbox)

    def test_bad_name(self):
        from kit import onboard
        for name in ("", "../evil", "a/b", ".hidden"):
            with self.assertRaises(ValueError) as c:
                onboard.relocate(self.inbox, self.base, name)
            self.assertEqual(str(c.exception), "name")

    def test_missing_parent(self):
        from kit import onboard
        with self.assertRaises(ValueError) as c:
            onboard.relocate(self.inbox, os.path.join(self.base, "nope"), "x")
        self.assertEqual(str(c.exception), "parent")

    def test_inside_itself(self):
        from kit import onboard
        with self.assertRaises(ValueError) as c:
            onboard.relocate(self.inbox, os.path.join(self.inbox, "logo"), "x")
        self.assertEqual(str(c.exception), "inside")

    def test_existing_target(self):
        from kit import onboard
        os.makedirs(os.path.join(self.base, "taken"))
        with self.assertRaises(ValueError) as c:
            onboard.relocate(self.inbox, self.base, "taken")
        self.assertEqual(str(c.exception), "exists")
        self.assertTrue(os.path.isfile(os.path.join(self.inbox, "briefing.md")))


if __name__ == "__main__":
    unittest.main()