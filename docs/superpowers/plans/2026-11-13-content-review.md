# Content Review Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user approve / reject / redo AI-suggested copy in the browser review page (mirroring image-piece review), and let the content team approve the same copy via an exported spreadsheet they fill and return.

**Architecture:** `content.json` becomes the proposal store with per-row `id/origin/status/note`. Ingest stamps sheet rows approved; the agent's added/changed rows are pending. A new Copy panel in the existing review page marks decisions (never executes); **Apply approved copy** is the single gate that merges only approved rows into `campaign.json.copy` (render/PPC untouched). A spreadsheet round-trip (`export` → team fills `decision`/`note` → `import`) writes the same status fields. Normalize pattern throughout: kit prepares + validates, agent/user acts, kit applies.

**Tech Stack:** Python 3.12 (stdlib `unittest`, `csv`, `json`, `tempfile`), `openpyxl` (read-only workbooks MUST `wb.close()` on Windows), existing `kit/ui.py` `ThreadingHTTPServer` + injected JS, `kit/i18n.py` PT-source/EN-overlay catalog.

**Spec:** `docs/superpowers/specs/2026-11-13-content-review-design.md` (approved).

**Conventions (read before starting):**
- Run tests from repo root with `.venv/Scripts/python.exe` (Windows). Single module: `.venv/Scripts/python.exe -m unittest tests.test_content_review -v`. Full suite: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
- Git identity is NOT configured. NEVER edit git config. Commit with:
  `git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "..."`
- `git push` is slow (>2 min) — run it in the background or with a long timeout.
- i18n: PT is source, EN is overlay. `i18n.t` raises `KeyError` on a missing key, so every referenced key must exist in BOTH `_PT` and `_EN`. HTML strings use `rv.copy.*`; injected-JS strings use `rv.js.copy.*` (the `rv.js.` prefix is stripped into `T`).
- Tests that call `export_review`/`/copy-export` MUST mock `kit.campaign.delivery_dir` to a temp dir so nothing lands on the real Desktop.
- Do not invent copy, URLs, or IDs. Kit never talks to SharePoint.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `kit/content.py` | proposal store: stamp, validate, apply-approved-only, decide, review payload, export/import | Modify (Tasks 1–5) |
| `kit/cli.py` | `content --export` / `content --import PATH` | Modify (Task 6) |
| `kit/ui.py` | `/state` fallback + content; `/copy-decision`, `/copy-apply`, `/copy-export`, `/copy-import`; Copy panel HTML+JS | Modify (Tasks 7–8) |
| `kit/i18n.py` | `rv.copy.*` + `rv.js.copy.*` PT/EN | Modify (Tasks 7–8) |
| `tests/test_content_review.py` | new review tests | Create (Tasks 1–8) |
| `tests/test_content.py` | update for stamped rows | Modify (Task 1) |
| `AGENTS.md`, `skills/campaign-kit/SKILL.md` | review contract + round-trip | Modify (Task 9) |

---

### Task 1: Data model — ingest stamping + status/origin validation

**Files:**
- Modify: `kit/content.py` (constants, `_stamp`, `validate`, `ingest`)
- Create: `tests/test_content_review.py`
- Modify: `tests/test_content.py` (stamped-row expectations)

- [ ] **Step 1: Write the failing tests** — create `tests/test_content_review.py`:

```python
import json
import os
import tempfile
import unittest

from kit import content


class StampAndValidate(unittest.TestCase):
    def _sheet(self, d, text="concept,hook\nclean,Hi\n"):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_ingest_stamps_ids_origin_status(self):
        with tempfile.TemporaryDirectory() as d:
            self._sheet(d, "concept,hook\nclean,One\nclean,Two\n")
            content.ingest({"_root": d, "concepts": ["clean"]})
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                rows = json.load(f)["rows"]
        self.assertEqual([r["id"] for r in rows], ["c01", "c02"])
        self.assertTrue(all(r["origin"] == "sheet" and r["status"] == "approved"
                            for r in rows))

    def test_validate_rejects_missing_status(self):
        rows = [{"concept": "clean", "hook": "Hi", "origin": "sheet"}]
        self.assertTrue(any("status" in e for e in content.validate(rows, ["clean"])))

    def test_validate_rejects_bad_origin(self):
        rows = [{"concept": "clean", "hook": "Hi", "status": "approved", "origin": "alien"}]
        self.assertTrue(any("origin" in e for e in content.validate(rows, ["clean"])))

    def test_validate_accepts_stamped(self):
        rows = content._stamp([{"concept": "clean", "hook": "Hi"}])
        self.assertEqual(content.validate(rows, ["clean"]), [])
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review -v`
Expected: ERROR/FAIL — `content._stamp` does not exist; `validate` does not check status/origin.

- [ ] **Step 3: Implement stamping + validation** in `kit/content.py`.

Add constants after `SHEET_EXT = (".xlsx", ".csv")`:

```python
STATUSES = ("pending", "approved", "rejected", "redo")
ORIGINS = ("sheet", "agent")
```

Add `_stamp` immediately before `def validate`:

```python
def _stamp(rows):
    """Sheet rows are the team's own copy: trusted (approved), sequential ids."""
    for i, r in enumerate(rows, 1):
        r["id"] = f"c{i:02d}"
        r["origin"] = "sheet"
        r["status"] = "approved"
    return rows
```

Extend `validate` — append these two checks inside the existing `for` loop, after the `use` check:

```python
        if r.get("status") not in STATUSES:
            errs.append(f"linha {i}: status ausente ou inválido: {r.get('status')!r} — rode content de novo")
        if r.get("origin") not in ORIGINS:
            errs.append(f"linha {i}: origin ausente ou inválido: {r.get('origin')!r} — rode content de novo")
```

In `ingest`, change the sheet-read line from `rows = read_sheet(sheet)` to:

```python
        rows = _stamp(read_sheet(sheet))
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review -v`
Expected: 4 PASS.

- [ ] **Step 5: Update existing tests for stamped rows** in `tests/test_content.py`.

In `Ingest.test_writes_content_json`, replace the expected-rows assertion:

```python
            self.assertEqual(saved["rows"], [{"concept": "clean", "hook": "Hi", "use": "ppc",
                                              "id": "c01", "origin": "sheet", "status": "approved"}])
```

In each of the four `Validate` tests, add `"status": "approved", "origin": "sheet"` to every row dict. Example (`test_ok`):

```python
        rows = [{"concept": "clean", "hook": "Hi", "use": "both",
                 "status": "approved", "origin": "sheet"}]
```

Apply the same two fields to the rows in `test_unknown_concept`, `test_bad_use`, `test_empty_hook`.

In `Sample._example_rows`, stamp the parsed rows so they validate:

```python
        return content._stamp(content._rows_from_dicts(dicts))
```

- [ ] **Step 6: Run the full suite**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS (27 existing + 4 new = 31).

- [ ] **Step 7: Commit**

```bash
git add kit/content.py tests/test_content_review.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): stamp review ids/origin/status on ingest + validate enums"
```

---

### Task 2: Apply approved-only + pending count

**Files:**
- Modify: `kit/content.py` (`apply`)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class ApplyApprovedOnly(unittest.TestCase):
    def _camp(self, d, rows):
        with open(os.path.join(d, "content.json"), "w", encoding="utf-8") as f:
            json.dump({"rows": rows}, f)
        with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"concepts": ["clean"]}, f)
        return {"_root": d, "concepts": ["clean"]}

    def test_only_approved_merged(self):
        with tempfile.TemporaryDirectory() as d:
            rows = content._stamp([{"concept": "clean", "hook": "A"},
                                   {"concept": "clean", "hook": "B"}])
            rows[1]["status"] = "pending"
            summary = content.apply(self._camp(d, rows))
            self.assertEqual(summary["merged"], 1)
            self.assertEqual(summary["pending"], 1)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                copy = json.load(f)["copy"]["default"]["clean"]
            self.assertEqual(copy["hook"], "A")
            self.assertNotIn("versions", copy)

    def test_rejected_and_redo_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            rows = content._stamp([{"concept": "clean", "hook": "A"},
                                   {"concept": "clean", "hook": "B"},
                                   {"concept": "clean", "hook": "C"}])
            rows[1]["status"] = "rejected"
            rows[2]["status"] = "redo"
            summary = content.apply(self._camp(d, rows))
            self.assertEqual(summary["merged"], 1)
            self.assertEqual(summary["pending"], 2)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ApplyApprovedOnly -v`
Expected: FAIL — `apply` merges all rows and returns no `pending` key.

- [ ] **Step 3: Rewrite `apply`** in `kit/content.py` (replace the whole function):

```python
def apply(camp):
    """Merge only approved rows into campaign.json.copy (the single review gate).

    First approved row per (axis, concept) = base entry; further approved rows =
    versions in row order. Unrelated existing copy entries are preserved.
    `pending` counts rows not approved (still awaiting review/agent).
    """
    root = camp["_root"]
    cj_path = os.path.join(root, "content.json")
    if not os.path.isfile(cj_path):
        return {"errors": ["content.json ausente — rode content primeiro"],
                "merged": 0, "pending": 0}
    with open(cj_path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    pending = sum(1 for r in rows if r.get("status") != "approved")
    errors = validate(rows, camp.get("concepts") or [])
    if errors:
        return {"errors": errors, "merged": 0, "pending": pending}
    camp_path = os.path.join(root, "campaign.json")
    with open(camp_path, encoding="utf-8") as f:
        campj = json.load(f)
    copy = campj.setdefault("copy", {})
    merged = 0
    for row in rows:
        if row.get("status") != "approved":
            continue
        key = row.get("axis") or "default"
        concept = row["concept"]
        entry = _entry(row)
        slot = copy.setdefault(key, {}).setdefault(concept, {})
        if not slot.get("hook"):
            slot.update(entry)
            merged += 1
        else:
            slot.setdefault("versions", []).append(entry)
    with open(camp_path, "w", encoding="utf-8") as f:
        json.dump(campj, f, indent=2, ensure_ascii=False)
    return {"errors": [], "merged": merged, "pending": pending}
```

- [ ] **Step 4: Run new tests + full suite**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ApplyApprovedOnly -v`
Expected: 2 PASS.
Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS (existing `Apply`/`Cli` tests still green — ingest stamps approved).

- [ ] **Step 5: Commit**

```bash
git add kit/content.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): apply merges only approved rows, reports pending count"
```

---

### Task 3: `decide` + `review_payload`

**Files:**
- Modify: `kit/content.py` (add `_load_rows`, `_save_rows`, `decide`, `review_payload`)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class DecideAndPayload(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,One\nclean,Two\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def test_decide_marks_and_persists(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            self.assertTrue(content.decide(d, "c01", "rejected", "mudar"))
            payload = content.review_payload(d)
            row = next(r for r in payload["rows"] if r["id"] == "c01")
            self.assertEqual(row["status"], "rejected")
            self.assertEqual(row["note"], "mudar")
            self.assertEqual(payload["counts"]["rejected"], 1)

    def test_decide_unknown_id_false(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            self.assertFalse(content.decide(d, "nope", "approved"))

    def test_decide_bad_status_raises(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            with self.assertRaises(ValueError):
                content.decide(d, "c01", "bogus")

    def test_review_payload_none_without_file(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(content.review_payload(d))
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.DecideAndPayload -v`
Expected: ERROR — `decide`/`review_payload` not defined.

- [ ] **Step 3: Implement** — append to `kit/content.py` (after `apply`):

```python
def _load_rows(root):
    with open(os.path.join(root, "content.json"), encoding="utf-8") as f:
        return json.load(f)


def _save_rows(root, data):
    with open(os.path.join(root, "content.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def decide(root, row_id, status, note=""):
    """Mark one row (UI/import). Writes only status/note. False if id unknown."""
    if status not in STATUSES:
        raise ValueError(f"status inválido: {status}")
    data = _load_rows(root)
    found = False
    for r in data.get("rows") or []:
        if r.get("id") == row_id:
            r["status"] = status
            if note:
                r["note"] = note
            else:
                r.pop("note", None)
            found = True
            break
    if found:
        _save_rows(root, data)
    return found


def review_payload(root):
    """{rows, counts} for the review /state, or None without content.json."""
    path = os.path.join(root, "content.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    counts = {s: sum(1 for r in rows if r.get("status") == s) for s in STATUSES}
    return {"rows": rows, "counts": counts}
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.DecideAndPayload -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/content.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): decide marks a row, review_payload exposes rows+counts"
```

---

### Task 4: `export_review` (team spreadsheet)

**Files:**
- Modify: `kit/content.py` (add `REVIEW_COLUMNS`, `_REVIEW_NOTES`, `export_review`)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class ExportReview(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,Hi\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def test_export_tabs_and_columns(self):
        from unittest import mock
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            with mock.patch("kit.campaign.delivery_dir",
                            return_value=os.path.join(d, "delivery")):
                summary = content.export_review(d, "en")
            self.assertEqual(summary["rows"], 1)
            wb = load_workbook(summary["path"])
            try:
                self.assertEqual(wb.sheetnames, ["Review", "Instructions"])
                self.assertEqual([c.value for c in wb["Review"][1]],
                                 list(content.REVIEW_COLUMNS))
            finally:
                wb.close()

    def test_export_without_content_raises(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                content.export_review(d)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ExportReview -v`
Expected: ERROR — `export_review`/`REVIEW_COLUMNS` not defined.

- [ ] **Step 3: Implement** — append to `kit/content.py`:

```python
REVIEW_COLUMNS = ("id",) + COLUMNS + ("origin", "status", "decision", "note")

_REVIEW_NOTES = {
    "pt": [
        "Preencha a coluna decision com approve / reject / redo (ou aprovar / rejeitar / refazer).",
        "Em branco = sem mudança. Edições no texto do copy são ignoradas na importação.",
        "A coluna note é opcional — use para pedir ajustes (redo) ou justificar (reject).",
        "Devolva este arquivo para importar as decisões. Re-ingest (nova planilha base) zera as decisões.",
    ],
    "en": [
        "Fill the decision column with approve / reject / redo (or aprovar / rejeitar / refazer).",
        "Blank = no change. Edits to the copy text are ignored on import.",
        "The note column is optional — use it to request changes (redo) or justify (reject).",
        "Send this file back to import the decisions. Re-ingest (new base sheet) resets decisions.",
    ],
}


def export_review(root, lang="pt"):
    """Write content_review.xlsx into <delivery>/content_review/. {path, rows}."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    from . import campaign as C

    payload = review_payload(root)
    if payload is None:
        raise ValueError("content.json ausente — rode content primeiro")
    rows = payload["rows"]
    key = "pt" if lang == "pt" else "en"
    wb = Workbook()
    ws = wb.active
    ws.title = "Review"
    ws.append(list(REVIEW_COLUMNS))
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([r.get(col, "") for col in REVIEW_COLUMNS])
    for i, w in enumerate((8, 12, 12, 46, 12, 26, 18, 8, 6, 8, 10, 12, 30), 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ins = wb.create_sheet("Instruções" if key == "pt" else "Instructions")
    for line in _REVIEW_NOTES[key]:
        ins.append([line])
    dest_dir = os.path.join(C.delivery_dir(root), "content_review")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "content_review.xlsx")
    wb.save(path)
    wb.close()
    return {"path": path, "rows": len(rows)}
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ExportReview -v`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/content.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): export review spreadsheet (Review + Instructions tabs)"
```

---

### Task 5: `import_decisions` + `_raw_rows` refactor + decision aliases

**Files:**
- Modify: `kit/content.py` (`ALIASES`, `_DECISION_VALUES`, `_raw_rows`, `read_sheet`, `import_decisions`)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class ImportDecisions(unittest.TestCase):
    def _setup(self, d):
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,One\nclean,Two\nclean,Three\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def _return_xlsx(self, d, rows):
        from openpyxl import Workbook
        p = os.path.join(d, "return.xlsx")
        wb = Workbook()
        ws = wb.active
        ws.append(["id", "decision", "note"])
        for row in rows:
            ws.append(list(row))
        wb.save(p)
        wb.close()
        return p

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "approve", ""),
                                      ("c02", "reject", "mudar"),
                                      ("c03", "", "")])
            summary = content.import_decisions(d, p)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["approved"], 1)
            self.assertEqual(summary["rejected"], 1)
            self.assertEqual(summary["unchanged"], 1)
            rows = {r["id"]: r for r in content.review_payload(d)["rows"]}
            self.assertEqual(rows["c01"]["status"], "approved")
            self.assertEqual(rows["c02"]["status"], "rejected")
            self.assertEqual(rows["c02"]["note"], "mudar")
            self.assertEqual(rows["c03"]["status"], "approved")

    def test_unknown_id_blocks_all(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "reject", ""), ("nope", "approve", "")])
            summary = content.import_decisions(d, p)
            self.assertTrue(summary["errors"])
            rows = {r["id"]: r for r in content.review_payload(d)["rows"]}
            self.assertEqual(rows["c01"]["status"], "approved")  # nothing written

    def test_bad_decision_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = self._return_xlsx(d, [("c01", "maybe", "")])
            self.assertTrue(content.import_decisions(d, p)["errors"])

    def test_missing_id_column_blocks(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = os.path.join(d, "noid.xlsx")
            wb = Workbook()
            wb.active.append(["decision"])
            wb.active.append(["approve"])
            wb.save(p)
            wb.close()
            self.assertTrue(content.import_decisions(d, p)["errors"])

    def test_pt_decision_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            p = os.path.join(d, "return.csv")
            with open(p, "w", encoding="utf-8") as f:
                f.write("id,decisao,nota\nc01,aprovar,\nc02,rejeitar,ajustar\n")
            summary = content.import_decisions(d, p)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["approved"], 1)
            self.assertEqual(summary["rejected"], 1)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ImportDecisions -v`
Expected: ERROR — `import_decisions` not defined.

- [ ] **Step 3: Add decision/note aliases** — extend the `ALIASES` dict in `kit/content.py` (add these entries before the closing brace):

```python
    "decisao": "decision", "aprovacao": "decision", "approval": "decision",
    "nota": "note", "observacao": "note", "comment": "note",
```

Add the decision map after `ORIGINS`:

```python
_DECISION_VALUES = {
    "approve": "approved", "aprovar": "approved",
    "reject": "rejected", "rejeitar": "rejected",
    "redo": "redo", "refazer": "redo",
}
```

- [ ] **Step 4: Refactor `read_sheet` into `_raw_rows`** — replace the existing `read_sheet` function with:

```python
def _raw_rows(path):
    """Normalized-header dicts from .xlsx/.csv (all columns; empty cells kept)."""
    low = path.lower()
    if low.endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            return [dict((_norm_header(k), v) for k, v in row.items())
                    for row in csv.DictReader(f)]
    if low.endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            it = wb.active.iter_rows(values_only=True)
            headers = [_norm_header(h) for h in next(it, ())]
            return [dict(zip(headers, vals)) for vals in it]
        finally:
            wb.close()
    raise ValueError(f"unsupported sheet extension: {path} (use .xlsx or .csv)")


def read_sheet(path):
    """Canonical rows from .xlsx/.csv. Empty cells dropped; blank use = both."""
    return _rows_from_dicts(_raw_rows(path))
```

- [ ] **Step 5: Implement `import_decisions`** — append to `kit/content.py`:

```python
def import_decisions(root, path):
    """Apply team decisions from a returned review sheet. Atomic; decisions only."""
    zeros = {"approved": 0, "rejected": 0, "redo": 0, "unchanged": 0}
    if os.path.getsize(path) > 20 * 1024 * 1024:
        return {"errors": ["arquivo > 20 MB"], **zeros}
    try:
        raw = _raw_rows(path)
    except Exception as e:
        return {"errors": [f"não foi possível ler a planilha: {e}"], **zeros}
    if not raw:
        return {"errors": ["planilha sem linhas"], **zeros}
    if "id" not in raw[0]:
        return {"errors": ["coluna id ausente — use a planilha exportada"], **zeros}
    data = _load_rows(root)
    by_id = {r.get("id"): r for r in data.get("rows") or []}
    errors, changes, unchanged = [], [], 0
    for i, rr in enumerate(raw, 2):
        rid = str(rr.get("id") or "").strip()
        if not rid:
            errors.append(f"linha {i}: id vazio")
            continue
        if rid not in by_id:
            errors.append(f"linha {i}: id desconhecido: {rid}")
            continue
        decision = str(rr.get("decision") or "").strip().lower()
        note = str(rr.get("note") or "").strip()
        if decision == "":
            unchanged += 1
            continue
        if decision not in _DECISION_VALUES:
            errors.append(f"linha {i}: decision inválida: {decision} (approve/reject/redo)")
            continue
        changes.append((by_id[rid], _DECISION_VALUES[decision], note))
    if errors:
        return {"errors": errors, **zeros}
    counts = dict(zeros)
    counts["unchanged"] = unchanged
    for row, status, note in changes:
        row["status"] = status
        if note:
            row["note"] = note
        else:
            row.pop("note", None)
        counts[status] += 1
    _save_rows(root, data)
    counts["errors"] = []
    return counts
```

- [ ] **Step 6: Run new tests + full suite**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.ImportDecisions -v`
Expected: 5 PASS.
Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS (the `read_sheet` refactor preserves behavior — `ReadSheet` tests stay green).

- [ ] **Step 7: Commit**

```bash
git add kit/content.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): import team decisions (atomic, id-matched, PT/EN aliases)"
```

---

### Task 6: CLI `content --export` / `content --import PATH`

**Files:**
- Modify: `kit/cli.py` (content subparser + handler)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing test** — append to `tests/test_content_review.py`:

```python
class CliReview(unittest.TestCase):
    def test_export_then_import(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        from kit import cli
        with tempfile.TemporaryDirectory() as d:
            cdir = os.path.join(d, "content")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
                f.write("concept,hook\nclean,Hi\n")
            with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
                json.dump({"concepts": ["clean"]}, f)
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["content", d]), 0)
            with mock.patch("kit.campaign.delivery_dir",
                            return_value=os.path.join(d, "delivery")):
                with redirect_stdout(buf):
                    self.assertEqual(cli.main(["content", d, "--export"]), 0)
            self.assertTrue(os.path.isfile(os.path.join(
                d, "delivery", "content_review", "content_review.xlsx")))
            ret = os.path.join(d, "return.csv")
            with open(ret, "w", encoding="utf-8") as f:
                f.write("id,decision\nc01,reject\n")
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["content", d, "--import", ret]), 0)
            self.assertEqual(content.review_payload(d)["rows"][0]["status"], "rejected")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.CliReview -v`
Expected: FAIL — `--export`/`--import` are unrecognized arguments.

- [ ] **Step 3: Add the flags** in `kit/cli.py`, in the `content` subparser (after the `--apply` line):

```python
    p.add_argument("--export", action="store_true",
                   help="exporta planilha de revisão p/ o time (content_review.xlsx)")
    p.add_argument("--import", dest="import_path", metavar="PATH",
                   help="importa decisões da planilha devolvida pelo time")
```

- [ ] **Step 4: Update the handler** — replace the `if args.cmd == "content":` block in `kit/cli.py`:

```python
    if args.cmd == "content":
        if args.export:
            try:
                summary = content.export_review(camp["_root"], lang)
            except ValueError as e:
                print(str(e), file=sys.stderr)
                return 1
        elif args.import_path:
            summary = content.import_decisions(camp["_root"], os.path.expanduser(args.import_path))
        else:
            summary = content.apply(camp) if args.apply else content.ingest(camp)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 1 if summary.get("errors") else 0
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.CliReview -v`
Expected: 1 PASS.

- [ ] **Step 6: Commit**

```bash
git add kit/cli.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(cli): content --export / --import for the team review round-trip"
```

---

### Task 7: UI endpoints + `/state` fallback + error i18n keys

**Files:**
- Modify: `kit/ui.py` (`do_GET /state`, `/copy-export`; `do_POST /copy-import`, `/copy-decision`, `/copy-apply`; `_copy_import`)
- Modify: `kit/i18n.py` (4 error keys PT/EN)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class Endpoints(unittest.TestCase):
    def _server(self, d):
        import threading
        from http.server import ThreadingHTTPServer
        from kit import ui
        ui.Handler.root = d
        ui.Handler.mode = "review"
        srv = ThreadingHTTPServer(("127.0.0.1", 0), ui.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def _setup(self, d):
        with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"slug": "t", "brand": "b", "concepts": ["clean"]}, f)
        cdir = os.path.join(d, "content")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook\nclean,Hi\n")
        content.ingest({"_root": d, "concepts": ["clean"]})

    def test_state_fallback_and_content(self):
        import urllib.request
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)  # no state.json yet
            srv = self._server(d)
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                with urllib.request.urlopen(base + "/state") as r:
                    state = json.load(r)
                self.assertEqual(state["pieces"], [])
                self.assertEqual(state["content"]["counts"]["approved"], 1)
            finally:
                srv.shutdown()

    def test_copy_decision_and_apply(self):
        import urllib.request
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            srv = self._server(d)
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                req = urllib.request.Request(base + "/copy-decision",
                                             data=json.dumps({"id": "c01", "status": "rejected"}).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                self.assertEqual(content.review_payload(d)["rows"][0]["status"], "rejected")
                req = urllib.request.Request(base + "/copy-decision",
                                             data=json.dumps({"id": "c01", "status": "approved"}).encode(),
                                             headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req).close()
                req = urllib.request.Request(base + "/copy-apply", data=b"{}",
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(json.load(r)["merged"], 1)
            finally:
                srv.shutdown()

    def test_copy_decision_bad_status_400(self):
        import urllib.request
        import urllib.error
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            srv = self._server(d)
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                req = urllib.request.Request(base + "/copy-decision",
                                             data=json.dumps({"id": "c01", "status": "bogus"}).encode(),
                                             headers={"Content-Type": "application/json"})
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(req)
                self.assertEqual(cm.exception.code, 400)
            finally:
                srv.shutdown()

    def test_copy_export_download(self):
        import urllib.request
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            srv = self._server(d)
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                with mock.patch("kit.campaign.delivery_dir",
                                return_value=os.path.join(d, "delivery")):
                    with urllib.request.urlopen(base + "/copy-export") as r:
                        self.assertEqual(r.status, 200)
                        self.assertTrue(r.read(2) == b"PK")
            finally:
                srv.shutdown()

    def test_copy_import_round_trip(self):
        import urllib.request
        with tempfile.TemporaryDirectory() as d:
            self._setup(d)
            srv = self._server(d)
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                body = b"id,decision\nc01,reject\n"
                req = urllib.request.Request(base + "/copy-import", data=body,
                                             headers={"X-Filename": "return.csv"})
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(json.load(r)["rejected"], 1)
                self.assertEqual(content.review_payload(d)["rows"][0]["status"], "rejected")
            finally:
                srv.shutdown()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.Endpoints -v`
Expected: FAIL/ERROR — `/state` crashes without state.json; `/copy-*` return 404.

- [ ] **Step 3: Add the 4 error i18n keys.** In `kit/i18n.py` `_PT`, after the `"rv.restyle.defaultnote"` line, add:

```python
    "rv.copy.err.big": "Arquivo maior que 20 MB.",
    "rv.copy.err.ext": "Envie um arquivo .xlsx ou .csv.",
    "rv.copy.err.status": "Status inválido.",
    "rv.copy.err.id": "Linha de copy não encontrada.",
```

In `_EN`, after the `"rv.restyle.defaultnote"` line, add:

```python
    "rv.copy.err.big": "File larger than 20 MB.",
    "rv.copy.err.ext": "Send a .xlsx or .csv file.",
    "rv.copy.err.status": "Invalid status.",
    "rv.copy.err.id": "Copy row not found.",
```

- [ ] **Step 4: `/state` fallback + content.** In `kit/ui.py` `do_GET`, replace the review branch of `/state`:

```python
        elif url.path == "/state":
            if self.mode == "onboard":
                return self._send(200, onboard.status(self.root, lang))
            state_path = os.path.join(self.root, "state.json")
            if os.path.isfile(state_path):
                with open(state_path, encoding="utf-8") as f:
                    state = json.load(f)
            else:
                camp = campaign.load_campaign(self.root)
                state = {"campaign": camp.get("slug"), "brand": camp.get("brand"),
                         "pieces": [], "blocked_count": 0,
                         "concepts": camp.get("concepts") or []}
            cp = content.review_payload(self.root)
            if cp is not None:
                state["content"] = cp
            self._send(200, state)
```

- [ ] **Step 5: `/copy-export` GET.** In `do_GET`, add a branch before the final `else` (after the `/style` branch):

```python
        elif url.path == "/copy-export":
            try:
                summary = content.export_review(self.root, self._lang())
            except ValueError:
                return self._send(404, {"error": "content.json ausente"})
            with open(summary["path"], "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", 'attachment; filename="content_review.xlsx"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
```

- [ ] **Step 6: `/copy-import` raw-bytes branch.** In `do_POST`, insert immediately after the onboard check and BEFORE `payload = json.loads(...)`:

```python
        if self.mode == "onboard":
            return self._onboard_post(length)
        if self.path == "/copy-import":
            return self._copy_import(length)
        payload = json.loads(self.rfile.read(length) or b"{}")
```

Add the `_copy_import` method to `Handler` (place it just before `do_POST`):

```python
    def _copy_import(self, length):
        import tempfile
        lang = self._lang()
        if length > 20 * 1024 * 1024:
            return self._send(413, {"error": i18n.t("rv.copy.err.big", lang)})
        data = self.rfile.read(length)
        name = self.headers.get("X-Filename", "upload.xlsx")
        ext = os.path.splitext(name)[1].lower()
        if ext not in content.SHEET_EXT:
            return self._send(400, {"error": i18n.t("rv.copy.err.ext", lang)})
        fd, tmp = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            summary = content.import_decisions(self.root, tmp)
        finally:
            os.unlink(tmp)
        if summary.get("errors"):
            return self._send(400, {"error": "; ".join(summary["errors"])})
        self._send(200, summary)
```

- [ ] **Step 7: `/copy-decision` + `/copy-apply`.** In `do_POST`, add these branches before the final `else` (after `/open-delivery`):

```python
        elif self.path == "/copy-decision":
            lang = self._lang()
            status = payload.get("status")
            if status not in content.STATUSES:
                return self._send(400, {"error": i18n.t("rv.copy.err.status", lang)})
            if not content.decide(self.root, payload.get("id"), status, payload.get("note", "")):
                return self._send(400, {"error": i18n.t("rv.copy.err.id", lang)})
            self._send(200, {"ok": True})
        elif self.path == "/copy-apply":
            summary = content.apply(campaign.load_campaign(self.root))
            if summary.get("errors"):
                return self._send(400, {"error": "; ".join(summary["errors"])})
            self._send(200, summary)
```

- [ ] **Step 8: Run to verify pass + full suite**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.Endpoints -v`
Expected: 5 PASS.
Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add kit/ui.py kit/i18n.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(ui): copy review endpoints + /state fallback with content payload"
```

---

### Task 8: Copy panel HTML + JS + i18n

**Files:**
- Modify: `kit/ui.py` (`review_page` HTML panel + JS)
- Modify: `kit/i18n.py` (`rv.copy.*` + `rv.js.copy.*` PT/EN)
- Modify: `tests/test_content_review.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/test_content_review.py`:

```python
class Panel(unittest.TestCase):
    def test_panel_markers_both_langs(self):
        from kit import ui
        for lang in ("pt", "en"):
            page = ui.review_page(lang)
            self.assertIn('id="copypanel"', page)
            self.assertIn("/copy-export", page)
            self.assertIn("drawCopy", page)

    def test_i18n_keys_present(self):
        from kit import i18n
        for lang in ("pt", "en"):
            for key in ("rv.copy.title", "rv.copy.apply",
                        "rv.js.copy.stats", "rv.js.copy.applied"):
                self.assertTrue(i18n.t(key, lang))
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.Panel -v`
Expected: FAIL — no `copypanel`; `KeyError` on missing i18n keys.

- [ ] **Step 3: Add the panel i18n keys.** In `kit/i18n.py` `_PT`, after the `rv.copy.err.*` keys from Task 7, add:

```python
    "rv.copy.title": "Revisar copy",
    "rv.copy.desc": "Aprove, rejeite ou peça refazer o copy sugerido — cada clique só MARCA. Nada entra nas peças/planilhas até você clicar Aplicar copy aprovado. Exporte a planilha para o time aprovar online e importe as decisões de volta.",
    "rv.copy.export": "↓ Exportar planilha de revisão",
    "rv.copy.import": "↑ Importar decisões",
    "rv.copy.apply": "Aplicar copy aprovado",
    "rv.js.copy.stats": '<span class="stat"><b>{total}</b> copies</span>'
                        '<span class="stat"><b>{approved}</b> aprovadas</span>'
                        '<span class="stat"><b>{pending}</b> pendentes</span>'
                        '<span class="stat"><b>{rejected}</b> rejeitadas</span>'
                        '<span class="stat"><b>{redo}</b> refazer</span>',
    "rv.js.copy.warn": "{n} copy(s) ainda não aprovado(s) — a campanha segue rodando com o copy anterior.",
    "rv.js.copy.empty": "Nenhum copy neste filtro.",
    "rv.js.copy.ai": "IA",
    "rv.js.copy.sheet": "planilha",
    "rv.js.copy.approvedtitle": "Copy aprovado ({n})",
    "rv.js.copy.redoask": "O que ajustar neste copy?",
    "rv.js.copy.applied": "{n} copy(s) aplicado(s) · {m} ainda aguardando revisão",
    "rv.js.copy.appliedtoast": "{n} copy(s) aplicado(s) à campanha",
    "rv.js.copy.imported": "{a} aprovada(s) · {r} rejeitada(s) · {d} refazer",
```

In `_EN`, after the `rv.copy.err.*` keys, add:

```python
    "rv.copy.title": "Review copy",
    "rv.copy.desc": "Approve, reject or ask to redo the suggested copy — each click only MARKS. Nothing reaches pieces/sheets until you click Apply approved copy. Export the sheet for the team to approve online and import the decisions back.",
    "rv.copy.export": "↓ Export review sheet",
    "rv.copy.import": "↑ Import decisions",
    "rv.copy.apply": "Apply approved copy",
    "rv.js.copy.stats": '<span class="stat"><b>{total}</b> copies</span>'
                        '<span class="stat"><b>{approved}</b> approved</span>'
                        '<span class="stat"><b>{pending}</b> pending</span>'
                        '<span class="stat"><b>{rejected}</b> rejected</span>'
                        '<span class="stat"><b>{redo}</b> redo</span>',
    "rv.js.copy.warn": "{n} copy(ies) not approved yet — the campaign still runs on the previous copy.",
    "rv.js.copy.empty": "No copy matches this filter.",
    "rv.js.copy.ai": "AI",
    "rv.js.copy.sheet": "sheet",
    "rv.js.copy.approvedtitle": "Approved copy ({n})",
    "rv.js.copy.redoask": "What should change in this copy?",
    "rv.js.copy.applied": "{n} copy(ies) applied · {m} still awaiting review",
    "rv.js.copy.appliedtoast": "{n} copy(ies) applied to the campaign",
    "rv.js.copy.imported": "{a} approved · {r} rejected · {d} redo",
```

- [ ] **Step 4: Add the panel HTML.** In `kit/ui.py` `review_page`, insert this block immediately after `<div class="wrap">` and BEFORE the pieces panel (`<div class="panel"><h2><span class="n">5</span>`):

```python
<div class="panel" id="copypanel" hidden>
<h2>{i18n.t('rv.copy.title', lang)}</h2>
<p class="desc">{i18n.t('rv.copy.desc', lang)}</p>
<div class="stats" id="copystats"></div>
<div class="row" style="align-items:center">
<a class="btn" href="/copy-export" download>{i18n.t('rv.copy.export', lang)}</a>
<label class="btn" style="cursor:pointer">{i18n.t('rv.copy.import', lang)}<input type="file" id="copyimport" accept=".xlsx,.csv" hidden onchange="importCopy(this)"></label>
<button class="btn primary" onclick="applyCopy()">{i18n.t('rv.copy.apply', lang)}</button>
<span class="meta" id="copyresult"></span></div>
<div class="filters" id="copyfilters"></div>
<div class="row" style="align-items:center"><span class="meta">{i18n.t('rv.concept', lang)}</span><div class="filters" id="copycfilters"></div></div>
<div id="copywarn"></div>
<div class="rgrid" id="copygrid"></div>
<div id="copyapproved"></div>
</div>
```

- [ ] **Step 5: Add the panel JS.** In `review_page`'s trailing plain-string `<script>` block:

(a) Extend the state-vars line to add copy filters:

```javascript
let state=null, filter="working", cfilter="all", lastState="", styleOpen=false, styleConcept=null, cstatus="working", cconcept="all";
```

(b) At the end of `applyState`, change `draw();` to `draw();drawCopy();`.

(c) Add these functions immediately before `async function poll(){`:

```javascript
function drawCopy(){
  const cp=state.content, panel=document.getElementById("copypanel");
  if(!cp){panel.hidden=true;return;}
  panel.hidden=false;
  const rows=cp.rows, counts=cp.counts;
  document.getElementById("copystats").innerHTML=fill(T["copy.stats"],
    {total:rows.length,pending:counts.pending,approved:counts.approved,rejected:counts.rejected,redo:counts.redo});
  const cc={working:rows.filter(r=>r.status!=="approved").length,
    approved:counts.approved,pending:counts.pending,rejected:counts.rejected,redo:counts.redo};
  document.getElementById("copyfilters").innerHTML=Object.entries(cc)
    .map(([k,v])=>`<button class="${k===cstatus?'on':''}" onclick="setCopyStatus('${k}')">${LBL[k]} (${v})</button>`).join("");
  const ccc={};for(const r of rows)ccc[r.concept]=(ccc[r.concept]||0)+1;
  const concepts=[...new Set(rows.map(r=>r.concept))];
  document.getElementById("copycfilters").innerHTML=
    `<button class="${cconcept==='all'?'on':''}" onclick="setCopyConcept('all')">${fill(T.allconcepts,{n:rows.length})}</button>`+
    concepts.map(k=>`<button class="${cconcept===k?'on':''}" onclick="setCopyConcept('${k}')">${k} (${ccc[k]||0})</button>`).join("");
  const notApproved=rows.filter(r=>r.status!=="approved").length;
  document.getElementById("copywarn").innerHTML=notApproved>0
    ?`<div class="callout warn">${fill(T["copy.warn"],{n:notApproved})}</div>`:"";
  const items=rows.filter(r=>(cstatus==="working"?r.status!=="approved":r.status===cstatus)&&(cconcept==="all"||r.concept===cconcept));
  const g=document.getElementById("copygrid");
  if(!items.length){g.innerHTML=`<div class="empty">${T["copy.empty"]}</div>`;}
  else g.innerHTML=items.map(r=>{
    const meta=[r.kicker,r.program,r.cta].filter(Boolean).map(esc).join(" · ");
    const tags=`<span class="tag">${esc(r.concept)}</span>`
      +(r.axis?`<span class="tag">${esc(r.axis)}</span>`:"")
      +`<span class="tag">${esc(r.use||"both")}</span>`
      +(r.lang?`<span class="tag">${esc(r.lang)}</span>`:"")
      +`<span class="tag ${r.origin==="agent"?"redo":""}">${r.origin==="agent"?T["copy.ai"]:T["copy.sheet"]}</span>`;
    const note=(r.note&&(r.status==="redo"||r.status==="rejected"))?`<p class="hint">↻ ${esc(r.note)}</p>`:"";
    return `<div class="card rcard"><div class="body">
      <div class="row"><span class="tag ${r.status}"><span class="dot"></span>${SING[r.status]||r.status}</span>${tags}</div>
      <div class="name">${esc(r.hook)}</div>
      ${meta?`<p class="desc">${meta}</p>`:""}
      ${note}
      <div class="row">
        <button class="btn ok" onclick="decideCopy('${r.id}','approved')">${T.approve}</button>
        <button class="btn no" onclick="decideCopy('${r.id}','rejected')">${T.reject}</button>
        <button class="btn" onclick="redoCopy('${r.id}')">${T.redo}</button>
      </div></div></div>`;
  }).join("");
  const approved=rows.filter(r=>r.status==="approved");
  document.getElementById("copyapproved").innerHTML=approved.length
    ?`<h3>${fill(T["copy.approvedtitle"],{n:approved.length})}</h3>`+approved.map(r=>
      `<div class="row" style="align-items:center"><span class="tag approved"><span class="dot"></span>${esc(r.hook)}</span>
       <span class="meta">${esc(r.concept)}${r.axis?" · "+esc(r.axis):""} · ${esc(r.use||"both")}</span>
       <button class="btn" onclick="decideCopy('${r.id}','pending')">↺</button></div>`).join("")
    :"";
}
function setCopyStatus(s){cstatus=s;drawCopy();}
function setCopyConcept(k){cconcept=k;drawCopy();}
async function decideCopy(id,status){
  const r=await fetch("/copy-decision",{method:"POST",body:JSON.stringify({id,status})});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  await load();
  notify(status==="approved"?T.approvetoast:T.rejecttoast);
}
async function redoCopy(id){
  const note=await ask(T["copy.redoask"]);
  if(note===null)return;
  const r=await fetch("/copy-decision",{method:"POST",body:JSON.stringify({id,status:"redo",note})});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  await load();
  notify(T.regentoast);
}
async function applyCopy(){
  const r=await fetch("/copy-apply",{method:"POST",body:"{}"});
  const j=await r.json();
  const box=document.getElementById("copyresult");
  if(!r.ok){box.innerHTML=`<span class="tag rejected">${esc(j.error||"erro")}</span>`;return;}
  box.innerHTML=fill(T["copy.applied"],{n:j.merged,m:j.pending});
  notify(fill(T["copy.appliedtoast"],{n:j.merged}));
  await load();
}
async function importCopy(input){
  const file=input.files[0];input.value="";
  if(!file)return;
  const r=await fetch("/copy-import",{method:"POST",body:file,headers:{"X-Filename":file.name}});
  const j=await r.json();
  if(!r.ok){await tell(j.error||"erro");return;}
  await load();
  notify(fill(T["copy.imported"],{a:j.approved,r:j.rejected,d:j.redo}));
}
```

- [ ] **Step 6: Run to verify pass + full suite**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content_review.Panel -v`
Expected: 2 PASS.
Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add kit/ui.py kit/i18n.py tests/test_content_review.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(ui): Copy review panel (approve/reject/redo, apply, export/import) PT/EN"
```

---

### Task 9: Docs — agent contract + skill

**Files:**
- Modify: `AGENTS.md` (content section + pipeline step 3b)
- Modify: `skills/campaign-kit/SKILL.md` (steps 5b/7)

- [ ] **Step 1: Update `AGENTS.md`.** In the "Conteúdo base (planilha do time de conteúdo)" section, append a paragraph documenting the review contract:

```markdown
### Revisão do copy (etapa entre content e render)

Depois de adaptar o copy em `content.json`, **abra a revisão** (`review`) — o painel
**Revisar copy** aparece quando há `content.json`. Cada linha tem `id` (`c01…`),
`origin` (`sheet`/`agent`), `status` (`pending`/`approved`/`rejected`/`redo`) e `note`.
O ingest marca as linhas da planilha como `origin:sheet, status:approved` (copy do time
é confiável). **SEU TRABALHO:** linhas que você adiciona/edita ao adaptar ficam
`origin:agent, status:pending` (nova linha pega o próximo id livre); cumprir um
`rejected`/`redo` = reescrever o copy, voltar `status:pending` e limpar `note`. **Nunca**
marque `approved` você mesmo — isso é do usuário/time. Re-ingest (nova planilha) zera as
decisões. Só **Aplicar copy aprovado** (`content --apply`) mescla as aprovadas em
`campaign.json.copy` — render/PPC não mudam. O time aprova online pela planilha:
`content --export` gera `content_review.xlsx` na pasta de entrega; eles preenchem
`decision` (approve/reject/redo) + `note` e devolvem; `content --import <arquivo>` aplica
só as decisões (edições de texto são ignoradas). O kit nunca fala com SharePoint.
```

In the pipeline step `3b` comment block, add a line after the `--apply` line:

```bash
#    Revise o copy no navegador antes do render: o painel "Revisar copy" aprova/rejeita/refaz;
#    só "Aplicar copy aprovado" mescla as aprovadas. Time aprova online: content --export / --import.
```

- [ ] **Step 2: Update `skills/campaign-kit/SKILL.md`.** In step 5b (content) mention the Copy panel, and in step 7 (review) note that copy is reviewed before render. Add to step 5b:

```markdown
   Depois de adaptar, abra `review`: o painel **Revisar copy** deixa o usuário/time aprovar,
   rejeitar ou refazer cada linha. Só **Aplicar copy aprovado** entra no render/PPC. Para o
   time aprovar online: `content --export` → eles preenchem `decision`/`note` → `content --import`.
```

- [ ] **Step 3: Verify docs render / no broken references**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS (docs-only change; sanity check nothing else broke).

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md skills/campaign-kit/SKILL.md
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "docs: content review contract + team spreadsheet round-trip (AGENTS.md + skill)"
```

---

### Task 10: Full verification + live browser pass + push

**Files:** none (verification only)

- [ ] **Step 1: Full suite green**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t .`
Expected: all PASS — 52 tests (27 baseline + 25 new review tests). Record the count.

- [ ] **Step 2: Live browser golden path on a fixture campaign.** Create a temp campaign with a base sheet, ingest, start the review server headless, and drive it in the browser (PT and EN):
  - approve a row → it leaves the grid into "Approved copy";
  - reject a row; redo a row with a note → note callout shows;
  - **Apply approved copy** → callout "N applied · M awaiting"; verify `campaign.json.copy` got only approved;
  - **Export review sheet** → download lands in `<delivery>/content_review/`;
  - fill `decision` in a copy of the sheet, **Import decisions** → poll updates counts;
  - confirm the warn line shows while any row is unapproved.
  Use the browser tools to click and screenshot; confirm no console errors.

- [ ] **Step 3: Push** (background or long timeout — pushes are slow):

```bash
git push
```

- [ ] **Step 4: Report** — end with verified / not-verified plus the user's click steps (open review → Revisar copy panel → approve/reject/redo → Aplicar; Export/Import for the team). Note PT and EN both checked.

---

## Self-Review (completed by author)

**Spec coverage:** ingest stamping (T1), status/origin validation (T1), apply-approved-only + pending (T2), decide/review_payload (T3), export tabs/columns (T4), import round-trip + aliases + atomic block + 20MB (T5), CLI flags (T6), four endpoints + /state fallback (T7), panel + chips + approved list + warn line + i18n PT/EN (T8), docs (T9), verification + live pass (T10). All spec sections map to a task.

**Placeholder scan:** no TBD/TODO; every code step has complete code; every run step has an exact command + expected result.

**Type consistency:** `decide(root,…)`, `review_payload(root)`, `export_review(root,lang)`, `import_decisions(root,path)` all root-based; `apply/ingest` stay camp-dict-based; CLI passes `camp["_root"]`; UI passes `self.root`. `REVIEW_COLUMNS` = id + COLUMNS + (origin,status,decision,note) = 13 cols, matching the 13 width values. `_DECISION_VALUES` maps to `STATUSES`. i18n keys referenced by endpoints (T7) are added in T7; panel keys (T8) added in T8 — no forward references.