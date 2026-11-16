"""Testes do módulo copy (skill independente de copy)."""

import json
import os
import tempfile
import unittest

from kit import copy


def _row(**kw):
    r = {"id": "k01", "destination": "overlay", "concept": "clean", "axis": "default",
         "kind": "hook", "text": "Sua semana, planejada em minutos.", "lang": "pt",
         "status": "pending", "note": "", "origin": "agent",
         "updated_at": "2026-11-15T00:00:00Z", "updated_by": "agent"}
    r.update(kw)
    return r


def _data(rows=None, concepts=None):
    return {"concepts": concepts if concepts is not None else ["clean"],
            "rows": rows if rows is not None else [_row()]}


class ValidateTest(unittest.TestCase):
    def test_good_rows_no_errors(self):
        self.assertEqual(copy.validate(_data()), [])

    def test_ppc_kinds_ok(self):
        rows = [_row(id="k01", destination="ppc", kind="headline", text="Headline curta"),
                _row(id="k02", destination="ppc", kind="description", text="Descrição da oferta"),
                _row(id="k03", destination="ppc", kind="primary_text", text="Texto principal")]
        self.assertEqual(copy.validate(_data(rows)), [])

    def test_bad_destination(self):
        errs = copy.validate(_data([_row(destination="video")]))
        self.assertTrue(any("destination" in e for e in errs))

    def test_kind_must_match_destination(self):
        errs = copy.validate(_data([_row(destination="ppc", kind="hook")]))
        self.assertTrue(any("kind" in e for e in errs))
        errs = copy.validate(_data([_row(destination="overlay", kind="headline")]))
        self.assertTrue(any("kind" in e for e in errs))

    def test_empty_text(self):
        errs = copy.validate(_data([_row(text="   ")]))
        self.assertTrue(any("text" in e for e in errs))

    def test_duplicate_id(self):
        errs = copy.validate(_data([_row(id="k01"), _row(id="k01", kind="cta", text="Saiba mais")]))
        self.assertTrue(any("id" in e and "repetid" in e for e in errs))

    def test_undeclared_concept(self):
        errs = copy.validate(_data([_row(concept="cinema")], concepts=["clean"]))
        self.assertTrue(any("conceito" in e for e in errs))

    def test_bad_status_lang_origin(self):
        errs = copy.validate(_data([_row(status="ok", lang="fr", origin="bot")]))
        self.assertTrue(any("status" in e for e in errs))
        self.assertTrue(any("lang" in e for e in errs))
        self.assertTrue(any("origin" in e for e in errs))


class DecideTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        copy.save(self.root, _data([_row(id="k01"), _row(id="k02", kind="cta", text="Saiba mais")]))

    def tearDown(self):
        self.tmp.cleanup()

    def test_approve_marks_and_stamps(self):
        ok = copy.decide(self.root, "k01", "approved", who="Dann")
        self.assertTrue(ok)
        rows = copy.load(self.root)["rows"]
        r = next(r for r in rows if r["id"] == "k01")
        self.assertEqual(r["status"], "approved")
        self.assertEqual(r["updated_by"], "Dann")
        self.assertTrue(r["updated_at"])
        self.assertNotEqual(r["updated_at"], "2026-11-15T00:00:00Z")

    def test_unknown_id_false(self):
        self.assertFalse(copy.decide(self.root, "k99", "approved"))

    def test_redo_requires_note(self):
        with self.assertRaises(ValueError):
            copy.decide(self.root, "k01", "redo", note="")
        ok = copy.decide(self.root, "k01", "redo", note="mais curto", who="Dann")
        self.assertTrue(ok)
        r = next(r for r in copy.load(self.root)["rows"] if r["id"] == "k01")
        self.assertEqual(r["status"], "redo")
        self.assertEqual(r["note"], "mais curto")

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            copy.decide(self.root, "k01", "bogus")

    def test_approve_clears_note(self):
        copy.decide(self.root, "k01", "redo", note="ajuste")
        copy.decide(self.root, "k01", "approved")
        r = next(r for r in copy.load(self.root)["rows"] if r["id"] == "k01")
        self.assertEqual(r.get("note", ""), "")


class PayloadTest(unittest.TestCase):
    def test_counts_and_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(copy.review_payload(root))
            copy.save(root, _data([_row(id="k01", status="approved"),
                                   _row(id="k02", kind="cta", text="Saiba mais", status="pending"),
                                   _row(id="k03", kind="kicker", text="NOVO", status="rejected")]))
            p = copy.review_payload(root)
            self.assertEqual(p["counts"]["approved"], 1)
            self.assertEqual(p["counts"]["pending"], 1)
            self.assertEqual(p["counts"]["rejected"], 1)
            self.assertEqual(len(p["rows"]), 3)


class IdTest(unittest.TestCase):
    def test_next_id_sequential_skips_used(self):
        self.assertEqual(copy.next_id([]), "k01")
        self.assertEqual(copy.next_id([_row(id="k01")]), "k02")
        self.assertEqual(copy.next_id([_row(id="k01"), _row(id="k03")]), "k02")
        self.assertEqual(copy.next_id([_row(id="k01"), _row(id="k02")]), "k03")


if __name__ == "__main__":
    unittest.main()