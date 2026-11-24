"""Tests for the rule-change alarm: propose -> user decides -> override merged on every load."""

import json
import os
import tempfile
import threading
import time
import unittest

from kit import campaign, compliance, rules


def _campaign(root, brand="acme"):
    with open(os.path.join(root, "campaign.json"), "w", encoding="utf-8") as f:
        json.dump({"brand": brand, "slug": "rules-demo", "cta": "Request Information"}, f)
    return root


def _rule(brand, check):
    return next(r for r in brand.compliance if r.get("check") == check)


def _trace(*texts):
    return {"elements": [{"op": "text", "text": t} for t in texts]}


_DISCLAIMER = {"check": "disclaimer_required", "text": "Median wage, Job Bank 2026",
               "when_text": "$28"}


class PathTest(unittest.TestCase):
    def test_get_and_set_nested_dict(self):
        data = {"copy": {"hero": {"disclaimer": ""}}}
        self.assertEqual(rules.get_path(data, "copy.hero.disclaimer"), "")
        rules.set_path(data, "copy.hero.disclaimer", "Median wage, Job Bank 2026")
        self.assertEqual(data["copy"]["hero"]["disclaimer"], "Median wage, Job Bank 2026")

    def test_get_missing_path_is_none(self):
        self.assertIsNone(rules.get_path({"copy": {}}, "copy.hero.disclaimer"))

    def test_set_matches_the_list_entry_by_key(self):
        data = {"compliance": [{"check": "contrast_min", "ratio": 3.0},
                               {"check": "disclaimer_required", "text": "Median wage"}]}
        rules.set_path(data, "compliance[check=contrast_min].ratio", 2.5)
        self.assertEqual(data["compliance"][0]["ratio"], 2.5)
        self.assertEqual(data["compliance"][1], {"check": "disclaimer_required", "text": "Median wage"})

    def test_set_creates_the_entry_and_the_field(self):
        data = {"compliance": [{"check": "nobreak", "text": ["CDI College"]}]}
        rules.set_path(data, "compliance[check=disclaimer_required].when_text", "$28")
        self.assertEqual(data["compliance"][-1],
                         {"check": "disclaimer_required", "when_text": "$28"})

    def test_malformed_target_raises(self):
        for bad in ("", "copy..hero", "copy.hero]", "1copy.x", "copy[=x]"):
            with self.assertRaises(KeyError):
                rules.get_path({"copy": {}}, bad)


class ProposalTest(unittest.TestCase):
    def test_add_records_the_current_value_and_dedupes(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "compliance[check=contrast_min].ratio", 2.5,
                          "the overlay only reaches 2.6:1 on this photo", notify=False)
            self.assertEqual(p["status"], "pending")
            self.assertEqual(p["scope"], "brand")
            self.assertEqual(p["current"], 3.0)
            again = rules.add(root, "compliance[check=contrast_min].ratio", 2.5, "same", notify=False)
            self.assertEqual(again["id"], p["id"])
            self.assertEqual(len(rules.pending(root)), 1)

    def test_agree_patches_the_brand_and_leaves_the_files_alone(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "compliance[check=contrast_min].ratio", 2.5, "r", notify=False)
            before = campaign.brand_for(campaign.load_campaign(root))
            self.assertEqual(_rule(before, "contrast_min")["ratio"], 3.0)
            rules.decide(root, p["id"], True)
            after = campaign.brand_for(campaign.load_campaign(root))
            self.assertEqual(_rule(after, "contrast_min")["ratio"], 2.5)
            self.assertEqual(_rule(before, "contrast_min")["ratio"], 3.0)
            with open(os.path.join(root, "rules", "overrides.yaml"), encoding="utf-8") as f:
                self.assertIn("contrast_min", f.read())
            with open(os.path.join(campaign.ROOT, "brands", "acme", "brand.yaml"),
                      encoding="utf-8") as f:
                self.assertIn("ratio: 3.0", f.read())

    def test_agree_adds_a_field_the_rule_did_not_have(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "compliance[check=contrast_min].when_text", "$28", "r", notify=False)
            self.assertIsNone(p["current"])
            rules.decide(root, p["id"], True)
            brand = campaign.brand_for(campaign.load_campaign(root))
            self.assertEqual(_rule(brand, "contrast_min")["when_text"], "$28")

    def test_keep_leaves_the_original_rule(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "compliance[check=contrast_min].ratio", 2.5, "r", notify=False)
            rules.decide(root, p["id"], False)
            brand = campaign.brand_for(campaign.load_campaign(root))
            self.assertEqual(_rule(brand, "contrast_min")["ratio"], 3.0)
            self.assertFalse(os.path.isfile(os.path.join(root, "rules", "overrides.yaml")))
            self.assertEqual(rules.load_proposals(root)[0]["status"], "kept")

    def test_a_decision_cannot_be_reopened(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "cta", "Apply now", "r", scope="campaign", notify=False)
            rules.decide(root, p["id"], True)
            self.assertIsNone(rules.decide(root, p["id"], False))
            self.assertIsNone(rules.decide(root, "r-nope", True))

    def test_campaign_scope_patches_the_briefing_copy_not_the_file(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "cta", "Apply now", "the client changed the CTA",
                          scope="campaign", notify=False)
            self.assertEqual(p["current"], "Request Information")
            rules.decide(root, p["id"], True)
            self.assertEqual(campaign.load_campaign(root)["cta"], "Apply now")
            with open(os.path.join(root, "campaign.json"), encoding="utf-8") as f:
                self.assertIn("Request Information", f.read())

    def test_take_decisions_reports_once(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "cta", "Apply now", "r", scope="campaign", notify=False)
            self.assertEqual(rules.take_decisions(root), [])
            rules.decide(root, p["id"], True)
            self.assertEqual([d["id"] for d in rules.take_decisions(root)], [p["id"]])
            self.assertEqual(rules.take_decisions(root), [])

    def test_wait_returns_the_decision(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "cta", "Apply now", "r", scope="campaign", notify=False)
            out = []
            t = threading.Thread(target=lambda: out.append(campaign.wait_batch(root, timeout=10)))
            t.start()
            time.sleep(0.3)
            rules.decide(root, p["id"], False)
            t.join(15)
            self.assertEqual(out[0][0]["stage"], "rules")
            self.assertEqual(out[0][0]["reason"], "kept")
            self.assertEqual(out[0][0]["target"], "cta")

    def test_payload_carries_pending_and_history(self):
        with tempfile.TemporaryDirectory() as root:
            _campaign(root)
            p = rules.add(root, "cta", "Apply now", "r", scope="campaign", notify=False)
            self.assertEqual(len(rules.payload(root)["pending"]), 1)
            rules.decide(root, p["id"], True)
            payload = rules.payload(root)
            self.assertEqual(payload["pending"], [])
            self.assertEqual(payload["patches"], 1)
            self.assertEqual(payload["decided"][-1]["status"], "agreed")


class DisclaimerTriggerTest(unittest.TestCase):
    def test_silent_when_the_trigger_text_is_absent(self):
        self.assertEqual(
            compliance.check_disclaimer_required(None, _trace("24 weeks to a healthcare career."),
                                                 _DISCLAIMER, None), [])

    def test_fails_when_the_trigger_is_there_and_the_disclaimer_is_not(self):
        out = compliance.check_disclaimer_required(
            None, _trace("In demand. $28/h median wage."), _DISCLAIMER, None)
        self.assertEqual([f["check"] for f in out], ["disclaimer_required"])
        self.assertEqual(out[0]["level"], "fail")

    def test_passes_when_both_are_there(self):
        self.assertEqual(
            compliance.check_disclaimer_required(
                None, _trace("$28/h", "Median wage, Job Bank 2026"), _DISCLAIMER, None), [])

    def test_without_a_trigger_the_rule_stays_unconditional(self):
        rule = {"check": "disclaimer_required", "text": "Median wage, Job Bank 2026"}
        out = compliance.check_disclaimer_required(None, _trace("24 weeks."), rule, None)
        self.assertEqual([f["check"] for f in out], ["disclaimer_required"])


if __name__ == "__main__":
    unittest.main()
