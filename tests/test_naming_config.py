"""Tests for axis-aware piece naming and null-safe config values."""

import types
import unittest

from kit import campaign, compliance, formats
from kit.providers.base import Provider, num


def _brand(naming):
    return types.SimpleNamespace(id="acme", naming=naming, locale_default="en")


def _campaign(naming):
    return {"slug": "launch", "naming": naming}


class NamingTest(unittest.TestCase):
    def test_axis_suffix_is_file_safe_and_sorted(self):
        self.assertEqual(campaign.axis_suffix({"locale": "en", "angle": "urgency!"}),
                         "angle-urgency_locale-en")
        self.assertEqual(campaign.axis_suffix({}), "")
        self.assertEqual(campaign.axis_suffix(None), "")

    def test_axes_field_separates_variations(self):
        brand, camp = _brand("{slug}_{concept}{axes}_{size}"), _campaign(None)
        names = {campaign.piece_name(brand, camp, c, "clean", "meta_feed_square")
                 for c in ({"angle": "a"}, {"angle": "b"})}
        self.assertEqual(len(names), 2)
        self.assertTrue(all("angle-" in n for n in names))

    def test_no_axes_keeps_the_legacy_name(self):
        brand = _brand("{slug}_{concept}{axes}_{size}")
        self.assertEqual(campaign.piece_name(brand, _campaign(None), {}, "clean",
                                             "meta_feed_square"),
                         "launch_clean_" + formats.label("meta_feed_square"))

    def test_unique_name_fixes_a_pattern_that_ignores_the_axes(self):
        brand, camp = _brand("{slug}_{concept}_{size}"), _campaign(None)
        used = set()
        first = campaign.unique_name(campaign.piece_name(brand, camp, {"angle": "a"},
                                                         "clean", "meta_feed_square"),
                                     {"angle": "a"}, used)
        second = campaign.unique_name(campaign.piece_name(brand, camp, {"angle": "b"},
                                                          "clean", "meta_feed_square"),
                                      {"angle": "b"}, used)
        self.assertNotEqual(first, second)
        self.assertIn("angle-b", second)

    def test_unique_name_counts_when_the_axes_already_appear(self):
        used = set()
        self.assertEqual(campaign.unique_name("same_angle-a", {"angle": "a"}, used),
                         "same_angle-a")
        self.assertEqual(campaign.unique_name("same_angle-a", {"angle": "a"}, used),
                         "same_angle-a_2")


class NullConfigTest(unittest.TestCase):
    def test_num_coerces_empty_and_invalid_values(self):
        for bad in (None, True, False, "", "abc"):
            self.assertEqual(num(bad), 0.0)
        self.assertEqual(num("3"), 3.0)
        self.assertEqual(num(None, 1.5), 1.5)

    def test_estimate_survives_an_empty_credits_field(self):
        p = Provider()
        p.credits_per_image = None
        p.credits_per_video = None
        est = p.estimate([{"id": "a", "kind": "image"}, {"id": "b", "kind": "video"}])
        self.assertEqual((est["images"], est["videos"], est["credits"]), (1, 1, 0.0))

    def test_rule_num_falls_back_when_the_field_is_null(self):
        self.assertEqual(compliance._num({"tolerance": None}, "tolerance", 0.02), 0.02)
        self.assertEqual(compliance._num({}, "ratio", 4.5), 4.5)
        self.assertEqual(compliance._num({"px": "12"}, "px", 0), 12)


if __name__ == "__main__":
    unittest.main()
