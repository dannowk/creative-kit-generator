"""assets_by_concept: a concept's own asset map wins over the shared photo."""

import os
import tempfile
import unittest

from PIL import Image

from kit import campaign


def _png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (40, 40), (200, 30, 30)).save(path)


class AssetsByConcept(unittest.TestCase):
    def test_concept_override_wins_and_others_keep_shared(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "templates"))
            for c in ("a", "b"):
                with open(os.path.join(root, "templates", f"{c}.yaml"), "w", encoding="utf-8") as f:
                    f.write("layers:\n- op: paper\n")
            _png(os.path.join(root, "assets", "shared.png"))
            _png(os.path.join(root, "assets", "own.png"))
            camp = {"_root": root, "brand": "acme", "slug": "t",
                    "channels": [], "formats": ["meta_feed_square"],
                    "concepts": ["a", "b"], "axes": {},
                    "copy": {"default": {"hook": "Test hook"}},
                    "assets": {"default": "assets/shared.png"},
                    "assets_by_concept": {"b": {"default": "assets/own.png"}}}
            state = campaign.run(camp, dry=True)
            by = {p["concept"]: p["asset"] for p in state["pieces"]}
            self.assertEqual(by, {"a": "shared.png", "b": "own.png"})

    def test_without_override_every_concept_keeps_shared(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "templates"))
            with open(os.path.join(root, "templates", "a.yaml"), "w", encoding="utf-8") as f:
                f.write("layers:\n- op: paper\n")
            _png(os.path.join(root, "assets", "shared.png"))
            camp = {"_root": root, "brand": "acme", "slug": "t",
                    "channels": [], "formats": ["meta_feed_square"],
                    "concepts": ["a"], "axes": {},
                    "copy": {"default": {"hook": "Test hook"}},
                    "assets": {"default": "assets/shared.png"}}
            state = campaign.run(camp, dry=True)
            self.assertEqual([p["asset"] for p in state["pieces"]], ["shared.png"])


if __name__ == "__main__":
    unittest.main()