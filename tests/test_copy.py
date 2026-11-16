"""Tests for the copy module (standalone copy skill)."""

import json
import os
import tempfile
import unittest

from kit import copy


def _row(**kw):
    r = {"id": "k01", "destination": "overlay", "concept": "clean", "axis": "default",
         "kind": "hook", "text": "Your week, planned in minutes.", "lang": "en",
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
        rows = [_row(id="k01", destination="ppc", kind="headline", text="Short headline"),
                _row(id="k02", destination="ppc", kind="description", text="Offer description"),
                _row(id="k03", destination="ppc", kind="primary_text", text="Primary text")]
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
        errs = copy.validate(_data([_row(id="k01"), _row(id="k01", kind="cta", text="Learn more")]))
        self.assertTrue(any("id" in e and "duplicate" in e for e in errs))

    def test_undeclared_concept(self):
        errs = copy.validate(_data([_row(concept="cinema")], concepts=["clean"]))
        self.assertTrue(any("concept" in e for e in errs))

    def test_bad_status_lang_origin(self):
        errs = copy.validate(_data([_row(status="ok", lang="fr", origin="bot")]))
        self.assertTrue(any("status" in e for e in errs))
        self.assertTrue(any("lang" in e for e in errs))
        self.assertTrue(any("origin" in e for e in errs))


class DecideTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        copy.save(self.root, _data([_row(id="k01"), _row(id="k02", kind="cta", text="Learn more")]))

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
        ok = copy.decide(self.root, "k01", "redo", note="shorter", who="Dann")
        self.assertTrue(ok)
        r = next(r for r in copy.load(self.root)["rows"] if r["id"] == "k01")
        self.assertEqual(r["status"], "redo")
        self.assertEqual(r["note"], "shorter")

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            copy.decide(self.root, "k01", "bogus")

    def test_approve_clears_note(self):
        copy.decide(self.root, "k01", "redo", note="adjust")
        copy.decide(self.root, "k01", "approved")
        r = next(r for r in copy.load(self.root)["rows"] if r["id"] == "k01")
        self.assertEqual(r.get("note", ""), "")


class PayloadTest(unittest.TestCase):
    def test_counts_and_none(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertIsNone(copy.review_payload(root))
            copy.save(root, _data([_row(id="k01", status="approved"),
                                   _row(id="k02", kind="cta", text="Learn more", status="pending"),
                                   _row(id="k03", kind="kicker", text="NEW", status="rejected")]))
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


class ScaffoldTest(unittest.TestCase):
    def test_creates_briefing_and_examples(self):
        with tempfile.TemporaryDirectory() as folder:
            brief = copy.scaffold(folder)
            self.assertTrue(os.path.isfile(brief))
            self.assertTrue(os.path.isfile(os.path.join(folder, "examples.txt")))
            self.assertIn("Copy briefing", copy.read_text(folder, "briefing.md"))
            self.assertFalse(os.path.exists(os.path.join(folder, "logo")))

    def test_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            copy.scaffold(folder)
            with open(os.path.join(folder, "briefing.md"), "w", encoding="utf-8") as f:
                f.write("my briefing")
            copy.scaffold(folder)
            self.assertEqual(copy.read_text(folder, "briefing.md"), "my briefing")


class ProgressTest(unittest.TestCase):
    def test_fresh_template_not_filled(self):
        from kit import copy_ui
        filled, total = copy_ui._brief_progress(copy.BRIEF_TEMPLATE)
        self.assertEqual(filled, 0)
        self.assertEqual(total, 9)

    def test_filled_section_counts(self):
        from kit import copy_ui
        text = "# Briefing\n\n## 1. Objective\nGenerate leads.\n\n## 2. Audience\n(who)\n"
        self.assertEqual(copy_ui._brief_progress(text), (1, 2))

    def test_paren_placeholder_not_filled(self):
        from kit import copy_ui
        self.assertEqual(copy_ui._brief_progress("## 1. Objective\n(what you want)\n")[0], 0)


class AttachTest(unittest.TestCase):
    def test_save_list_remove_and_collision(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(copy.attachments(root), [])
            name = copy.save_attachment(root, "ready-copy.md", b"# hooks\nLess phone tag.")
            self.assertEqual(name, "ready-copy.md")
            name2 = copy.save_attachment(root, "ready-copy.md", b"second version")
            self.assertEqual(name2, "ready-copy (2).md")
            atts = copy.attachments(root)
            self.assertEqual([a["name"] for a in atts], ["ready-copy (2).md", "ready-copy.md"])
            self.assertEqual(atts[1]["size"], len(b"# hooks\nLess phone tag."))
            self.assertTrue(copy.remove_attachment(root, "ready-copy.md"))
            self.assertFalse(copy.remove_attachment(root, "ready-copy.md"))
            self.assertEqual([a["name"] for a in copy.attachments(root)], ["ready-copy (2).md"])

    def test_name_is_sanitized(self):
        with tempfile.TemporaryDirectory() as root:
            name = copy.save_attachment(root, "../../etc/passwd", b"x")
            self.assertEqual(name, "passwd")
            self.assertTrue(os.path.isfile(os.path.join(root, "attachments", "passwd")))

    def test_plan_lists_attachments(self):
        with tempfile.TemporaryDirectory() as root:
            copy.scaffold(root)
            copy.save_attachment(root, "brief.docx", b"\x00binary")
            with os.popen(f"python3 -m kit.cli copy plan {root!r}") as p:
                out = p.read()
            self.assertIn("attached files", out)
            self.assertIn("brief.docx", out)


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.desktop = tempfile.TemporaryDirectory()
        os.environ["KIT_DESKTOP_DIR"] = self.desktop.name
        self.folder = os.path.join(self.tmp.name, "my-campaign-copy")
        os.makedirs(self.folder)

    def tearDown(self):
        os.environ.pop("KIT_DESKTOP_DIR", None)
        self.tmp.cleanup()
        self.desktop.cleanup()

    def _write(self, rows):
        copy.save(self.folder, {"concepts": ["clean"], "rows": rows})

    def test_approved_only_and_files(self):
        import csv
        self._write([
            _row(id="k01", destination="ppc", kind="headline", text="Enroll today", status="approved"),
            _row(id="k02", destination="ppc", kind="description", text="Limited seats.", status="approved"),
            _row(id="k03", destination="ppc", kind="primary_text", text="Study design from scratch.", status="approved"),
            _row(id="k04", destination="overlay", kind="hook", text="Last seats", status="approved"),
            _row(id="k05", destination="overlay", kind="cta", text="Enroll", status="approved"),
            _row(id="k06", destination="ppc", kind="headline", text="Not approved", status="pending"),
        ])
        s = copy.export(self.folder)
        self.assertEqual((s["meta"], s["google_rsa"], s["overlay"], s["manifest"]), (1, 1, 1, 5))
        self.assertIn("meta_bulk_import.csv", s["files"])
        self.assertTrue(os.path.isfile(os.path.join(s["dir"], "meta_bulk_import.csv")))
        self.assertTrue(os.path.isfile(os.path.join(s["dir"], "overlay.csv")))
        with open(os.path.join(s["dir"], "copy_manifest.csv"), encoding="utf-8-sig") as f:
            ids = [r["ID"] for r in csv.DictReader(f)]
        self.assertIn("k01", ids)
        self.assertNotIn("k06", ids)

    def test_rsa_limit_warning(self):
        self._write([_row(id="k01", destination="ppc", kind="headline", text="x" * 40, status="approved")])
        s = copy.export(self.folder)
        self.assertEqual(len(s["warnings"]), 1)
        self.assertEqual(s["warnings"][0]["id"], "k01")
        self.assertEqual(s["warnings"][0]["limit"], 30)

    def test_deliver_counts_approved(self):
        self._write([_row(id="k01", destination="overlay", kind="hook", text="Hi", status="approved")])
        self.assertEqual(copy.deliver(self.folder)["exported"], 1)

    def test_deliver_empty_when_none_approved(self):
        self._write([_row(id="k01", status="pending")])
        s = copy.deliver(self.folder)
        self.assertEqual(s["exported"], 0)
        self.assertEqual(s["files"], [])


if __name__ == "__main__":
    unittest.main()