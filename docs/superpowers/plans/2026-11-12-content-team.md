# Content-Team Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the content team feed base ad copy from a spreadsheet (SharePoint link or local file), route each copy to images / PPC / both via a `use` column, and let the agent expand versions per briefing rules.

**Architecture:** New `kit/content.py` (parse → validate → apply, normalize pattern: kit prepares, agent adapts, kit validates). Wizard gains a `content` slot + SharePoint link field. `use` filtering added to `campaign.run` (render) and `kit/ppc.py` (export). Spec: `docs/superpowers/specs/2026-11-12-content-team-design.md`.

**Tech Stack:** Python 3.12 (`.venv/Scripts/python.exe` on Windows), openpyxl (already a dep), stdlib `unittest` (no new deps), PIL render engine unchanged.

**Conventions:** commits use `git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit` (no git identity configured; never edit git config). Run tests from repo root. PT is the source language; EN is an overlay in `kit/i18n.py`.

---

### Task 1: Test scaffold + sheet reader

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/test_content.py`
- Create: `kit/content.py`

- [ ] **Step 1: Write the failing test**

`tests/__init__.py`: empty file.

`tests/test_content.py`:

```python
import os
import tempfile
import unittest

from kit import content


class ReadSheet(unittest.TestCase):
    def test_csv_with_aliases(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                f.write("conceito,gancho,uso\n clean,Hello,ppc\n")
            rows = content.read_sheet(p)
        self.assertEqual(rows, [{"concept": "clean", "hook": "Hello", "use": "ppc"}])

    def test_xlsx_canonical_headers(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.xlsx")
            wb = Workbook()
            ws = wb.active
            ws.append(["concept", "hook", "kicker", "use"])
            ws.append(["clean", "Hello", "World", "both"])
            ws.append(["clean", "", "empty hook row", ""])
            wb.save(p)
            rows = content.read_sheet(p)
        self.assertEqual(rows[0], {"concept": "clean", "hook": "Hello",
                                   "kicker": "World", "use": "both"})
        self.assertEqual(rows[1]["hook"], "")

    def test_blank_use_defaults_to_both(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write("concept,hook\nclean,Hi\n")
            rows = content.read_sheet(p)
        self.assertEqual(rows[0]["use"], "both")

    def test_unknown_extension_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "base.txt")
            open(p, "w").write("concept,hook\n")
            with self.assertRaises(ValueError):
                content.read_sheet(p)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: ERROR — `ModuleNotFoundError: No module named 'kit.content'` (kit/content.py does not exist yet; on Linux/macOS use `.venv/bin/python`).

- [ ] **Step 3: Write minimal implementation**

`kit/content.py`:

```python
"""Base content from the content team's spreadsheet.

Normalize pattern: the kit parses + validates, the agent adapts per the briefing
rules, the kit applies. One row = one base copy; `use` routes it (image/ppc/both).
"""

import csv
import os

COLUMNS = ("concept", "axis", "hook", "kicker", "program", "cta", "use", "lang")
ALIASES = {
    "conceito": "concept", "eixo": "axis", "gancho": "hook", "chamada": "hook",
    "headline": "hook", "apoio": "kicker", "subtitulo": "kicker",
    "programa": "program", "oferta": "program", "uso": "use", "destino": "use",
    "idioma": "lang", "locale": "lang",
}
USES = ("image", "ppc", "both")
SHEET_EXT = (".xlsx", ".csv")


def _norm_header(h):
    h = str(h or "").strip().lower()
    return ALIASES.get(h, h)


def _rows_from_dicts(dicts):
    rows = []
    for raw in dicts:
        row = {}
        for k, v in raw.items():
            key = _norm_header(k)
            if key in COLUMNS and v is not None and str(v).strip() != "":
                row[key] = str(v).strip()
        if not row:
            continue
        row.setdefault("use", "both")
        rows.append(row)
    return rows


def read_sheet(path):
    """Canonical rows from .xlsx/.csv. Empty cells dropped; blank use = both."""
    low = path.lower()
    if low.endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            return _rows_from_dicts(list(csv.DictReader(f)))
    if low.endswith(".xlsx"):
        from openpyxl import load_workbook
        ws = load_workbook(path, read_only=True, data_only=True).active
        it = ws.iter_rows(values_only=True)
        headers = [_norm_header(h) for h in next(it, ())]
        dicts = [dict(zip(headers, vals)) for vals in it]
        return _rows_from_dicts(dicts)
    raise ValueError(f"unsupported sheet extension: {path} (use .xlsx or .csv)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/__init__.py tests/test_content.py kit/content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): spreadsheet reader (csv/xlsx, PT/EN header aliases)"
```

---

### Task 2: Row validation + ingest

**Files:**
- Modify: `kit/content.py` (append)
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class Validate(unittest.TestCase):
    def test_ok(self):
        rows = [{"concept": "clean", "hook": "Hi", "use": "both"}]
        self.assertEqual(content.validate(rows, ["clean"]), [])

    def test_unknown_concept(self):
        rows = [{"concept": "nope", "hook": "Hi", "use": "both"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("nope" in e for e in errs))

    def test_bad_use(self):
        rows = [{"concept": "clean", "hook": "Hi", "use": "banner"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("use" in e for e in errs))

    def test_empty_hook(self):
        rows = [{"concept": "clean", "hook": "", "use": "both"}]
        errs = content.validate(rows, ["clean"])
        self.assertTrue(any("hook" in e for e in errs))


class Ingest(unittest.TestCase):
    def test_writes_content_json(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            cdir = os.path.join(d, "content")
            os.makedirs(cdir)
            with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
                f.write("concept,hook,use\nclean,Hi,ppc\n")
            with open(os.path.join(cdir, "content_link.txt"), "w", encoding="utf-8") as f:
                f.write("https://sharepoint.example/base.xlsx\n")
            camp = {"_root": d, "concepts": ["clean"]}
            summary = content.ingest(camp)
            self.assertEqual(summary["errors"], [])
            self.assertEqual(summary["link"], "https://sharepoint.example/base.xlsx")
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["rows"], [{"concept": "clean", "hook": "Hi", "use": "ppc"}])

    def test_no_sheet_is_gap_not_error(self):
        with tempfile.TemporaryDirectory() as d:
            camp = {"_root": d, "concepts": ["clean"]}
            summary = content.ingest(camp)
            self.assertEqual(summary["rows"], [])
            self.assertTrue(summary["gaps"])
            self.assertEqual(summary["errors"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: FAIL — `AttributeError: module 'kit.content' has no attribute 'validate'`.

- [ ] **Step 3: Write minimal implementation**

Append to `kit/content.py`:

```python
import json


def validate(rows, concepts):
    """Row-level errors (PT — agent contract). Empty list = appliable."""
    errs = []
    for i, r in enumerate(rows, 1):
        if not r.get("concept"):
            errs.append(f"linha {i}: concept vazio")
        elif r["concept"] not in concepts:
            errs.append(f"linha {i}: conceito não declarado: {r['concept']}")
        if not r.get("hook"):
            errs.append(f"linha {i}: hook vazio")
        if r.get("use", "both") not in USES:
            errs.append(f"linha {i}: use inválido: {r.get('use')} (image/ppc/both)")
    return errs


def find_sheet(root):
    d = os.path.join(root, "content")
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.lower().endswith(SHEET_EXT):
            return os.path.join(d, f)
    return None


def ingest(camp):
    """Parse + validate the sheet into <campaign>/content.json. Touches nothing else."""
    root = camp["_root"]
    sheet = find_sheet(root)
    link_path = os.path.join(root, "content", "content_link.txt")
    link = ""
    if os.path.isfile(link_path):
        with open(link_path, encoding="utf-8") as f:
            link = f.read().strip()
    rows, gaps = [], []
    if sheet:
        rows = read_sheet(sheet)
    elif link:
        gaps.append("link presente, arquivo ausente — o agente baixa a planilha uma vez "
                    "e salva em content/ antes de rodar content de novo")
    else:
        gaps.append("sem planilha em content/ — passo opcional; o copy manual segue valendo")
    errors = validate(rows, camp.get("concepts") or []) if rows else []
    out = {"source": {"file": os.path.relpath(sheet, root) if sheet else None, "link": link},
           "rows": rows, "gaps": gaps, "errors": errors}
    with open(os.path.join(root, "content.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return {"file": out["source"]["file"], "link": link, "rows": len(rows),
            "gaps": gaps, "errors": errors}
```

Note: move the `import json` to the top of the file with the other imports (keep one import block).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/content.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): row validation + ingest into content.json"
```

---

### Task 3: Apply (merge into campaign.json.copy)

**Files:**
- Modify: `kit/content.py` (append)
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class Apply(unittest.TestCase):
    def _camp(self, d, rows):
        import json
        cdir = os.path.join(d, "content")
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "base.csv"), "w", encoding="utf-8") as f:
            f.write("concept,hook,use\n" + "\n".join(
                f"{r['concept']},{r['hook']},{r.get('use', 'both')}" for r in rows) + "\n")
        with open(os.path.join(d, "campaign.json"), "w", encoding="utf-8") as f:
            json.dump({"concepts": ["clean"], "copy": {"default": {"other": {"hook": "keep"}}}}, f)
        content.ingest({"_root": d, "concepts": ["clean"]})
        return {"_root": d, "concepts": ["clean"]}

    def test_base_and_versions(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "V1"},
                                  {"concept": "clean", "hook": "V2", "use": "ppc"}])
            summary = content.apply(camp)
            self.assertEqual(summary["errors"], [])
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            entry = campj["copy"]["default"]["clean"]
            self.assertEqual(entry["hook"], "V1")
            self.assertEqual(entry["versions"], [{"hook": "V2", "use": "ppc"}])
            self.assertEqual(campj["copy"]["default"]["other"], {"hook": "keep"})

    def test_axis_key(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "Hi"}])
            with open(os.path.join(d, "content.json"), encoding="utf-8") as f:
                cj = json.load(f)
            cj["rows"][0]["axis"] = "BC|Course-02"
            with open(os.path.join(d, "content.json"), "w", encoding="utf-8") as f:
                json.dump(cj, f)
            content.apply(camp)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            self.assertIn("clean", campj["copy"]["BC|Course-02"])

    def test_errors_block_apply(self):
        with tempfile.TemporaryDirectory() as d:
            camp = self._camp(d, [{"concept": "clean", "hook": "Hi", "use": "banner"}])
            summary = content.apply(camp)
            self.assertTrue(summary["errors"])
            import json
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                campj = json.load(f)
            self.assertNotIn("clean", campj["copy"]["default"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: FAIL — `AttributeError: module 'kit.content' has no attribute 'apply'`.

- [ ] **Step 3: Write minimal implementation**

Append to `kit/content.py`:

```python
def _entry(row):
    e = {k: row[k] for k in ("hook", "kicker", "program", "cta", "lang") if row.get(k)}
    e["use"] = row.get("use", "both")
    return e


def apply(camp):
    """Re-validate content.json and merge rows into campaign.json.copy.

    First row per (axis, concept) = base entry; further rows = versions.
    Existing copy entries not covered by the sheet are preserved.
    """
    root = camp["_root"]
    cj_path = os.path.join(root, "content.json")
    if not os.path.isfile(cj_path):
        return {"errors": ["content.json ausente — rode content primeiro"], "merged": 0}
    with open(cj_path, encoding="utf-8") as f:
        rows = json.load(f).get("rows") or []
    errors = validate(rows, camp.get("concepts") or [])
    if errors:
        return {"errors": errors, "merged": 0}
    camp_path = os.path.join(root, "campaign.json")
    with open(camp_path, encoding="utf-8") as f:
        campj = json.load(f)
    copy = campj.setdefault("copy", {})
    merged = 0
    for row in rows:
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
    return {"errors": [], "merged": merged}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/content.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): apply merges base+versions into campaign.json.copy"
```

---

### Task 4: `content` CLI command

**Files:**
- Modify: `kit/cli.py:69-77` (subparsers) and after the `plan` handler
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class Cli(unittest.TestCase):
    def test_content_ingest_and_apply(self):
        import io
        import json
        from contextlib import redirect_stdout
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
                rc = cli.main(["content", d])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join(d, "content.json")))
            with redirect_stdout(buf):
                rc = cli.main(["content", d, "--apply"])
            self.assertEqual(rc, 0)
            with open(os.path.join(d, "campaign.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["copy"]["default"]["clean"]["hook"], "Hi")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content.Cli -v`
Expected: FAIL — `SystemExit: 2` (argparse: invalid choice 'content').

- [ ] **Step 3: Write minimal implementation**

In `kit/cli.py`, add `content` to the import line: `from . import briefing, campaign, content, i18n, intake, onboard, providers, render, ui, video`.

Add the subparser right after the `plan` subparser (line ~70):

```python
    p = sub.add_parser("content", help="copy base da planilha do time de conteúdo (ingest → agente adapta → --apply)")
    p.add_argument("campaign")
    p.add_argument("--apply", action="store_true", help="valida content.json e mescla em campaign.json.copy")
```

Add the handler immediately before `if args.cmd == "plan":` (after the `camp = campaign.load_campaign(...)` line):

```python
    if args.cmd == "content":
        summary = content.apply(camp) if args.apply else content.ingest(camp)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 1 if summary.get("errors") else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/cli.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(content): content CLI (ingest / --apply)"
```

---

### Task 5: Wizard slot + SharePoint link field

**Files:**
- Modify: `kit/onboard.py` (SLOTS + status)
- Modify: `kit/ui.py` (onboard_page panel 1, load()/saveLink JS, /content-link POST, i18n keys)
- Modify: `kit/i18n.py` (PT + EN keys)
- Modify: `kit/intake.py` (inventory content bucket)
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class Wizard(unittest.TestCase):
    def test_slot_and_link_in_status(self):
        from kit import onboard
        with tempfile.TemporaryDirectory() as d:
            onboard.scaffold(d)
            self.assertTrue(os.path.isdir(os.path.join(d, "content")))
            with open(os.path.join(d, "content_link.txt"), "w", encoding="utf-8") as f:
                f.write("https://sharepoint.example/base.xlsx\n")
            st = onboard.status(d)
            self.assertIn("content", st["slots"])
            self.assertEqual(st["content_link"], "https://sharepoint.example/base.xlsx")
            self.assertFalse(st["slots"]["content"]["required"])

    def test_intake_collects_content(self):
        from kit import intake
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "content"))
            p = os.path.join(d, "content", "base.csv")
            open(p, "w").write("concept,hook\nclean,Hi\n")
            inv = intake.inventory(d)
            self.assertEqual(inv["content"], [p])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content.Wizard -v`
Expected: FAIL — `KeyError: 'content'` (slot missing) / `KeyError: 'content'` in inventory.

- [ ] **Step 3: Write minimal implementation**

`kit/onboard.py` — add to `SLOTS` (after the `videos` entry):

```python
    {"key": "content", "dir": "content", "label": "Base content (spreadsheet)",
     "ext": (".xlsx", ".csv"), "multiple": False, "required": False,
     "hint": "Opcional. Planilha do time de conteúdo com o copy base (colunas: concept, hook, kicker, program, cta, use). A coluna use roteia: image / ppc / both."},
```

In `status()`, add to the returned dict (read the link file):

```python
    link_path = os.path.join(inbox, "content_link.txt")
    content_link = ""
    if os.path.isfile(link_path):
        with open(link_path, encoding="utf-8") as f:
            content_link = f.read().strip()
```

and include `"content_link": content_link` in the returned dict.

`kit/intake.py` — in `inventory()`: add `"content": []` to the `found` dict; inside the walk loop, before the extension checks:

```python
            if top == "content" and low.endswith((".xlsx", ".csv")):
                found["content"].append(p)
                continue
```

In `run()` summary dict add `"content": inv["content"],`.

`kit/i18n.py` — PT block (after `slot.videos.hint`, line ~270):

```python
    "slot.content.label": "Conteúdo base (planilha)",
    "slot.content.hint": "Opcional. Planilha do time de conteúdo com o copy base (colunas: concept, hook, kicker, program, cta, use). A coluna use roteia: image / ppc / both.",
    "ob.content.linkph": "Link do SharePoint (opcional)",
    "ob.content.linksave": "salvar link",
    "ob.content.linknote": "O agente baixa a planilha uma vez; o kit lê o arquivo local.",
```

EN block (after the EN `slot.videos.hint`):

```python
    "slot.content.label": "Base content (spreadsheet)",
    "slot.content.hint": "Optional. The content team's sheet with base copy (columns: concept, hook, kicker, program, cta, use). The use column routes: image / ppc / both.",
    "ob.content.linkph": "SharePoint link (optional)",
    "ob.content.linksave": "save link",
    "ob.content.linknote": "The agent downloads the sheet once; the kit reads the local file.",
```

`kit/ui.py` — in `onboard_page`, panel 1, right after `<div class="grid" id="slots"></div></div>` change to keep the panel open and add the link row before the closing `</div>`:

```python
<div class="grid" id="slots"></div>
<div class="row" style="margin-top:10px"><input type="text" id="contentlink"
  placeholder="{i18n.t('ob.content.linkph', lang)}">
<button class="btn" onclick="saveLink()">{i18n.t('ob.content.linksave', lang)}</button></div>
<p class="desc">{i18n.t('ob.content.linknote', lang)}</p></div>
```

In the onboard JS `load()`, after the `docslist` block, add:

```javascript
  const cl=document.getElementById("contentlink");
  if(document.activeElement!==cl) cl.value=S.content_link||"";
```

Add the JS function next to `saveBrief`:

```javascript
async function saveLink(){
  await fetch("/content-link",{method:"POST",body:JSON.stringify({link:document.getElementById("contentlink").value})});
  await load();
}
```

In `_onboard_post`, after the `/briefing` handler (payload already parsed):

```python
        if url.path == "/content-link":
            link = str(payload.get("link", "")).strip()
            with open(os.path.join(self.root, "content_link.txt"), "w", encoding="utf-8") as f:
                f.write(link)
            return self._send(200, {"ok": True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 16 tests PASS.

- [ ] **Step 5: Live wizard check**

Restart the wizard (stop the running background task, then):
`.venv/Scripts/python.exe -m kit.cli onboard "C:\Users\owkda\OneDrive\Área de Trabalho\minha-campanha"` (background).
Open http://127.0.0.1:8766, confirm the "Base content (spreadsheet)" slot renders, type a link, click save, refresh — link persists. Toggle EN — slot label/hint in English.

- [ ] **Step 6: Commit**

```bash
git add kit/onboard.py kit/ui.py kit/i18n.py kit/intake.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(onboard): content slot + SharePoint link field (PT/EN)"
```

---

### Task 6: Briefing section 11 (PT/EN)

**Files:**
- Modify: `kit/onboard.py` (BRIEFING_TEMPLATE + BRIEFING_TEMPLATE_EN)
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class BriefingSection(unittest.TestCase):
    def test_section_11_present_both_langs(self):
        from kit import onboard
        for tmpl, marker in ((onboard.BRIEFING_TEMPLATE, "_preencher"),
                             (onboard.BRIEFING_TEMPLATE_EN, "_fill in")):
            self.assertIn("## 11.", tmpl)
            self.assertIn(marker, tmpl.split("## 11.")[1])

    def test_section_11_not_required(self):
        from kit import onboard
        with tempfile.TemporaryDirectory() as d:
            onboard.scaffold(d)
            st = onboard.status(d)
            self.assertFalse(any(t.startswith("11.") for t in st["briefing"]["missing"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content.BriefingSection -v`
Expected: FAIL — `AssertionError` (no `## 11.` in templates).

- [ ] **Step 3: Write minimal implementation**

Append to `BRIEFING_TEMPLATE` (PT), after section 10:

```markdown
## 11. Conteúdo base e regras
_preencher: link da planilha do time de conteúdo (SharePoint ou arquivo) e as regras de adaptação — ex.: "15 versões a mais, hooks mais curtos para Stories". Coluna use da planilha: image / ppc / both._
```

Append to `BRIEFING_TEMPLATE_EN`, after section 10:

```markdown
## 11. Base content & rules
_fill in: link to the content team's spreadsheet (SharePoint or file) and the adaptation rules — e.g. "15 more versions, shorter hooks for Stories". Sheet use column: image / ppc / both._
```

Do NOT add "11." to `REQUIRED_SECTIONS` (stays `("1.", "2.", "3.")`).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 18 tests PASS. Also re-run the i18n swap check:
`.venv/Scripts/python.exe -c "from kit import onboard; assert onboard.BRIEFING_TEMPLATE.strip()!=onboard.BRIEFING_TEMPLATE_EN.strip(); print('OK templates')"`.

- [ ] **Step 5: Commit**

```bash
git add kit/onboard.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(onboard): briefing section 11 — base content & rules (PT/EN)"
```

---

### Task 7: Render respects `use`

**Files:**
- Modify: `kit/campaign.py:192-196` (run loop)
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class RenderRouting(unittest.TestCase):
    def test_ppc_only_copy_skips_images(self):
        from kit import campaign as C
        camp = C.load_campaign("campaigns/acme-launch")
        entries = [e for concepts in (camp.get("copy") or {}).values()
                   if isinstance(concepts, dict) for e in concepts.values()
                   if isinstance(e, dict)]
        self.assertTrue(entries)
        for e in entries:
            e["hook"] = e.get("hook") or "Hi"
            e["use"] = "ppc"
        state = C.run(camp, dry=True)
        self.assertEqual(state["pieces"], [])
        for e in entries:
            e["use"] = "both"
        state = C.run(camp, dry=True)
        self.assertTrue(state["pieces"])
```

Note: acme's copy is keyed by axis (`Agenda`), not `default` — the test marks every
real concept entry, so it works regardless of key layout.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content.RenderRouting -v`
Expected: FAIL — pieces rendered despite `use: ppc` (first assertEqual fails).

- [ ] **Step 3: Write minimal implementation**

In `kit/campaign.py` `run()`, right after `voice = copy.get(concept)` (line ~192):

```python
            if isinstance(voice, dict) and voice.get("use") == "ppc":
                continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 19 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/campaign.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(render): use=ppc copy never renders into images"
```

---

### Task 8: PPC routing + versions + ppc-only rows

**Files:**
- Modify: `kit/ppc.py:78-87` (_copy_for), `_meta_rows`, `_display_rows`, `_rsa_rows`, `export`
- Modify: `tests/test_content.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_content.py`:

```python
class PpcRouting(unittest.TestCase):
    def _brand(self):
        from kit import campaign as C
        return C.brand_for(C.load_campaign("campaigns/acme-launch"))

    def _camp(self):
        return {"slug": "t", "concepts": ["clean"], "cta": "Learn more",
                "copy": {"default": {"clean": {
                    "hook": "Base", "kicker": "K", "program": "P", "cta": "Buy",
                    "use": "both",
                    "versions": [{"hook": "V2", "use": "ppc"}]}}}}

    def _piece(self):
        return {"id": "p1", "concept": "clean", "format": "meta_feed_square",
                "axes": {}, "path": "clean/p1.png", "status": "approved"}

    def test_copy_for_carries_use_and_versions(self):
        from kit import ppc
        c = ppc._copy_for(self._camp(), {}, "clean")
        self.assertEqual(c["use"], "both")
        self.assertEqual(c["versions"], [{"hook": "V2", "use": "ppc"}])

    def test_meta_one_row_per_version(self):
        from kit import ppc
        rows = ppc._meta_rows([self._piece()], self._camp(), self._brand())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Ad Name"], "p1")
        self.assertEqual(rows[1]["Ad Name"], "p1_V1")
        self.assertEqual(rows[1]["Body"], "V2")

    def test_image_only_excluded(self):
        from kit import ppc
        camp = self._camp()
        camp["copy"]["default"]["clean"]["use"] = "image"
        self.assertEqual(ppc._meta_rows([self._piece()], camp, self._brand()), [])

    def test_ppc_only_extra_rows(self):
        from kit import ppc
        camp = self._camp()
        camp["copy"]["default"]["clean"]["use"] = "ppc"
        rows = ppc._ppc_only_rows(camp, self._brand())
        self.assertEqual(len(rows), 2)  # base + 1 version
        self.assertEqual(rows[0]["Body"], "Base")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content.PpcRouting -v`
Expected: FAIL — `KeyError: 'use'` in _copy_for result.

- [ ] **Step 3: Write minimal implementation**

`kit/ppc.py` `_copy_for` — extend the returned dict:

```python
    return {"hook": _clean(merged.get("hook", "")),
            "kicker": _clean(merged.get("kicker", "")),
            "program": _clean(merged.get("program") or C.lookup(camp.get("labels"), combo) or ""),
            "cta": _clean(merged.get("cta", camp.get("cta", "Learn more"))),
            "use": merged.get("use") or "both",
            "versions": merged.get("versions") or []}
```

Add a helper after `_copy_for`:

```python
def _variants(copy):
    base = {k: copy[k] for k in ("hook", "kicker", "program", "cta")}
    return [base] + [{k: _clean(v.get(k, "")) for k in base} for v in copy["versions"]]
```

`_meta_rows` — skip image-only, one row per variant:

```python
def _meta_rows(pieces, camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    rows = []
    for p in pieces:
        copy = _copy_for(camp, p.get("axes", {}), p["concept"])
        if copy["use"] == "image":
            continue
        for i, v in enumerate(_variants(copy)):
            row = {c: "" for c in META_COLUMNS}
            row.update({"Campaign Name": cname, "Campaign Status": "PAUSED", "Buying Type": "AUCTION",
                        "Ad Set Name": _adgroup(p["concept"], p.get("axes", {})), "Ad Set Run Status": "PAUSED",
                        "Placements": _meta_placement(p["format"]),
                        "Ad Name": p["id"] if i == 0 else f"{p['id']}_V{i}", "Ad Status": "PAUSED",
                        "Creative Type": "Link Page Post Ad", "Title": _trunc(v["program"] or v["hook"], 40),
                        "Body": v["hook"], "Link Description": _trunc(v["kicker"], 30),
                        "Call to Action": _cta_enum(v["cta"]), "Link": url})
            row["Video File Name" if p.get("kind") == "video" else "Image File Name"] = _creative_basename(p)
            rows.append(row)
    return rows
```

`_display_rows` — skip image-only, one row per variant (full replacement):

```python
def _display_rows(pieces, camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    logo = os.path.basename(brand.logo_path) if brand.logo_path else ""
    rows = []
    for p in pieces:
        copy = _copy_for(camp, p.get("axes", {}), p["concept"])
        if copy["use"] == "image":
            continue
        for i, v in enumerate(_variants(copy)):
            row = {c: "" for c in DISPLAY_COLUMNS}
            row.update({"Campaign": cname, "Ad group": _adgroup(p["concept"], p.get("axes", {})),
                        "Ad type": "Responsive display ad", "Headline": _trunc(v["program"] or v["hook"], 30),
                        "Long headline": _trunc(v["hook"], 90), "Description": _trunc(v["kicker"] or v["hook"], 90),
                        "Business name": brand.name, "Final URL": url, "Status": "Paused",
                        "Image file": _creative_basename(p), "Logo file": logo, "Size": _size(p["format"]),
                        "Concept": p["concept"], "Placement": "Google Display Network"})
            rows.append(row)
    return rows
```

`_rsa_rows` — skip image-only; pool headlines/descriptions across variants:

```python
    for concept, combo in combos:
        copy = _copy_for(camp, combo, concept)
        if copy["use"] == "image":
            continue
        vs = _variants(copy)
        headlines = [_trunc(x, 30) for x in _dedup(
            [t for v in vs for t in (v["program"], v["kicker"], v["hook"], v["cta"])] + [brand.name])]
        descriptions = [_trunc(x, 90) for x in _dedup(
            [t for v in vs for t in (
                v["hook"],
                " ".join(x for x in [v["kicker"], v["program"]] if x),
                " — ".join(x for x in [v["cta"], v["program"]] if x))])]
```

(rest of the row building unchanged; caps `[:15]` / `[:4]` stay).

`_manifest_rows` — add `if copy["use"] == "image": continue` after `_copy_for`.

New `_ppc_only_rows` (copy entries with `use: ppc` have no piece; export as text-ad rows, creative left blank for the PPC team):

```python
def _ppc_only_rows(camp, brand):
    cname, url = _campaign_name(camp, brand), camp.get("landing_url", "")
    rows = []
    for axis, concepts in (camp.get("copy") or {}).items():
        if not isinstance(concepts, dict):
            continue
        for concept, entry in concepts.items():
            if not isinstance(entry, dict) or entry.get("use") != "ppc":
                continue
            copy = {"hook": _clean(entry.get("hook", "")), "kicker": _clean(entry.get("kicker", "")),
                    "program": _clean(entry.get("program", "")),
                    "cta": _clean(entry.get("cta", camp.get("cta", "Learn more"))),
                    "use": "ppc", "versions": entry.get("versions") or []}
            for i, v in enumerate(_variants(copy)):
                row = {c: "" for c in META_COLUMNS}
                row.update({"Campaign Name": cname, "Campaign Status": "PAUSED", "Buying Type": "AUCTION",
                            "Ad Set Name": _adgroup(concept, {} if axis == "default" else dict(
                                zip(("axis",), (axis,)))), "Ad Set Run Status": "PAUSED",
                            "Ad Name": f"{concept}_{axis}_V{i + 1}", "Ad Status": "PAUSED",
                            "Creative Type": "Link Page Post Ad",
                            "Title": _trunc(v["program"] or v["hook"], 40), "Body": v["hook"],
                            "Link Description": _trunc(v["kicker"], 30),
                            "Call to Action": _cta_enum(v["cta"]), "Link": url})
                rows.append(row)
    return rows
```

In `export()`, change the Meta emit to include ppc-only rows:

```python
    if want_meta:
        emit("meta_bulk_import", META_COLUMNS,
             _meta_rows(meta, camp, brand) + _ppc_only_rows(camp, brand),
             "Meta bulk import", "meta")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python.exe -m unittest tests.test_content -v`
Expected: 23 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add kit/ppc.py tests/test_content.py
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "feat(ppc): use routing, one row per version, ppc-only text-ad rows"
```

---

### Task 9: Docs + spec correction

**Files:**
- Modify: `AGENTS.md` (pipeline + new "Content" section)
- Modify: `skills/campaign-kit/SKILL.md` (step between plan and assets)
- Modify: `docs/superpowers/specs/2026-11-12-content-team-design.md` (intake wording)

- [ ] **Step 1: Update AGENTS.md**

In the Pipeline block, between `plan` (step 3) and `assets` (step 4), add:

```bash
# 3b. Conteúdo base da planilha do time de conteúdo (opcional)
python3 -m kit.cli content campaigns/acme-launch          # ingest + valida → content.json
#    SEU TRABALHO: aplique as regras da seção 11 do briefing em content.json
#    (versões, adaptação por destino use: image/ppc/both). Nunca invente copy.
python3 -m kit.cli content campaigns/acme-launch --apply  # mescla em campaign.json.copy
```

Add a "## Conteúdo base (planilha do time de conteúdo)" section after "Documentos de apoio do briefing": slot `content/` (.xlsx/.csv) + `content_link.txt` (SharePoint — o agente baixa uma vez, o kit nunca fala com SharePoint); colunas canônicas (concept, axis?, hook, kicker, program, cta, use, lang?); `use` em branco = both; render pula `use: ppc`, PPC pula `use: image`; versões = linhas extras (base primeiro); variantes de imagem via eixo de versão (mecanismo existente de axes + lookup); o agente copia a planilha do inbox para `campaigns/<slug>/content/` antes de rodar `content`.

- [ ] **Step 2: Update SKILL.md**

In the passos list, between step 5 (plan) and step 6 (custo), insert: "5b. **Conteúdo base**: se o inbox tem `content/` (planilha) ou `content_link.txt`, copie para `campaigns/<slug>/content/` (link: baixe uma vez pelo navegador), rode `content`, aplique as regras da seção 11 do briefing em `content.json` (versões por destino `use`), rode `content --apply`. Sem planilha, o passo é opcional."

- [ ] **Step 3: Correct the spec**

In the spec's Flow section, replace "(copied there by intake, like other slots)" with "(the agent copies it from the inbox — collected by `intake.inventory` — into the campaign's `content/` dir before running `content`, same agent-mediated pattern as provider drop_dir)".

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md skills/campaign-kit/SKILL.md docs/superpowers/specs/2026-11-12-content-team-design.md
git -c user.name="Dann Owczarzak" -c user.email="owk.dann@gmail.com" commit -m "docs: content step contract (AGENTS.md + skill) and spec intake wording"
```

---

### Task 10: Full verification + push

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -t . -v`
Expected: 23 tests PASS, 0 failures.

- [ ] **Step 2: End-to-end smoke (acme fixture)**

```bash
.venv/Scripts/python.exe -m kit.cli content campaigns/acme-launch
```
Expected: JSON with `gaps: ["sem planilha em content/ ..."]`, exit 0 (optional step, no sheet).

- [ ] **Step 3: Live wizard check**

With the wizard running (Task 5 Step 5), confirm in the browser: content slot accepts a .csv, link field saves/persists, EN toggle localizes slot + link labels, briefing textarea shows section 11 in both languages.

- [ ] **Step 4: Push**

```bash
git push
```

- [ ] **Step 5: Report**

Summarize to the user in PT: what shipped, the `use` routing, how the content team fills the sheet, and that the agent downloads SharePoint links once.