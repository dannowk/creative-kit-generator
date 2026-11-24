"""Tests for the PPC sheets: platform limits are enforced and reported, never silent."""

import unittest

from kit import ppc


class _Brand:
    name = "Acme"
    logo_path = "/tmp/brand/assets/logo.png"


CAMP = {"slug": "launch", "cta": "Book a demo",
        "copy": {"Agenda": {"program": "Acme Agenda",
                            "kicker": "Acme Agenda for multi-site clinics with rotating staff",
                            "clean": {"hook": "Scheduling that finally keeps up with the clinic"}}}}


def _piece(pid, fmt, concept="clean", axes=None):
    return {"id": pid, "concept": concept, "format": fmt, "path": f"{concept}/{pid}.png",
            "axes": axes if axes is not None else {"product": "Agenda"},
            "status": "approved", "kind": "image"}


class TruncTest(unittest.TestCase):
    def test_cuts_at_the_limit_on_a_word_boundary(self):
        self.assertEqual(ppc._trunc("Your front desk, finally quiet.", 30), "Your front desk, finally")
        self.assertEqual(ppc._trunc("supercalifragilistic", 10), "supercalif")

    def test_short_copy_is_untouched_and_silent(self):
        warnings = []
        self.assertEqual(ppc._trunc("Book a demo", 30, warnings, "clean | Agenda", "Headline"),
                         "Book a demo")
        self.assertEqual(warnings, [])

    def test_a_cut_is_reported_with_the_field_and_the_sizes(self):
        warnings = []
        out = ppc._trunc("Scheduling that finally keeps up with the clinic", 30,
                         warnings, "clean | Agenda", "Headline")
        self.assertLessEqual(len(out), 30)
        self.assertEqual(warnings, [{"id": "clean | Agenda", "field": "Headline",
                                     "chars": 48, "limit": 30}])


class RowTest(unittest.TestCase):
    def test_rsa_headlines_and_descriptions_stay_inside_the_limits(self):
        rows = ppc._rsa_rows([_piece("p1", "google_display_sq")], CAMP, _Brand())
        row = rows[0]
        heads = [v for k, v in row.items() if k.startswith("Headline") and v]
        descs = [v for k, v in row.items() if k.startswith("Description") and v]
        self.assertTrue(heads)
        self.assertTrue(descs)
        self.assertTrue(all(len(h) <= 30 for h in heads), heads)
        self.assertTrue(all(len(d) <= 90 for d in descs), descs)
        self.assertEqual(row["Status"], "Paused")
        self.assertEqual(row["Ad group"], "clean | Agenda")

    def test_the_same_cut_across_pieces_is_reported_once_per_ad_group(self):
        warnings = []
        pieces = [_piece(f"p{i}", "meta_feed_square") for i in range(3)]
        ppc._meta_rows(pieces, CAMP, _Brand(), warnings)
        keys = {(w["id"], w["field"]) for w in warnings}
        self.assertEqual(keys, {("clean | Agenda", "Link Description")})
        self.assertEqual(len(warnings), 1)

    def test_display_rows_report_their_own_cuts(self):
        camp = {"slug": "launch", "cta": "Book a demo",
                "copy": {"Agenda": {"program": "Acme Agenda for multi-site clinics",
                                    "clean": {"hook": "Scheduling that keeps up"}}}}
        warnings = []
        rows = ppc._display_rows([_piece("p1", "google_display_land")], camp, _Brand(), warnings)
        self.assertEqual(rows[0]["Headline"], "Acme Agenda for multi-site")
        self.assertEqual(warnings, [{"id": "clean | Agenda", "field": "Headline",
                                     "chars": 34, "limit": 30}])


if __name__ == "__main__":
    unittest.main()
